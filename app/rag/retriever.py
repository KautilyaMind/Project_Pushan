"""Retrieval stays separate so relevance can be inspected and tested."""

from pathlib import Path

from langchain_core.documents import Document

from .vector_store import DEFAULT_VECTOR_STORE_PATH, load_vector_store


def retrieve_context(
    question: str,
    k: int = 3,
    persist_path: str | Path = DEFAULT_VECTOR_STORE_PATH,
) -> list[Document]:
    """Return at most k chunks most similar to a non-empty question."""
    if not question.strip():
        raise ValueError("Question must not be empty.")
    if k < 1:
        raise ValueError("k must be at least 1.")
    return load_vector_store(persist_path).similarity_search(question.strip(), k=k)
