import ollama
import numpy as np
from config import MODEL_FAST, EMBED_MODEL
import hashlib

def ollama_chat(model, prompt):
    return ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

_embed_cache = {}

def embed_ollama(text: str):
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    if key in _embed_cache:
        return _embed_cache[key]

    resp = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=text
    )
    vec = np.array(resp["embedding"])
    _embed_cache[key] = vec
    return vec
