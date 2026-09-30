"""
AIRB RAG Index Builder
Implements SRS F-04 (vector retrieval) and Architecture Doc §7 (N-decoupled design).

Responsibilities:
1. Embed grounding-corpus cases via ChromaDB's default local embeddings (all-MiniLM-L6-v2).
2. Store embeddings in ChromaDB (local, disk-backed).
3. Provide top-k retrieval by cosine similarity.

Config params (from config.yaml — NEVER hardcoded):
    rag.top_k, rag.index_type, rag.chroma_persist_dir, rag.embedding_model

Usage:
    python -m rag.index --rebuild    # Re-build index from scratch
    python -m rag.index --status     # Show index stats
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import chromadb
import chromadb.utils.embedding_functions as embedding_functions

from config import Config
from rag.ingest import load_cases_by_split, check_no_test_cases_in_index
from schemas.digital_twin import SplitLabel

logger = logging.getLogger(__name__)

# Collection name inside ChromaDB
COLLECTION_NAME = "airb_grounding_corpus"

# Use ChromaDB's default local embedding function (SentenceTransformers all-MiniLM-L6-v2)
default_ef = embedding_functions.DefaultEmbeddingFunction()


# ── ChromaDB Client ───────────────────────────────────────────────────────────

def get_chroma_client() -> chromadb.PersistentClient:
    """Get a persistent ChromaDB client (disk-backed, local)."""
    persist_dir = Config.rag.chroma_persist_dir
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def get_collection(client: Optional[chromadb.PersistentClient] = None) -> chromadb.Collection:
    """Get or create the grounding corpus collection."""
    if client is None:
        client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=default_ef,
        metadata={"hnsw:space": "cosine"},  # cosine similarity (SRS F-04)
    )


# ── Index Building ────────────────────────────────────────────────────────────

def build_index(cases_jsonl_path: Optional[str] = None, force_rebuild: bool = False) -> None:
    """
    Build or update the ChromaDB grounding corpus index.

    Only grounding-split cases are indexed. Test-set cases are NEVER indexed (F-03).
    After building, runs the F-03 hard gate check automatically.

    Args:
        cases_jsonl_path: Path to JSONL file of all cases (with split tags).
        force_rebuild: If True, clears existing index before rebuilding.
    """
    client = get_chroma_client()
    collection = get_collection(client)

    if force_rebuild:
        logger.warning("Force rebuild: deleting existing index...")
        client.delete_collection(COLLECTION_NAME)
        collection = get_collection(client)

    # Load grounding-split cases only
    jsonl_path = cases_jsonl_path or Config.dataset.raw_data_path
    grounding_cases = load_cases_by_split(SplitLabel.GROUNDING, jsonl_path)

    if not grounding_cases:
        logger.warning("No grounding cases found. Run ingest.py first.")
        return

    # Find cases not yet in the index
    existing_ids = set(collection.get(include=[])["ids"])
    new_cases = [c for c in grounding_cases if c.case_id not in existing_ids]

    if not new_cases:
        logger.info("Index is already up to date.")
    else:
        logger.info(f"Indexing {len(new_cases)} new grounding cases...")
        # ChromaDB handles embeddings automatically via the embedding_function
        collection.add(
            ids=[c.case_id for c in new_cases],
            documents=[c.raw_text for c in new_cases],
            metadatas=[
                {
                    "industry": c.industry,
                    "outcome": c.outcome.value,
                    "primary_risk_category": c.primary_risk_category.value,
                    "root_cause_summary": c.root_cause_summary,
                    "split": c.split.value,
                }
                for c in new_cases
            ],
        )
        logger.info(f"Indexed {len(new_cases)} cases. Total: {collection.count()}.")

    # F-03 HARD GATE: confirm no test cases leaked into the index
    check_no_test_cases_in_index(collection)


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(query_text: str, k: Optional[int] = None) -> list[dict]:
    """
    Retrieve top-k most similar grounding cases for a given query text.
    Uses ChromaDB default embedding function internally.
    """
    k = k or Config.rag.top_k
    collection = get_collection()

    if collection.count() == 0:
        logger.warning("ChromaDB collection is empty. Auto-building index from data/historical_cases.jsonl...")
        try:
            build_index()
        except Exception as exc:
            logger.warning(f"Auto-index build failed: {exc}")
            return []

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query_text],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    if results and results.get("ids") and len(results["ids"]) > 0:
        for i, case_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            similarity = 1.0 - (distance / 2.0)
            output.append({
                "case_id": case_id,
                "raw_text": results["documents"][0][i],
                "similarity_score": round(similarity, 6),
                **results["metadatas"][0][i],
            })
    return output


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="AIRB RAG Index")
    parser.add_argument("--rebuild", action="store_true", help="Force full index rebuild")
    parser.add_argument("--status", action="store_true", help="Show index stats")
    parser.add_argument("--input", default="data/historical_cases.jsonl")
    args = parser.parse_args()

    if args.status:
        col = get_collection()
        logger.info(f"Index '{COLLECTION_NAME}': {col.count()} documents.")
    else:
        build_index(cases_jsonl_path=args.input, force_rebuild=args.rebuild)
