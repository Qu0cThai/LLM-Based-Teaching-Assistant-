import json
import re
from llm.ollama_client import ollama_chat
from config import MODEL_PLANNER

def extract_json(raw: str) -> str:
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1:
        return raw[start:end+1]
    return raw

def clean_json_text(raw: str) -> str:
    raw = re.sub(r"```json|```", "", raw)
    raw = re.sub(r'"\s*\n\s*"', '",\n"', raw)
    raw = re.sub(r',\s*([\]}])', r'\1', raw)
    raw = re.sub(r'(\w+\s*\(\d{4}\)[^,"\]\}]*)', r'"\1"', raw)
    raw = re.sub(r'\[\s*\[([^\]]+)\]\s*\]', r'[\1]', raw)

    return raw.strip()

def safe_json_parse(raw: str) -> dict:
    raw = clean_json_text(raw)

    try:
        return json.loads(raw)
    except:
        pass

    try:
        cleaned = extract_json(raw)
        cleaned = clean_json_text(cleaned)
        return json.loads(cleaned)
    except:
        pass

    fix_prompt = f"""
You must convert this into VALID JSON.

Rules:
- Fix ALL syntax errors
- Merge broken strings into ONE line
- Ensure arrays contain ONLY strings
- Return ONLY JSON

{raw}
"""

    try:
        resp = ollama_chat(MODEL_PLANNER, fix_prompt)

        fixed = extract_json(
            resp["message"]["content"]
        )

        return json.loads(fixed)

    except:
        return {
            "error": "JSON_PARSE_FAILED",
            "raw": raw
        }