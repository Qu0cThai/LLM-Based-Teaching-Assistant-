import re
import hashlib
from datetime import datetime
import random
from questions.types import QuestionType

def normalize_question_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def ensure_question_id(q):
    if "id" not in q:
        raw = q["question"]
        q["id"] = hashlib.md5(raw.encode("utf-8")).hexdigest()

def normalize_question_object(q, qtype: QuestionType):
    q["type"] = qtype.value 
    q["_type"] = qtype
    q["created_at"] = q.get("created_at") or datetime.now().isoformat()
    ensure_question_id(q)
    return q

def normalize_mcq_options(q):
    if not isinstance(q, dict):
        return None

    if "options" not in q or not isinstance(q["options"], list):
        return None

    options = q.get("options", [])
    if not isinstance(options, list) or len(options) != 4:
        return None

    fixed = []
    for i, opt in enumerate(options):
        label = chr(65 + i)
        text = re.sub(r"^[A-D]\.\s*", "", opt, flags=re.IGNORECASE).strip()
        fixed.append(f"{label}. {text}")

    q["options"] = fixed
    return q

def shuffle_mcq_options(q):
    options = q["options"][:]
    correct_letter = q["answer"].upper()
    idx = ord(correct_letter) - 65
    if 0 <= idx < len(options):
        correct_text = options[idx]
    else:
        return q  
    
    random.shuffle(options)
    
    new_options = []
    new_answer = None
    for i, opt in enumerate(options):
        label = chr(65 + i)
        text = re.sub(r"^[A-D]\.\s*", "", opt)
        new_opt = f"{label}. {text}"
        new_options.append(new_opt)

        if opt == correct_text:
            new_answer = label

    q["options"] = new_options
    q["answer"] = new_answer
    return q

def get_mcq_answer_text(q):
    letter = q.get("answer", "").upper()
    options = q.get("options", [])

    if not letter or not options:
        return "Invalid answer"

    idx = ord(letter) - 65  
    if 0 <= idx < len(options):
        return options[idx]

    return "Invalid answer"