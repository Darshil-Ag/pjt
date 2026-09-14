"""
AIRB FastAPI Routes (SRS §5 — External Interface Requirements)

Endpoints:
  POST /evaluate               — Submit pitch; returns immediately with status "queued";
                                 graph runs as background asyncio task
  GET  /status/{id}            — Poll live pipeline progress (per-node + per-agent)
  POST /hitl-respond           — Submit HITL answer; loads Supabase checkpoint, resumes graph
  GET  /decision/{id}          — Get full decision trace for a completed evaluation
  GET  /replay/{id}            — Return stored trace without re-invoking any LLM (F-17)

Sprint 2:
  - POST /evaluate: full end-to-end pipeline (context router → parallel dispatch →
    conflict index → [HITL or] fusion → sensitivity sweep → red team → logger)
  - GET /status/{id}: returns live progress + per-agent scores + hitl_question
  - POST /hitl-respond: IMPLEMENTED — loads Supabase checkpoint, merges answer,
    resumes pipeline from parallel dispatch (F-09 hard gate satisfied)
  - GET /decision/{id}: returns full decision trace from in-memory result store
    (SQLite persistence deferred to Sprint 3)
  - GET /replay/{id}: stub (Sprint 3)
"""

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
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
    hitl_question: Optional[str] = None   # populated when status == "hitl_pending"
    error_message: Optional[str]
    updated_at: str


class HITLRespondRequest(BaseModel):
    evaluation_id: str
    answer: str


class HITLRespondResponse(BaseModel):
    evaluation_id: str
    status: str
    message: str


class DecisionResponse(BaseModel):
    evaluation_id: str
    decision: Optional[str]          # PROCEED | HIGH-RISK | REVIEW
    final_score: Optional[float]
    final_confidence: Optional[float]
    final_score_uncertainty: Optional[float]
    digital_twin: dict = {}          # Extracted DigitalTwin dict (F-01)
    retrieved_cases: list[dict] = []  # Extracted retrieved historical cases (F-04)
    retrieved_case_ids: list[str] = [] # List of retrieved case IDs for UI evidence count
    agent_scores: dict[str, float]
    agent_claims: dict[str, str]
    agent_weights: dict[str, float]
    agent_confidences: dict[str, float]
    agent_citations: dict[str, list]
    conflict_detected: bool
    variance_history: list[float]
    red_team_flag: bool
    red_team_severity: Optional[str]
    red_team_reasoning: Optional[str]
    hitl_triggered: bool
    hitl_question: Optional[str]
    hitl_answer: Optional[str]
    version_info: dict


# ── Node imports (lazy, inside functions, to avoid circular imports) ──────────

def _import_nodes():
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
    from graph.nodes.conflict_index import route_after_conflict
    from graph.nodes.hitl import hitl_node, hitl_resume_node
    return (
        context_router_node, retrieval_node, parallel_dispatch_node,
        conflict_index_node, route_after_conflict, hitl_node, hitl_resume_node,
        fusion_node, sensitivity_sweep_node, red_team_node, evaluation_logger_node,
    )


# ── Background Graph Runner ───────────────────────────────────────────────────

async def _run_evaluation(evaluation_id: str, startup_pitch: str) -> None:
    """
    Background coroutine: builds the LangGraph state and invokes the full pipeline.

    Pipeline: context_router → retrieval → parallel_dispatch → conflict_index
                → [hitl if CI > theta] | [fusion → sensitivity_sweep → red_team → logger]

    On HITL trigger: persists state to Supabase and suspends. Resumed via POST /hitl-respond.
    On any node error: transitions to "error" in progress store (NF-05 graceful degradation).
    """
    (
        context_router_node, retrieval_node, parallel_dispatch_node,
        conflict_index_node, route_after_conflict, hitl_node, hitl_resume_node,
        fusion_node, sensitivity_sweep_node, red_team_node, evaluation_logger_node,
    ) = _import_nodes()

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

        # ── Sprint 2 pipeline (manual sequential calls — LangGraph.ainvoke wired in Sprint 3) ──
        state.update(await context_router_node(state))
        state.update(await retrieval_node(state))
        state.update(await parallel_dispatch_node(state))
        state.update(conflict_index_node(state))

        if route_after_conflict(state) == "hitl":
            # HITL path: hitl_node persists state to Supabase before returning
            state.update(await hitl_node(state))
            # Progress store already updated to hitl_pending inside hitl_node
            return  # Suspended — resumed via POST /hitl-respond

        await _run_post_fusion(evaluation_id, state, fusion_node, sensitivity_sweep_node,
                               red_team_node, evaluation_logger_node)

    except Exception:
        msg = traceback.format_exc()
        logger.error(f"[{evaluation_id}] Evaluation error:\n{msg}")
        prog.mark_error(evaluation_id, msg)


