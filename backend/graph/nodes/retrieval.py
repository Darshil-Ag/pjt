"""
Node: Retrieval
Responsibility: Embed digital twin → query vector index → return top-k similar cases (SRS F-04)
LLM: Default Local ChromaDB Embedding (all-MiniLM-L6-v2)
Vector store: ChromaDB (local, grounding corpus only)
"""

from __future__ import annotations

import logging

from config import Config
from rag.index import retrieve
from schemas.state import ReviewBoardState

logger = logging.getLogger(__name__)


# Requirement: F-04
# Acceptance criteria: Returns exactly k results (or fewer if corpus < k) with similarity
#                      scores attached, in under 2 seconds.
async def retrieval_node(state: ReviewBoardState) -> dict:
    """
    Retrieval Node.
    Reads: state["digital_twin"] or state["startup_pitch"]
    Writes: state["retrieved_cases"]
    """
    from progress import update_stage
    eval_id = state.get("evaluation_id", "")
    update_stage(eval_id, "retrieval")

    dt = state.get("digital_twin", {}) or {}
    query_text = (
        f"{dt.get('industry', '')} {dt.get('business_model_summary', '')} {dt.get('target_market', '')}".strip()
        or state.get("startup_pitch", "")
    )

    logger.info(f"[{eval_id}] Executing retrieval node for query text...")
    # Using local embeddings means this is fast enough to run synchronously 
    retrieved_cases = retrieve(query_text, k=Config.rag.top_k)
    return {"retrieved_cases": retrieved_cases}
