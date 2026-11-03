import re
import random
from datetime import datetime
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import STOPWORDS
from io_utils import load_json
from questions.quota import compute_quota
from questions.types import QuestionType

from questions.generators import (
    generate_mcqs_json,
    generate_short_answer_json,
    generate_fill_blank_json,
)

from questions.normalize import (
    normalize_question_object,
    normalize_mcq_options,
    get_mcq_answer_text,
)

from questions.validators import (
    validate_and_fix_question,
    is_true_false_answer,
    validate_fix_mcq,
    validate_fix_short_answer,
    validate_fix_fill_blank 
)

TYPE_TO_GENERATOR = {
    QuestionType.MCQ: generate_mcqs_json,
    QuestionType.SHORT_ANSWER: generate_short_answer_json,
    QuestionType.FILL_BLANK: generate_fill_blank_json,
}

def _get_keywords(text: str) -> set:
    tokens = text.lower().split()
    cleaned = set()
    for t in tokens:
        t = t.strip('.,!?"\'()[]{}')
        if t and t not in STOPWORDS:
            cleaned.add(t)
    return cleaned

def is_semantic_duplicate(q, accepted_list):
    q_text = q['question'].lower()
    q_ans = str(q.get('answer', '')).lower()
    
    if q.get('type') == QuestionType.MCQ.value:
        q_ans = get_mcq_answer_text(q).lower()
        q_ans = re.sub(r'^[a-d]\.\s*', '', q_ans)

    q_text_words = _get_keywords(q_text)
    q_ans_words = _get_keywords(q_ans)
    q_full_words = q_text_words | q_ans_words

    for acc in accepted_list:
        acc_text = acc['question'].lower()
        acc_ans = str(acc.get('answer', '')).lower()
        
        if acc.get('type') == QuestionType.MCQ.value:
            acc_ans = get_mcq_answer_text(acc).lower()
            acc_ans = re.sub(r'^[a-d]\.\s*', '', acc_ans)
        
        if q_text.strip() == acc_text.strip():
            return True

        acc_text_words = _get_keywords(acc_text)
        acc_ans_words = _get_keywords(acc_ans)
        acc_full_words = acc_text_words | acc_ans_words

        if q_text_words and acc_text_words:
            text_overlap = len(q_text_words & acc_text_words)
            text_union = len(q_text_words | acc_text_words)
            if text_union > 0 and (text_overlap / text_union) >= 0.40:
                return True

        if q_ans_words and acc_ans_words:
            ans_overlap = len(q_ans_words & acc_ans_words)
            ans_union = len(q_ans_words | acc_ans_words)
            if ans_union > 0 and (ans_overlap / ans_union) >= 0.50:
                return True

        if q_full_words and acc_full_words:
            full_overlap = len(q_full_words & acc_full_words)
            full_union = len(q_full_words | acc_full_words)
            
            dup_threshold = 0.50 if q.get('type') == QuestionType.MCQ.value else 0.60
            if full_union > 0 and (full_overlap / full_union) > dup_threshold:
                return True
                
    return False

def get_evenly_spaced_blocks(text: str, target_blocks: int, words_per_block: int = 600) -> List[str]:
    words = text.split()
    total_words = len(words)
    
    if total_words <= words_per_block:
        return [" ".join(words)]

    all_blocks = []
    for i in range(0, total_words, words_per_block):
        all_blocks.append(" ".join(words[i : i + words_per_block]))

    if len(all_blocks) <= target_blocks:
        return all_blocks

    step = len(all_blocks) / target_blocks
    sampled_blocks = [all_blocks[int(i * step)] for i in range(target_blocks)]
    return sampled_blocks

def _generate_from_block(qtype: QuestionType, required: int, block_context: str, subject: str, difficulty: str) -> Tuple[QuestionType, list, str, str]:
    if required <= 0:
        return qtype, [], block_context, difficulty
        
    reason_prompt = "Generate highly distinct questions based strictly on this specific excerpt."
    raw = TYPE_TO_GENERATOR[qtype](block_context, required, reason=reason_prompt, subject=subject, difficulty=difficulty)
    
    if not isinstance(raw, list):
        return qtype, [], block_context, difficulty
        
    return qtype, raw, block_context, difficulty

