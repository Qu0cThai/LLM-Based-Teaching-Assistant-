import json
import re

from config import MODEL_FAST
from llm.ollama_client import ollama_chat
from llm.prompts import (
    mcq_prompt,
    short_answer_prompt,
    fill_blank_prompt
)

from questions.validators import (
    validate_mcq,
    validate_fix_short_answer,
)

from questions.normalize import (
    normalize_mcq_options,
)

def clean_json(text):
    match = re.search(r"(\[\s*\{.*?\}\s*\])", text, re.DOTALL)
    return match.group(1) if match else text

def parse_llm_json(text):
    cleaned = clean_json(text)
    try:
        return json.loads(cleaned)
    except Exception:
        return []

def generate_mcqs_json(context, n, reason="", batch=5, retries=5, subject="General", difficulty="Medium"):
    results, seen = [], set()

    for i in range(0, n, batch):
        count = min(batch, n - i)
        attempt = 0

        while attempt < retries and len(results) < n:
            prompt = mcq_prompt(context, count, reason, subject, difficulty) 
            resp = ollama_chat(MODEL_FAST, prompt)
            
            data = parse_llm_json(resp["message"]["content"])

            for mcq in data:
                mcq = normalize_mcq_options(mcq)
                if not validate_mcq(mcq):
                    continue
                if mcq["question"] in seen:
                    continue

                seen.add(mcq["question"])
                results.append(mcq)

            attempt += 1

    return results[:n]

def generate_short_answer_json(context, n, reason="", subject="General", difficulty="Medium"):
    prompt = short_answer_prompt(context, n, reason, subject, difficulty)
    resp = ollama_chat(MODEL_FAST, prompt)
    raw = parse_llm_json(resp["message"]["content"])
    results = []
    for q in raw:
        if not isinstance(q, dict):
            continue
        fixed = validate_fix_short_answer(q, context)
        if fixed:
            results.append(fixed)
    return results

def generate_fill_blank_json(context, n, reason="", subject="General", difficulty="Medium"):
    prompt = fill_blank_prompt(context, n, reason, subject, difficulty)
    resp = ollama_chat(MODEL_FAST, prompt)
    return parse_llm_json(resp["message"]["content"])