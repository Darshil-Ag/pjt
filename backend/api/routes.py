"""
AIRB FastAPI Routes (SRS §5 — External Interface Requirements)

Endpoints:
  POST /evaluate          — Submit a pitch, start evaluation, return evaluation_id
  POST /hitl-respond      — Submit HITL answer, resume graph execution
  GET  /decision/{id}     — Get full decision trace for a completed evaluation
  GET  /replay/{id}       — Return stored trace without re-invoking any LLM (F-17)

Sprint 1: All routes are stubbed. evaluate() creates an evaluation_id and
          initializes state; actual graph invocation is Sprint 2.
"""

from __future__ import annotations

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import Config
from schemas.state import initial_state

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    startup_pitch: str


class EvaluateResponse(BaseModel):
    evaluation_id: str
    status: str  # "running" | "hitl_pending" | "complete" | "error"
    message: str


class HITLRespondRequest(BaseModel):
    evaluation_id: str
    answer: str


class HITLRespondResponse(BaseModel):
    evaluation_id: str
    status: str
    message: str


# ── POST /evaluate ─────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluateResponse, tags=["Evaluation"])
async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    """
    Submit a startup pitch for evaluation.

    Sprint 1 (stub): Assigns evaluation_id and initializes state.
    Sprint 2: Invokes the full LangGraph pipeline asynchronously.

    Returns:
        evaluation_id: Unique identifier for this run (use with GET /decision/{id})
        status: "running" while processing; "hitl_pending" if paused for HITL
    """
    if not request.startup_pitch.strip():
        raise HTTPException(status_code=422, detail="startup_pitch must not be empty.")

    evaluation_id = str(uuid.uuid4())
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

    # Initialize state (Sprint 2: pass this to the compiled LangGraph graph)
    state = initial_state(request.startup_pitch, evaluation_id, version_info)
    logger.info(f"Evaluation started: {evaluation_id}")

    # TODO (Sprint 2): Invoke compiled graph with state; store thread_id for HITL resume.
    # graph = get_compiled_graph(checkpointer=SqliteSaver(...))
    # await graph.ainvoke(state, config={"configurable": {"thread_id": evaluation_id}})

    return EvaluateResponse(
        evaluation_id=evaluation_id,
        status="running",
        message="Evaluation initialized. Full pipeline available in Sprint 2.",
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
    The stored trace includes the full version_info snapshot (model, prompt template,
    RAG index, dataset, weight-calibration, threshold versions) needed for exact replay.
    """
    logger.info(f"Replay requested for: {evaluation_id}")

    # TODO (Sprint 3): Load stored DecisionTrace from SQLite. See SRS F-17.
    # IMPORTANT: No LLM calls may occur in this function — it reads stored data only.

    return {
        "evaluation_id": evaluation_id,
        "status": "stub",
        "message": "Replay endpoint available in Sprint 3.",
    }
