"""
Node: Retrieval
Responsibility: Embed digital twin → query vector index → return top-k similar cases (SRS F-04)
LLM: Gemini text-embedding-004 (Google AI Studio free tier)
Vector store: ChromaDB (local, grounding corpus only)

Sprint 1: STUB — node signature defined; actual retrieval implemented via rag/index.py.
"""

from __future__ import annotations

from schemas.state import ReviewBoardState


# Requirement: F-04
# Acceptance criteria: Returns exactly k results (or fewer if corpus < k) with similarity
#                      scores attached, in under 2 seconds.
async def retrieval_node(state: ReviewBoardState) -> dict:
    """
    Retrieval Node.
    Reads: state["digital_twin"]
    Writes: state["retrieved_cases"]

    Implementation (Sprint 2):
      1. Embed digital_twin["raw_text"] via Gemini embeddings API.
      2. Query ChromaDB grounding corpus for top-k nearest neighbours.
      3. Attach cosine similarity scores to each result.
      4. Return list of HistoricalCase dicts with similarity scores.

    Config params: rag.top_k, rag.index_type (from config.yaml — never hardcoded).
    """
    # TODO (Sprint 2): Implement via rag/retrieval.py. See SRS F-04.
    raise NotImplementedError(
        "Retrieval Node not yet implemented. "
        "See SRS F-04. Scheduled for Sprint 2."
    )
