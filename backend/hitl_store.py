"""
HITL Checkpoint Store — Supabase persistence (SRS F-09).

Why Supabase instead of local SQLite:
  Render's free tier uses EPHEMERAL disk — local SQLite is wiped on every deploy/restart.
  F-09's acceptance criterion explicitly requires graph state to survive a server restart
  between the HITL pause and resume. Supabase free tier (Postgres) is the zero-cost,
  restart-proof alternative named in the Architecture Doc §7.

Table schema (run once in Supabase SQL editor):
    CREATE TABLE IF NOT EXISTS hitl_checkpoints (
        evaluation_id TEXT PRIMARY KEY,
        state_json    JSONB NOT NULL,
        created_at    TIMESTAMPTZ DEFAULT NOW()
    );

Usage:
    await save_hitl_state(eval_id, state_dict)   # before suspending
    await load_hitl_state(eval_id)               # on resume (may be after restart)
    await delete_hitl_state(eval_id)             # after resume completes
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from config import Config

logger = logging.getLogger(__name__)

# ── Lazy singleton client ─────────────────────────────────────────────────────

_supabase_client = None


def _get_client():
    """
    Lazily initialize the Supabase client.
    Returns None (with a logged error) if SUPABASE_URL / SUPABASE_KEY are not set.
    This lets the app start locally without Supabase configured — the HITL path
    will log a CRITICAL error if it is actually reached without credentials.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = Config.llm.supabase_url
    key = Config.llm.supabase_key

    if not url or not key or "your-project" in url or "your_supabase" in key:
        logger.warning(
            "SUPABASE_URL / SUPABASE_KEY not configured. "
            "HITL persistence (F-09) will be unavailable. "
            "Set these in .env or Render environment variables."
        )
        return None

    try:
        from supabase import create_client  # type: ignore[import]
        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized (HITL persistence active).")
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase client: {exc}")
        return None

    return _supabase_client


# ── Public API ────────────────────────────────────────────────────────────────

async def save_hitl_state(evaluation_id: str, state: dict) -> bool:
    """
    Persist the full evaluation state to Supabase before graph suspension.

    This is the F-09 persistence guarantee: state is written to Postgres
    before hitl_node returns, so a server restart does not lose the checkpoint.

    Returns True on success, False on failure (caller should log and surface the error).
    """
    client = _get_client()
    if client is None:
        logger.critical(
            f"[{evaluation_id}] HITL state NOT persisted: Supabase unconfigured. "
            "F-09 acceptance criterion VIOLATED — evaluation cannot survive server restart."
        )
        return False

    # Sanitize state: remove non-serializable objects, convert to JSON-safe dict
    safe_state = _make_serializable(state)
    payload = {
        "evaluation_id": evaluation_id,
        "state_json": safe_state,  # Supabase JSONB column accepts dict directly
    }

    def _upsert() -> None:
        client.table("hitl_checkpoints").upsert(payload, on_conflict="evaluation_id").execute()

    try:
        await asyncio.to_thread(_upsert)
        logger.info(f"[{evaluation_id}] HITL state persisted to Supabase. F-09 satisfied.")
        return True
    except Exception as exc:
        logger.critical(f"[{evaluation_id}] Supabase upsert failed: {exc}. F-09 VIOLATED.")
        return False


async def load_hitl_state(evaluation_id: str) -> Optional[dict]:
    """
    Load the persisted evaluation state from Supabase on resume.
    Returns the state dict, or None if not found or Supabase is unavailable.
    """
    client = _get_client()
    if client is None:
        return None

    def _select():
        return (
            client.table("hitl_checkpoints")
            .select("state_json")
            .eq("evaluation_id", evaluation_id)
            .maybe_single()
            .execute()
        )

    try:
        result = await asyncio.to_thread(_select)
        if result.data is None:
            logger.warning(f"[{evaluation_id}] No HITL checkpoint found in Supabase.")
            return None
        state_json = result.data.get("state_json")
        if isinstance(state_json, str):
            return json.loads(state_json)
        return state_json  # Supabase JSONB returns dict directly
    except Exception as exc:
        logger.error(f"[{evaluation_id}] Supabase load failed: {exc}")
        return None


async def delete_hitl_state(evaluation_id: str) -> None:
    """
    Remove the checkpoint after successful resume (clean up Supabase table).
    Non-fatal if this fails — the checkpoint will just be orphaned.
    """
    client = _get_client()
    if client is None:
        return

    def _delete() -> None:
        client.table("hitl_checkpoints").delete().eq("evaluation_id", evaluation_id).execute()

    try:
        await asyncio.to_thread(_delete)
        logger.info(f"[{evaluation_id}] HITL checkpoint deleted from Supabase.")
    except Exception as exc:
        logger.warning(f"[{evaluation_id}] Failed to delete HITL checkpoint: {exc}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _make_serializable(obj):
    """
    Recursively convert a dict/list to a JSON-serializable form.
    Handles sets, Pydantic models, and any object with __dict__.
    """
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(i) for i in obj]
    if isinstance(obj, set):
        return [_make_serializable(i) for i in sorted(obj)]
    if hasattr(obj, "model_dump"):
        return _make_serializable(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return _make_serializable(obj.__dict__)
    return obj
