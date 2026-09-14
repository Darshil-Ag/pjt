"""
AIRB LangGraph State Machine
Full pipeline topology — Architecture Doc §3 (Component Diagram) and §4 (Data Flow).

Node order:
  Context Router → Retrieval → Parallel Dispatch → Conflict Index
     ↓ (CI > θ)                              ↓ (CI ≤ θ or max_rounds hit)
  HITL Node ──── (resume) ──► Parallel Dispatch (re-run)
                                              ↓
                                        Fusion Node
                                              ↓
                                   Sensitivity Sweep (if HITL occurred)
                                              ↓
                                       Red Team Check
                                              ↓
                                     Evaluation Logger
                                              ↓
                                           END

Sprint 1 status:
  - Topology: FULLY WIRED (all 9 nodes connected)
  - conflict_index_node + route_after_conflict: IMPLEMENTED
  - fusion_node: IMPLEMENTED
  - evaluation_logger_node: PARTIALLY IMPLEMENTED (version_info; no DB yet)
  - All other nodes: STUB (raise NotImplementedError with SRS reference)
"""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.graph import StateGraph, END

# Checkpointer for HITL pause/resume (SRS F-09).
# Imported lazily so node unit tests don't require SQLite at import time.
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    SqliteSaver = None  # type: ignore[assignment,misc]

from config import Config
from schemas.state import ReviewBoardState, initial_state
from graph.nodes import (
    context_router_node,
    retrieval_node,
    parallel_dispatch_node,
    conflict_index_node,
    route_after_conflict,
    hitl_node,
    fusion_node,
    sensitivity_sweep_node,
    red_team_node,
    evaluation_logger_node,
)


def _route_after_sensitivity(state: ReviewBoardState) -> str:
    """Always proceed to red_team after sweep (sweep may be no-op if no HITL)."""
    return "red_team"


def build_graph() -> StateGraph:
    """
    Construct and compile the AIRB LangGraph StateGraph.
    The SQLite checkpointer enables HITL pause/resume across server restarts (SRS F-09).
    """
    workflow = StateGraph(ReviewBoardState)

    # ── Register Nodes ────────────────────────────────────────────────────────
    workflow.add_node("context_router", context_router_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("parallel_dispatch", parallel_dispatch_node)
    workflow.add_node("conflict_index", conflict_index_node)
    workflow.add_node("hitl", hitl_node)
    workflow.add_node("fusion", fusion_node)
    workflow.add_node("sensitivity_sweep", sensitivity_sweep_node)
    workflow.add_node("red_team", red_team_node)
    workflow.add_node("evaluation_logger", evaluation_logger_node)

    # ── Entry Point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("context_router")

    # ── Static Edges ──────────────────────────────────────────────────────────
    workflow.add_edge("context_router", "retrieval")
    workflow.add_edge("retrieval", "parallel_dispatch")
    workflow.add_edge("parallel_dispatch", "conflict_index")

    # ── Conditional Routing: Conflict Index → HITL or Fusion ─────────────────
    workflow.add_conditional_edges(
        "conflict_index",
        route_after_conflict,
        {
            "hitl": "hitl",
            "fusion": "fusion",
        },
    )

    # After HITL question is generated, graph pauses. On resume, re-run agents.
    # hitl_resume logic is handled inside the HITL node via the checkpointer.
    workflow.add_edge("hitl", END)  # Graph suspends here; resumed by POST /hitl-respond

    # ── Fusion → Sensitivity → Red Team → Logger → END ───────────────────────
    workflow.add_edge("fusion", "sensitivity_sweep")
    workflow.add_edge("sensitivity_sweep", "red_team")
    workflow.add_edge("red_team", "evaluation_logger")
    workflow.add_edge("evaluation_logger", END)

    return workflow


def get_compiled_graph(checkpointer: Any = None):
    """
    Compile the graph with an optional checkpointer.
    For HITL persistence (SRS F-09), pass a SqliteSaver checkpointer.
    """
    workflow = build_graph()
    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()


def create_evaluation_run(
    startup_pitch: str,
) -> tuple[ReviewBoardState, str]:
    """
    Factory: initialize a new evaluation run with a unique evaluation_id.
    Returns (initial_state, evaluation_id).
    """
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
    state = initial_state(startup_pitch, evaluation_id, version_info)
    return state, evaluation_id
