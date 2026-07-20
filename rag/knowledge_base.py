"""
Facade over the retriever so agents ask for context by *intent*
(e.g. "generate a dashboard chart component") instead of knowing
anything about TF-IDF or the underlying doc store.
"""

from rag.retriever import get_retriever


def get_context(component_type: str, description: str, top_k: int = 3) -> tuple[str, list]:
    """
    Returns (formatted_context_string, raw_results) for a given component
    request, so callers can both feed the LLM and show retrieval evidence
    in the UI (useful for the demo video / RAG-effectiveness metric).
    """
    retriever = get_retriever()
    query = f"{component_type} {description}"
    results = retriever.retrieve(query, top_k=top_k)

    if not results:
        return "No directly relevant documentation snippet was retrieved.", []

    formatted = "\n".join(
        f"- [{r['title']}] {r['content']}" for r in results
    )
    return formatted, results
