"""
AIRB FastAPI Routes (SRS §5 — External Interface Requirements)

Endpoints:
  POST /evaluate               — Submit pitch; returns immediately with status "queued";
                                 graph runs as background asyncio task
  GET  /status/{id}            — Poll live pipeline progress (per-node + per-agent)
  POST /hitl-respond           — Submit HITL answer, resume graph execution
  GET  /decision/{id}          — Get full decision trace for a completed evaluation
  GET  /replay/{id}            — Return stored trace without re-invoking any LLM (F-17)

Sprint 1:
  - POST /evaluate: returns "queued" immediately; background task is wired but
    graph nodes still raise NotImplementedError until Sprint 2, so the task will
    transition to "error" state. Progress store + /status polling is fully functional.
  - GET /status/{id}: IMPLEMENTED — returns live progress including per-agent status.
  - All other routes: stubbed.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from config import Config
from schemas.state import initial_state
import progress as prog

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    startup_pitch: str


class EvaluateResponse(BaseModel):
    evaluation_id: str
    status: str  # "queued" | "running" | "hitl_pending" | "complete" | "error"
    message: str


class StatusAgentEntry(BaseModel):
    status: str        # "pending" | "running" | "complete" | "error"
    score: Optional[float] = None   # set once agent is complete


class StatusResponse(BaseModel):
    evaluation_id: str
    status: str        # "queued" | "running" | "hitl_pending" | "complete" | "error"
    current_stage: Optional[str]
    stages_completed: list[str]
    agent_status: dict[str, StatusAgentEntry]
    error_message: Optional[str]
    updated_at: str


class HITLRespondRequest(BaseModel):
    evaluation_id: str
    answer: str


class HITLRespondResponse(BaseModel):
    evaluation_id: str
    status: str
    message: str


# ── Background Graph Runner ───────────────────────────────────────────────────

async def _run_evaluation(evaluation_id: str, startup_pitch: str) -> None:
    """
    Background coroutine: builds the LangGraph state and invokes the full pipeline.
    Updates the progress store at every step. Transitions to "error" if any node
    raises (expected in Sprint 1 since stub nodes raise NotImplementedError).

    Sprint 2: replace the NotImplementedError stubs in each node with real logic;
              this runner requires no changes — it will automatically work end-to-end.
    """
    try:
        version_info = {
            "model_worker": Config.llm.worker_model,
            "model_router": Config.llm.router_model,
            "prompt_template_version": Config.versioning.prompt_template_version,
            "rag_index_version": Config.versioning.rag_index_version,
            "dataset_version": Config.versioning.dataset_version,
            "weight_calibration_version": Config.versioning.weight_calibration_version,
            "thresholds": {
                "theta_conflict": Config.thresholds.theta_conflict,
                "tau_approve": Config.thresholds.tau_approve,
                "tau_confidence": Config.thresholds.tau_confidence,
            },
        }
        state = initial_state(startup_pitch, evaluation_id, version_info)

        # Sprint 2: replace with:
        #   from graph.graph import get_compiled_graph
        #   from langgraph.checkpoint.sqlite import SqliteSaver
        #   checkpointer = SqliteSaver(Config.sqlite_db_path)
        #   graph = get_compiled_graph(checkpointer=checkpointer)
        #   await graph.ainvoke(state, config={"configurable": {"thread_id": evaluation_id}})

        # Sprint 1: directly call nodes that are implemented; others will raise NotImplementedError.
        # The progress store transitions to "error" cleanly in that case.
        from graph.nodes import (
            context_router_node,
            retrieval_node,
            parallel_dispatch_node,
            conflict_index_node,
            fusion_node,
            sensitivity_sweep_node,
            red_team_node,
            evaluation_logger_node,
        )

        # Each await propagates state updates into the progress store via update_stage().
        state.update(await context_router_node(state))
        state.update(await retrieval_node(state))
        state.update(await parallel_dispatch_node(state))
        state.update(conflict_index_node(state))

        from graph.nodes.conflict_index import route_after_conflict
        from graph.nodes.hitl import hitl_node
        if route_after_conflict(state) == "hitl":
            state.update(await hitl_node(state))
            prog.mark_hitl_pending(evaluation_id)
            return  # Paused; resumed via POST /hitl-respond

        state.update(fusion_node(state))
        state.update(sensitivity_sweep_node(state))
        state.update(await red_team_node(state))
        state.update(evaluation_logger_node(state))

        prog.mark_complete(evaluation_id)
        logger.info(f"Evaluation completed: {evaluation_id}")

    except NotImplementedError as exc:
        # Expected in Sprint 1 — stub nodes raise this
        msg = f"Stub node not yet implemented: {exc}"
        logger.warning(f"[{evaluation_id}] {msg}")
        prog.mark_error(evaluation_id, msg)
    except Exception:
        msg = traceback.format_exc()
        logger.error(f"[{evaluation_id}] Evaluation error:\n{msg}")
        prog.mark_error(evaluation_id, msg)


# ── POST /evaluate ─────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluateResponse, tags=["Evaluation"])
async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """
    Submit a startup pitch for evaluation.

    Returns immediately with status "queued" — the full LangGraph pipeline
    runs as a background asyncio task. Poll GET /status/{evaluation_id} for
    live per-node and per-agent progress.

    Sprint 1: graph nodes are stubs (NotImplementedError); the task will
              transition to status "error" once it hits the first stub.
    Sprint 2: full pipeline executes end-to-end.
    """
    if not request.startup_pitch.strip():
        raise HTTPException(status_code=422, detail="startup_pitch must not be empty.")

    evaluation_id = str(uuid.uuid4())

    # Write initial progress row BEFORE launching the task so GET /status
    # can return data immediately after this response is sent.
    prog.create_progress(evaluation_id)

    # asyncio.create_task() schedules the coroutine on the running event loop.
    # We MUST hold a reference to the task — without it, the GC can collect the
    # task mid-run (a known asyncio footgun). prog.register_task() stores it.
    task = asyncio.create_task(
        _run_evaluation(evaluation_id, request.startup_pitch.strip()),
        name=f"eval-{evaluation_id}",
    )
    prog.register_task(evaluation_id, task)

    logger.info(f"Evaluation queued: {evaluation_id}")
    return EvaluateResponse(
        evaluation_id=evaluation_id,
        status="queued",
        message="Evaluation queued. Poll GET /status/{evaluation_id} for live progress.",
    )


# ── GET /status/{evaluation_id} ───────────────────────────────────────────────

@router.get("/status/{evaluation_id}", response_model=StatusResponse, tags=["Evaluation"])
async def get_status(evaluation_id: str) -> StatusResponse:
    """
    Return live pipeline progress for an evaluation.

    Response includes:
      - status: overall pipeline state
      - current_stage: which node is active right now
      - stages_completed: ordered list of finished nodes
      - agent_status: per-domain-agent {status, score} — updates as each
        parallel agent finishes, not as a single batch
      - error_message: populated if status == "error"
    """
    row = prog.get_progress(evaluation_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id!r} not found.")

    agent_status = {
        domain: StatusAgentEntry(**entry)
        for domain, entry in row["agent_status"].items()
    }

    return StatusResponse(
        evaluation_id=row["evaluation_id"],
        status=row["status"],
        current_stage=row["current_stage"],
        stages_completed=row["stages_completed"],
        agent_status=agent_status,
        error_message=row["error_message"],
        updated_at=row["updated_at"],
    )


# ── POST /hitl-respond ────────────────────────────────────────────────────────

@router.post("/hitl-respond", response_model=HITLRespondResponse, tags=["HITL"])
async def hitl_respond(request: HITLRespondRequest) -> HITLRespondResponse:
    """
    Submit a user's answer to the HITL clarifying question.
    Resumes the paused LangGraph execution for this evaluation.

    Sprint 1 (stub): Returns acknowledgement.
    Sprint 2: Loads checkpoint from SQLite, injects answer, resumes graph.

    Acceptance criterion (SRS F-09): Graph state must survive a server restart
    between pause (POST /evaluate triggering HITL) and resume (this endpoint).
    """
    if not request.evaluation_id or not request.answer.strip():
        raise HTTPException(status_code=422, detail="evaluation_id and answer are required.")

    logger.info(f"HITL response received for evaluation: {request.evaluation_id}")

    # TODO (Sprint 2): Load checkpoint from SQLite, merge answer into digital_twin,
    #                  call graph.ainvoke() to resume. See SRS F-09.

    return HITLRespondResponse(
        evaluation_id=request.evaluation_id,
        status="running",
        message="HITL answer received. Graph resume available in Sprint 2.",
    )


# ── GET /decision/{id} ────────────────────────────────────────────────────────

@router.get("/decision/{evaluation_id}", tags=["Evaluation"])
async def get_decision(evaluation_id: str) -> dict:
    """
    Retrieve the full decision trace for a completed evaluation.
    Includes all agent scores, weights, confidences, claims, citations,
    conflict index, HITL details, final score, uncertainty band, and Red Team output.

    Sprint 1 (stub): Returns placeholder.
    Sprint 2/3: Loads DecisionTrace from SQLite by evaluation_id.

    Acceptance criterion (SRS F-11): Every figure shown in the UI must be
    traceable to a value in this response — no UI-invented numbers.
    """
    logger.info(f"Decision requested for: {evaluation_id}")

    # TODO (Sprint 2/3): Load DecisionTrace from SQLite. See SRS F-17.

    return {
        "evaluation_id": evaluation_id,
        "status": "stub",
        "message": "Decision trace retrieval available in Sprint 2/3.",
    }


# ── GET /replay/{id} ─────────────────────────────────────────────────────────

@router.get("/replay/{evaluation_id}", tags=["Reproducibility"])
async def replay_evaluation(evaluation_id: str) -> dict:
    """
    Return the exact stored trace for a past evaluation — WITHOUT re-invoking any LLM.

    Acceptance criterion (SRS F-17): Zero live LLM calls; output identical to original run.

    Sprint 1 (stub): Returns placeholder.
    Sprint 3: Loads and returns stored DecisionTrace from SQLite.
    """
    logger.info(f"Replay requested for: {evaluation_id}",)

    # TODO (Sprint 3): Load stored DecisionTrace from SQLite. See SRS F-17.
    # IMPORTANT: No LLM calls may occur in this function — it reads stored data only.

    return {
        "evaluation_id": evaluation_id,
        "status": "stub",
        "message": "Replay endpoint available in Sprint 3.",
    }
