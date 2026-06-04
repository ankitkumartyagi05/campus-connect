try:
    import chromadb

    # Initialize persistent local ChromaDB
    chroma_client = chromadb.Client()
    mentor_collection = chroma_client.get_or_create_collection(
        name="mentors",
        metadata={"hnsw:space": "cosine"}
    )
except Exception:
    # Fallback in-memory collection when chromadb is not installed or build tools are missing.
    class _InMemoryCollection:
        def __init__(self):
            self._store = {}

        def upsert(self, ids, embeddings, metadatas=None):
            for i, _id in enumerate(ids):
                self._store[_id] = {
                    "embedding": embeddings[i],
                    "metadata": (metadatas[i] if metadatas else {})
                }

        def query(self, query_embeddings, n_results=3):
            # naive nearest by dot product
            import math

            def score(vec1, vec2):
                return sum(a * b for a, b in zip(vec1, vec2))

            q = query_embeddings[0]
            scores = []
            for _id, item in self._store.items():
                emb = item["embedding"]
                sc = score(q, emb)
                scores.append((_id, sc, item["metadata"]))

            scores.sort(key=lambda x: x[1], reverse=True)
            top = scores[:n_results]
            # return simplified structure similar to chromadb
            return [{"id": _id, "score": sc, "metadata": meta} for _id, sc, meta in top]

    mentor_collection = _InMemoryCollection()