"""
Lightweight local RAG retriever.

Uses scikit-learn's TF-IDF + cosine similarity instead of a full vector DB
(ChromaDB/FAISS) so the deployed app has no heavy native dependencies or
first-boot model downloads — important when the deployment target is a
free Streamlit host with a cold-start budget. Swapping this for ChromaDB
later only means replacing this one module.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag.docs_data import DOCS


class Retriever:
    def __init__(self):
        self.docs = DOCS
        corpus = [f"{d['title']} {' '.join(d['tags'])} {d['content']}" for d in self.docs]
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.doc_matrix = self.vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, top_k: int = 3):
        if not query.strip():
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.doc_matrix).flatten()
        ranked = sorted(zip(scores, self.docs), key=lambda x: x[0], reverse=True)
        results = [
            {"score": round(float(score), 3), **doc}
            for score, doc in ranked[:top_k]
            if score > 0.0
        ]
        return results


_retriever_singleton = None


def get_retriever() -> Retriever:
    global _retriever_singleton
    if _retriever_singleton is None:
        _retriever_singleton = Retriever()
    return _retriever_singleton
