import re
from processing.embedding import cosine
from llm.ollama_client import embed_ollama, ollama_chat
from config import MODEL_FAST
from llm.prompts import judge_prompt
from questions.types import QuestionType
from utils.misc import is_meta_structure_question, has_broken_inline_code, normalize_blank_token, extract_topic_keywords

def context_grounding_check(text: str, context: str, threshold: float = 0.5) -> bool:
    text_words = extract_topic_keywords(text)
    if not text_words:
        return True 

    context_lower = context.lower()
    matched = sum(1 for w in text_words if w in context_lower)
    
    match_ratio = matched / len(text_words)
    return match_ratio >= threshold

def semantic_grounding_check(text: str, context: str, threshold: float = 0.45) -> bool:
    try:
        t_vec = embed_ollama(text)
        c_vec = embed_ollama(context)
        score = cosine(t_vec, c_vec)
        return score >= threshold
    except Exception:
        return True 

def get_semantic_score(text: str, context: str) -> float:
    try:
        t_vec = embed_ollama(text)
        c_vec = embed_ollama(context)
        return cosine(t_vec, c_vec)
    except Exception:
        return 1.0
    
def llm_judge_check(q: dict, context: str) -> bool:
    if q.get("type") != QuestionType.MCQ.value:
        return True

    q_text = q.get("question", "")
    options_str = " | ".join(q.get("options", []))
    answer = q.get("answer", "")

    prompt = judge_prompt(q_text, options_str, answer, context)
    
    try:
        resp = ollama_chat(MODEL_FAST, prompt)
        decision = resp["message"]["content"].strip().upper()
        return "VALID" in decision
    except Exception:
        return True 

def mark_review(q):
    q["needs_review"] = True
    return q

def reject_if_meta(q):
    if not isinstance(q, dict):
        return None
    return None if is_meta_structure_question(q.get("question", "")) else q

def has_broken_code(text):
    return has_broken_inline_code(text)

def validate_mcq(mcq):
    if not isinstance(mcq, dict):
        return False

    qtext = mcq.get("question", "").strip()
    if not qtext:
        return False

    options = mcq.get("options")
    if not isinstance(options, list) or len(options) != 4:
        return False
    for opt in options:
        if has_broken_inline_code(opt):
            return False

    labels = {"A", "B", "C", "D"}
    
    for i, opt in enumerate(options):
        if not isinstance(opt, str):
            return False
            
        clean_text = re.sub(r'^[A-D]\.\s*', '', opt, flags=re.IGNORECASE).strip()
        
        if not clean_text:
            return False
            
        options[i] = f"{chr(65+i)}. {clean_text}"

    mcq["options"] = options

    ans = mcq.get("answer", "").upper()
    if ans not in labels:
        return False

    return True

def validate_fix_mcq(q, context=""):
    if reject_if_meta(q) is None:
        return None

    if not validate_mcq(q):
        return None

    qtext = q["question"].lower()

    bad_phrases = [
        r"refer to\s*$", 
        r"indicate\s*$", 
        r"what does .* mean\s*$",
        r"in this context\s*$"
    ]

    if any(re.search(p, qtext) for p in bad_phrases):
        return None
    
    tokens = q["question"].split()
    if len(tokens) < 6:
        mark_review(q)
        
    if any(p in qtext for p in ["output of", "result of", "what will this code"]):
        if "<code>" not in context.lower():
            return None

    if q["question"].strip().endswith("?"):
        idx = ord(q["answer"]) - 65
        if 0 <= idx < 4:
            ans_text = q["options"][idx].lower()
            if "start of" in ans_text and "}" in q["question"]:
                return None

    if not isinstance(q.get("justification"), str):
        mark_review(q)

    return q

