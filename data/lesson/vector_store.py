import numpy as np

class SimpleVectorStore:
    def __init__(self, embed_fn):
        self.embed_fn = embed_fn
        self.data = []

    def add(self, chunks):
        for chunk in chunks:
            embedding = self.embed_fn(chunk["text"])

            self.data.append({
                "text": chunk["text"],
                "source": chunk["source"],
                "embedding": embedding
            })

    def search(self, query, top_k=5):
        query_vec = self.embed_fn(query)

        def cosine(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        scored = []
        for item in self.data:
            score = cosine(query_vec, item["embedding"])
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [item for _, item in scored[:top_k]]