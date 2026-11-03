import re
from llm.ollama_client import ollama_chat
from config import MODEL_PLANNER

def extract_subtopics(topic, context):
    prompt = f"""
Extract 5-10 important subtopics/concepts related to "{topic}"
from the context below.

Return comma separated only.

Context:
{context}
"""

    try:
        resp = ollama_chat(MODEL_PLANNER, prompt)
        raw = resp["message"]["content"]

        cleaned = re.sub(r"[\n\-•]", ",", raw)

        return [
            x.strip()
            for x in cleaned.split(",")
            if x.strip()
        ][:10]

    except:
        return []