def validate_fix_short_answer(q, context=""):
    if not isinstance(q, dict):
        return None

    if reject_if_meta(q) is None:
        return None

    question = q.get("question", "").lower()
    answer = q.get("answer", "").strip()

    if not answer:
        return None

    if answer.lower() in {"true", "false", "yes", "no"}:
        return None

    if len(answer.split()) < 5:
        return mark_review(q)

    if "continue" in question:
        if not any(k in answer.lower() for k in ["loop", "iteration", "skip"]):
            return None

    if "break" in question:
        if not any(k in answer.lower() for k in ["terminate", "loop"]):
            return None

    ctx_words = extract_topic_keywords(context)
    ans_words = extract_topic_keywords(answer)
    if len(ctx_words & ans_words) < 1:
        mark_review(q)

    if not isinstance(q.get("justification"), str):
        mark_review(q)

    return q

def validate_fix_fill_blank(q, context):
    if not isinstance(q, dict):
        return None

    if reject_if_meta(q) is None:
        return None

    question = normalize_blank_token(q.get("question", "")).strip()
    answer = q.get("answer", "").strip()

    if not question or not answer or "____" not in question:
        return None

    if len(question.split()) < 5:
        return None
    if len(answer.split()) > 4:
        return None

    lazy_answers = {"process", "system", "method", "procedure", "approach", "this", "that", "it", "true", "false", "one", "two", "the", "a", "an"}
    if answer.lower() in lazy_answers:
        return None

    question = re.sub(r'^[A-Z]+\s+\d+\s+', '', question) 
    question = re.sub(r'^\d+(\.\d+)+\s+[A-Za-z]+\s+', '', question) 
    question = re.sub(r'^Chapter\s+\d+[:\s]*[a-zA-Z]+\s+', '', question, flags=re.IGNORECASE)
    question = re.sub(r'^Figure\s+\d+(\.\d+)?:.*?\s+', '', question, flags=re.IGNORECASE)
    question = re.sub(r'^\d+[\)\.]\s+', '', question)

    if "____" not in question:
        return None

    match_start = re.search(r'[a-zA-Z]', question)
    if match_start:
        question = question[match_start.start():]
        question = question[0].upper() + question[1:]

    from config import STOPWORDS
    q_words = set(re.findall(r'[a-zA-Z]{3,}', question.lower() + " " + answer.lower())) - STOPWORDS
    ctx_words = set(re.findall(r'[a-zA-Z]{3,}', context.lower()))
    
    if not q_words:
        return None
        
    overlap = len(q_words & ctx_words)
    if overlap / len(q_words) < 0.6: 
        return None 

    q["question"] = question
    q["answer"] = answer
    return q

def validate_and_fix_question(q, context=""):
    if has_broken_inline_code(q.get("question", "")):
        return None

    qtype = QuestionType(q["type"])
    fixed_q = None

    if qtype is QuestionType.MCQ:
        fixed_q = validate_fix_mcq(q, context)
    elif qtype is QuestionType.FILL_BLANK:
        fixed_q = validate_fix_fill_blank(q, context)
    elif qtype is QuestionType.SHORT_ANSWER:
        fixed_q = validate_fix_short_answer(q, context)

    if not fixed_q:
        return None

    check_text = fixed_q["question"] + " " + str(fixed_q.get("answer", ""))
    
    if qtype is QuestionType.MCQ:
        lex_thresh = 0.20 
        sem_thresh = 0.45
    elif qtype is QuestionType.SHORT_ANSWER:
        lex_thresh = 0.10 
        sem_thresh = 0.35  
    else:
        lex_thresh = 0.60
        sem_thresh = 0.45

    lex_passed = context_grounding_check(check_text, context, threshold=lex_thresh)
    sem_score = get_semantic_score(check_text, context)

    actual_sem_thresh = 0.25 if qtype == QuestionType.SHORT_ANSWER else sem_thresh
    if sem_score < actual_sem_thresh:
        return None

    if lex_passed and sem_score < 0.85:
        return fixed_q
    
    if not llm_judge_check(fixed_q, context):
        return None

    return fixed_q

def is_true_false_answer(q):
    return q.get("answer", "").strip().lower() in {"true", "false", "yes", "no"}