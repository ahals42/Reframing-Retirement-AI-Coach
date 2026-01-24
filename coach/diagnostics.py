"""Diagnostic utilities for the coach module."""

from rag.retriever import RagRetriever


def run_rag_sanity_check(retriever: RagRetriever) -> None:
    """Query the master index once to confirm retrieval is working."""

    try:
        chunks = retriever.retrieve_master("What is physical activity?", top_k=1)
    except Exception as exc:
        print(f"[RAG check] Failed to query master index: {exc}")
        return

    if not chunks:
        print("[RAG check] No slides returned for sanity query.")
        return

    print(f"[RAG check] Top slide for 'What is physical activity?': {chunks[0].label()}")
