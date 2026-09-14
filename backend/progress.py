"""
AIRB In-Memory Progress Store
Tracks pipeline execution status per evaluation_id, including per-agent status and score.

IMPORTANT — Single-worker assumption:
  This module uses a plain Python dict. It works correctly only when the application
  runs as a single process (Render free tier: single worker, single process).
  If Render ever scales to multiple workers/processes (e.g. gunicorn -w 4), each
  process will have an independent dict and /status/{id} requests may hit the wrong
  process, returning 404. To fix at that point: replace this dict with Redis or SQLite.
  Do not remove this comment when upgrading.

Task-handle safety:
  asyncio.create_task() without storing a reference to the Task object is a footgun —
  the garbage collector can collect the task mid-run if nothing holds a reference.
  We store task handles in _running_tasks keyed by evaluation_id. Call
  discard_task(evaluation_id) from the route once the task completes or errors.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

# ── Internal stores ───────────────────────────────────────────────────────────

_PROGRESS: dict[str, dict] = {}
_running_tasks: dict[str, "asyncio.Task[None]"] = {}

DOMAINS = ["Finance", "Legal", "Market", "Operations", "Technology"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _initial_agent_status() -> dict[str, dict]:
    """Each agent entry: {status, score}. status ∈ pending|running|complete|error."""
    return {d: {"status": "pending", "score": None} for d in DOMAINS}


# ── Public API ────────────────────────────────────────────────────────────────

def create_progress(evaluation_id: str) -> None:
    """
    Write an initial 'queued' progress row.
    Call this synchronously before kicking off the background task.
    """
    _PROGRESS[evaluation_id] = {
        "evaluation_id": evaluation_id,
        "status": "queued",
        "current_stage": None,
        "stages_completed": [],
        "agent_status": _initial_agent_status(),
        "error_message": None,
        "hitl_question": None,    # Populated when HITL is triggered (for frontend display)
        "result": None,           # Populated on completion — agent scores, decision, etc.
        "created_at": _now(),
        "updated_at": _now(),
    }


def update_stage(evaluation_id: str, stage: str) -> None:
    """
    Mark a pipeline stage as the active stage.
    Appends the *previous* current_stage to stages_completed (if any).
    Safe to call even if evaluation_id is missing (logs a warning silently).
    """
    row = _PROGRESS.get(evaluation_id)
    if not row:
        return
    prev = row.get("current_stage")
    if prev and prev not in row["stages_completed"]:
        row["stages_completed"].append(prev)
    row["current_stage"] = stage
    row["status"] = "running"
    row["updated_at"] = _now()


def update_agent_status(
    evaluation_id: str,
    domain: str,
    status: str,
    score: Optional[float] = None,
) -> None:
    """
    Update a single domain agent's status and optionally its score.
    status ∈ "pending" | "running" | "complete" | "error"
    score  — set when status="complete", None otherwise.

    This lets the frontend show a checkmark + score preview per agent
    as soon as each agent finishes (not waiting for all 5 to complete).
    """
    row = _PROGRESS.get(evaluation_id)
    if not row or domain not in row["agent_status"]:
        return
    row["agent_status"][domain]["status"] = status
    if score is not None:
        row["agent_status"][domain]["score"] = round(score, 1)
    row["updated_at"] = _now()


def mark_hitl_pending(evaluation_id: str, hitl_question: str = "") -> None:
    """Pause state — graph is waiting for user HITL response. Stores the question for frontend."""
    row = _PROGRESS.get(evaluation_id)
    if not row:
        return
    row["status"] = "hitl_pending"
    if hitl_question:
        row["hitl_question"] = hitl_question
    row["updated_at"] = _now()


def mark_complete(evaluation_id: str) -> None:
    """Terminal success state."""
    row = _PROGRESS.get(evaluation_id)
    if not row:
        return
    # Flush current_stage into completed list
    current = row.get("current_stage")
    if current and current not in row["stages_completed"]:
        row["stages_completed"].append(current)
    row["status"] = "complete"
    row["updated_at"] = _now()
    discard_task(evaluation_id)


def mark_error(evaluation_id: str, error_message: str) -> None:
    """Terminal failure state."""
    row = _PROGRESS.get(evaluation_id)
    if not row:
        return
    row["status"] = "error"
    row["error_message"] = error_message
    row["updated_at"] = _now()
    discard_task(evaluation_id)


def store_result(evaluation_id: str, result: dict) -> None:
    """
    Store the final evaluation result in the progress row so GET /decision/{id}
    can return it without SQLite (Sprint 3 will persist to DB instead).
    Call this BEFORE mark_complete.
    """
    row = _PROGRESS.get(evaluation_id)
    if not row:
        return
    row["result"] = result
    row["updated_at"] = _now()


def get_progress(evaluation_id: str) -> Optional[dict]:
    """Return the progress dict, or None if not found."""
    return _PROGRESS.get(evaluation_id)


# ── Task reference management ─────────────────────────────────────────────────

def register_task(evaluation_id: str, task: "asyncio.Task[None]") -> None:
    """
    Store a hard reference to the asyncio Task so the GC cannot collect it.
    Must be called immediately after asyncio.create_task().
    """
    _running_tasks[evaluation_id] = task


def discard_task(evaluation_id: str) -> None:
    """Release the task reference once the run is done (success or failure)."""
    _running_tasks.pop(evaluation_id, None)