async def _resume_evaluation(evaluation_id: str, state: dict) -> None:
    """
    Resume pipeline from parallel_dispatch after a HITL answer is submitted.
    Called after loading the checkpoint from Supabase and merging the answer.

    This function satisfies F-09's round-trip requirement:
      POST /evaluate → [HITL pause] → server restart → POST /hitl-respond → complete
    """
    (
        _, _, parallel_dispatch_node, conflict_index_node, route_after_conflict,
        hitl_node, _, fusion_node, sensitivity_sweep_node, red_team_node, evaluation_logger_node,
    ) = _import_nodes()

    try:
        # Re-run agents with the updated digital_twin (hitl_answer already merged by caller)
        state.update(await parallel_dispatch_node(state))
        state.update(conflict_index_node(state))

        if route_after_conflict(state) == "hitl":
            # Another round of conflict (respects max_rounds guard in route_after_conflict)
            state.update(await hitl_node(state))
            # Progress already marked hitl_pending inside hitl_node
            return

        await _run_post_fusion(evaluation_id, state, fusion_node, sensitivity_sweep_node,
                               red_team_node, evaluation_logger_node)

    except Exception:
        msg = traceback.format_exc()
        logger.error(f"[{evaluation_id}] Resume error:\n{msg}")
        prog.mark_error(evaluation_id, msg)


async def _run_post_fusion(
    evaluation_id: str,
    state: dict,
    fusion_node,
    sensitivity_sweep_node,
    red_team_node,
    evaluation_logger_node,
) -> None:
    """
    Shared tail of the pipeline: fusion → sensitivity_sweep → red_team → logger.
    Used by both the initial run and HITL resume path.
    """
    from progress import update_stage

    state.update(fusion_node(state))
    state.update(sensitivity_sweep_node(state))
    state.update(await red_team_node(state))
    state.update(evaluation_logger_node(state))

    # Build result snapshot for GET /decision/{id} (Sprint 3 will persist to SQLite instead)
    result = {
        "decision": state.get("decision"),
        "final_score": state.get("final_score"),
        "final_confidence": state.get("final_confidence"),
        "final_score_uncertainty": state.get("final_score_uncertainty"),
        "digital_twin": state.get("digital_twin", {}),
        "retrieved_cases": state.get("retrieved_cases", []),
        "retrieved_case_ids": [
            c["case_id"] for c in state.get("retrieved_cases", []) if isinstance(c, dict) and "case_id" in c
        ],
        "agent_scores": state.get("agent_scores", {}),
        "agent_claims": state.get("agent_claims", {}),
        "agent_weights": state.get("agent_weights", {}),
        "agent_confidences": state.get("agent_confidences", {}),
        "agent_citations": state.get("agent_citations", {}),
        "conflict_detected": state.get("conflict_detected", False),
        "variance_history": state.get("variance_history", []),
        "red_team_flag": state.get("red_team_flag", False),
        "red_team_severity": state.get("red_team_severity"),
        "red_team_reasoning": state.get("red_team_reasoning"),
        "hitl_triggered": bool(state.get("hitl_answer")),
        "hitl_question": state.get("hitl_question"),
        "hitl_answer": state.get("hitl_answer"),
        "version_info": state.get("version_info", {}),
    }
    prog.store_result(evaluation_id, result)
    prog.mark_complete(evaluation_id)
    logger.info(
        f"[{evaluation_id}] Evaluation complete. "
        f"Decision={result['decision']}, Score={result['final_score']}"
    )


# ── POST /evaluate ─────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluateResponse, tags=["Evaluation"])
async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """
    Submit a startup pitch for evaluation.

    Returns immediately with status "queued" — the full LangGraph pipeline
    runs as a background asyncio task. Poll GET /status/{evaluation_id} for
    live per-node and per-agent progress.
    """
    if not request.startup_pitch.strip():
        raise HTTPException(status_code=422, detail="startup_pitch must not be empty.")

    evaluation_id = str(uuid.uuid4())

    # Write initial progress row BEFORE launching the task
    prog.create_progress(evaluation_id)

    # asyncio.create_task() + register_task() prevents GC collecting the task mid-run
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
      - agent_status: per-domain-agent {status, score} — updates as each parallel agent finishes
      - hitl_question: populated when status == "hitl_pending" (show in frontend form)
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
        hitl_question=row.get("hitl_question"),
        error_message=row.get("error_message"),
        updated_at=row["updated_at"],
    )


# ── POST /hitl-respond ────────────────────────────────────────────────────────

