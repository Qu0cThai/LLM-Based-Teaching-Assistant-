import numpy as np
from concurrent.futures import ThreadPoolExecutor
from llm.ollama_client import embed_ollama

def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)

def embed_chunks_parallel(chunks, max_workers=2):
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(embed_ollama, chunks))

def retrieve_top_k(query, chunks, vectors, k=None, q_vec=None):
    if q_vec is None:
        q_vec = embed_ollama(query)

    scores = [cosine(q_vec, v) for v in vectors]
    k = k or len(chunks)
    top_idx = np.argsort(scores)[-k:][::-1]
    return [chunks[i] for i in top_idx]
