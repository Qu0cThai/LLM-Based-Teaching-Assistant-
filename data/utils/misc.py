import re
from config import STOPWORDS

def is_true_false_answer(q):
    return q.get("answer", "").strip().lower() in {"true", "false", "yes", "no"}

def is_meta_structure_question(text: str) -> bool:
    text = text.lower()

    banned_patterns = [
        r"\bappendix\b",
        r"\btable\b",
        r"\bfigure\b",
        r"\blecture\b",
        r"\bnote\b",
        r"\bchapter\b",
        r"\bslide\b",
        r"\bexample\b",
        r"\bsection\b",
        r"\bpage\b",
        r"\bdocument\b",
        r"\b[a-z]\.\d+\b", 
        r"primary focus of",
        r"covers?\b",
        r"summarize\b",
        r"in the given",       
        r"in the context provided", 
        r"mentioned in"          
        r"what does ['\"`]?[a-z]['\"`]? represent",
        r"what does ['\"`]?[a-z]['\"`]? stand for",
        r"\bauthor\b",
        r"this book\b",     
        r"development of\b", 
        r"in th[ei]s? book",       
        r"of th[ei]s? book",        
        r"\bpart\s*\d+\b",         
        r"\bchapter\s*\d*\b",       
        r"presentation style",     
        r"pseudocode listing",      
        r"author['s]?\s",         
    ]

    return any(re.search(p, text) for p in banned_patterns)


def has_broken_inline_code(text: str) -> bool:
    if not isinstance(text, str):
        return True

    if re.search(r"`\s*`", text):
        return True

    if re.search(r"```[\s\n]*```", text):
        return True

    return False


def normalize_blank_token(text: str) -> str:
    return re.sub(r"_+", "____", text)


def extract_topic_keywords(question: str):
    words = re.findall(r"[a-zA-Z_]{3,}", question.lower())
    return {
        w for w in words
        if w not in STOPWORDS
        and not w.isdigit()
    }