@router.post("/hitl-respond", response_model=HITLRespondResponse, tags=["HITL"])
async def hitl_respond(request: HITLRespondRequest) -> HITLRespondResponse:
    """
    Submit a user's answer to the HITL clarifying question.

    F-09 implementation:
      1. Load full evaluation state from Supabase checkpoint (survives server restart)
      2. Merge answer into digital_twin via hitl_resume_node
      3. Delete the Supabase checkpoint (clean up)
      4. Resume pipeline as a new background task from parallel_dispatch

    Acceptance criterion (SRS F-09): Graph state must survive a server restart between
    pause and resume — verified by actually restarting Render service mid-pause and
    confirming /hitl-respond still finds the Supabase checkpoint.
    """
    from graph.nodes.hitl import hitl_resume_node
    from hitl_store import load_hitl_state, delete_hitl_state

    if not request.evaluation_id or not request.answer.strip():
        raise HTTPException(status_code=422, detail="evaluation_id and answer are required.")

    eval_id = request.evaluation_id

    # Step 1: Load checkpoint from Supabase (the key F-09 operation)
    state = await load_hitl_state(eval_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No HITL checkpoint found for evaluation {eval_id!r}. "
                "Either the evaluation hasn't paused for HITL yet, or the Supabase "
                "checkpoint expired/was never written (check SUPABASE_URL/KEY config)."
            ),
        )

    # Step 2: Merge answer into state
    state.update(hitl_resume_node(state, request.answer.strip()))
    logger.info(f"[{eval_id}] HITL answer merged. round_count={state.get('round_count', 1)}")

    # Step 3: Delete the checkpoint — re-created if HITL triggers again
    await delete_hitl_state(eval_id)

    # Step 4: Re-initialize progress store (may have been lost if server restarted)
    if prog.get_progress(eval_id) is None:
        prog.create_progress(eval_id)
        logger.info(f"[{eval_id}] Progress store re-initialized after server restart.")

    # Step 5: Resume pipeline as a new background task
    resume_task = asyncio.create_task(
        _resume_evaluation(eval_id, state),
        name=f"resume-{eval_id}",
    )
    prog.register_task(eval_id, resume_task)

    return HITLRespondResponse(
        evaluation_id=eval_id,
        status="running",
        message=(
            f"HITL answer accepted. Pipeline resuming from parallel dispatch. "
            f"Poll GET /status/{eval_id} for live progress."
        ),
    )


# ── GET /decision/{evaluation_id} ────────────────────────────────────────────

@router.get("/decision/{evaluation_id}", response_model=DecisionResponse, tags=["Evaluation"])
async def get_decision(evaluation_id: str) -> DecisionResponse:
    """
    Retrieve the full decision trace for a completed evaluation.
    Includes all agent scores, weights, confidences, claims, citations,
    conflict index, HITL details, final score, uncertainty band, and Red Team output.

    Sprint 2: Reads from in-memory result store (progress.py store_result).
    Sprint 3: Will load from SQLite evaluation_traces table (F-17 full persistence).

    Acceptance criterion (SRS F-11): Every figure shown in the UI is traceable
    to a value in this response — no UI-invented numbers.
    """
    row = prog.get_progress(evaluation_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id!r} not found.")

    if row["status"] != "complete":
        raise HTTPException(
            status_code=409,
            detail=f"Evaluation is not yet complete (status: {row['status']!r}). "
                   "Poll GET /status/{evaluation_id} and retry when status == 'complete'.",
        )

    result = row.get("result")
    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Evaluation marked complete but result data is missing. This is a bug.",
        )

    return DecisionResponse(
        evaluation_id=evaluation_id,
        decision=result.get("decision"),
        final_score=result.get("final_score"),
        final_confidence=result.get("final_confidence"),
        final_score_uncertainty=result.get("final_score_uncertainty"),
        digital_twin=result.get("digital_twin", {}),
        retrieved_cases=result.get("retrieved_cases", []),
        retrieved_case_ids=result.get("retrieved_case_ids", []),
        agent_scores=result.get("agent_scores", {}),
        agent_claims=result.get("agent_claims", {}),
        agent_weights=result.get("agent_weights", {}),
        agent_confidences=result.get("agent_confidences", {}),
        agent_citations=result.get("agent_citations", {}),
        conflict_detected=result.get("conflict_detected", False),
        variance_history=result.get("variance_history", []),
        red_team_flag=result.get("red_team_flag", False),
        red_team_severity=result.get("red_team_severity"),
        red_team_reasoning=result.get("red_team_reasoning"),
        hitl_triggered=result.get("hitl_triggered", False),
        hitl_question=result.get("hitl_question"),
        hitl_answer=result.get("hitl_answer"),
        version_info=result.get("version_info", {}),
    )


# ── GET /replay/{evaluation_id} ───────────────────────────────────────────────

@router.get("/replay/{evaluation_id}", tags=["Reproducibility"])
async def replay_evaluation(evaluation_id: str) -> dict:
    """
    Return the exact stored trace for a past evaluation — WITHOUT re-invoking any LLM.

    Acceptance criterion (SRS F-17): Zero live LLM calls; output identical to original run.

    Sprint 2: Returns same data as /decision/{id} (from in-memory store).
    Sprint 3: Loads and returns stored DecisionTrace from SQLite.
    IMPORTANT: No LLM calls may occur in this function — reads stored data only.
    """
    logger.info(f"Replay requested for: {evaluation_id}")

    row = prog.get_progress(evaluation_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id!r} not found.")

    result = row.get("result")
    if not result:
        raise HTTPException(
            status_code=409,
            detail=f"No stored result for {evaluation_id!r} (status: {row['status']!r}). "
                   "Replay requires a completed evaluation.",
        )

    return {"evaluation_id": evaluation_id, "replay": True, **result}