def generate_questions_pipeline(
    text: str,
    num_questions: int,
    selected_labels: list,
    subject: str = "General",
    diff_distribution: dict = None
):
    if diff_distribution is None:
        diff_distribution = {"Easy": 25, "Medium": 50, "Hard": 25}
        
    failure_reasons = []

    selected_types = [QuestionType.from_label(l) for l in selected_labels if QuestionType.from_label(l)]
    if not selected_types:
        return [], ["No valid question types selected"]

    from questions.quota import compute_quota, compute_diff_quota
    quota = compute_quota(num_questions, selected_types)
    
    target_matrix = {}
    for qtype in selected_types:
        qtype_total = quota[qtype]
        qtype_diffs = compute_diff_quota(qtype_total, diff_distribution)
        for d, count in qtype_diffs.items():
            if count > 0:
                target_matrix[(qtype, d)] = count

    final_questions_map = {k: [] for k in target_matrix.keys()}
    
    global_seen_pool = []

    target_blocks = max(20, num_questions * 4)
    blocks = get_evenly_spaced_blocks(text, target_blocks, words_per_block=300)
    random.shuffle(blocks)
    
    batch_size = 1
    raw_candidates = []
    
    for i in range(0, len(blocks), batch_size):
        current_batch = blocks[i : i + batch_size]
        tasks = []
    
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            for block in current_batch:
                for (qtype, diff), required_count in target_matrix.items():
                    if len(final_questions_map[(qtype, diff)]) < required_count:
                        tasks.append(executor.submit(_generate_from_block, qtype, 5, block, subject, diff))

            for future in as_completed(tasks):
                try:
                    qtype, generated_raw, block_context, diff = future.result()
                    for q in generated_raw:
                        raw_candidates.append((qtype, q, block_context, diff))
                except Exception:
                    continue

        total_needed = sum(target_matrix.values())
        if len(raw_candidates) >= total_needed * 2:
            break

    for qtype, q, block_context, diff in raw_candidates:
        if len(final_questions_map[(qtype, diff)]) >= target_matrix[(qtype, diff)]:
            continue

        q = normalize_question_object(q, qtype)
        if not q: continue

        if qtype is QuestionType.MCQ:
            q = normalize_mcq_options(q)
        if qtype is QuestionType.SHORT_ANSWER and is_true_false_answer(q):
            continue

        q_valid = validate_and_fix_question(q, block_context)

        if q_valid and not is_semantic_duplicate(q_valid, global_seen_pool):
            q_valid["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            q_valid["difficulty"] = diff
            final_questions_map[(qtype, diff)].append(q_valid)
            global_seen_pool.append(q_valid)
            
    for (qtype, diff), required in target_matrix.items():
        attempts = 0
        while len(final_questions_map[(qtype, diff)]) < required and attempts < 5:
            missing = required - len(final_questions_map[(qtype, diff)])
            fallback_block = random.choice(blocks) if blocks else text[:1000]
            _, fallback_raw, _, _ = _generate_from_block(qtype, missing + 2, fallback_block, subject, diff)
            
            for q in fallback_raw:
                if len(final_questions_map[(qtype, diff)]) >= required:
                    break 
                    
                q = normalize_question_object(q, qtype)
                if not q: continue
                
                if qtype == QuestionType.MCQ:
                    q = normalize_mcq_options(q)
                    q_valid = validate_fix_mcq(q, fallback_block)
                elif qtype == QuestionType.SHORT_ANSWER:
                    q_valid = validate_fix_short_answer(q, fallback_block)
                elif qtype == QuestionType.FILL_BLANK:
                    q_valid = validate_fix_fill_blank(q, fallback_block)
                    
                if q_valid:
                    q_valid["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    q_valid["difficulty"] = diff
                    final_questions_map[(qtype, diff)].append(q_valid)
                    
            attempts += 1
            
    final_questions = []
    for (qtype, diff), required in target_matrix.items():
        acquired = len(final_questions_map[(qtype, diff)])
        final_questions.extend(final_questions_map[(qtype, diff)][:required])
        
        if acquired < required:
            failure_reasons.append(
                f"{qtype.value.upper()} ({diff}): Only generated {acquired}/{required} valid questions."
            )

    return final_questions, failure_reasons