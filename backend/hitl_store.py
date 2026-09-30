"""
Local SQLite Store — Persists HITL state and completed evaluations (F-09, F-17).
Replaces the Supabase dependency with a zero-config local database.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/store.sqlite")

def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _get_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS hitl_checkpoints (
                evaluation_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS evaluations (
                evaluation_id TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Initialize tables on module import
init_db()


# ── HITL Checkpoints (F-09) ───────────────────────────────────────────────────

async def save_hitl_state(evaluation_id: str, state_dict: dict) -> None:
    """Persist graph state to SQLite before pausing for human input."""
    logger.info(f"[{evaluation_id}] Saving HITL state to SQLite...")
    try:
        state_json = json.dumps(state_dict)
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO hitl_checkpoints (evaluation_id, state_json) VALUES (?, ?)",
                (evaluation_id, state_json)
            )
            conn.commit()
    except Exception as exc:
        logger.error(f"[{evaluation_id}] Failed to save HITL state: {exc}")
        raise

async def load_hitl_state(evaluation_id: str) -> Optional[dict]:
    """Load paused graph state from SQLite upon user response."""
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT state_json FROM hitl_checkpoints WHERE evaluation_id = ?",
                (evaluation_id,)
            ).fetchone()
            if row:
                return json.loads(row["state_json"])
            return None
    except Exception as exc:
        logger.error(f"[{evaluation_id}] Failed to load HITL state: {exc}")
        return None

async def delete_hitl_state(evaluation_id: str) -> None:
    """Delete the checkpoint once successfully resumed."""
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM hitl_checkpoints WHERE evaluation_id = ?", (evaluation_id,))
            conn.commit()
    except Exception as exc:
        logger.warning(f"[{evaluation_id}] Failed to delete HITL checkpoint: {exc}")


# ── Completed Evaluations (F-17) ───────────────────────────────────────────────

def save_evaluation_result(evaluation_id: str, result_dict: dict) -> None:
    """Persist a completed evaluation trace to SQLite."""
    try:
        result_json = json.dumps(result_dict)
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO evaluations (evaluation_id, result_json) VALUES (?, ?)",
                (evaluation_id, result_json)
            )
            conn.commit()
    except Exception as exc:
        logger.error(f"[{evaluation_id}] Failed to save evaluation result: {exc}")

def load_evaluation_result(evaluation_id: str) -> Optional[dict]:
    """Load a completed evaluation trace from SQLite."""
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT result_json FROM evaluations WHERE evaluation_id = ?",
                (evaluation_id,)
            ).fetchone()
            if row:
                return json.loads(row["result_json"])
            return None
    except Exception as exc:
        logger.error(f"[{evaluation_id}] Failed to load evaluation result: {exc}")
        return None
