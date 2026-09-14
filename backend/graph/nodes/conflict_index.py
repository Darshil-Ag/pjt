"""
Node: Conflict Index
Responsibility: Compute CI = Var(S1..S5); route to HITL if CI > theta_conflict (SRS F-08)
This is PURELY deterministic Python — no LLM call.

Sprint 1: Conflict index math is IMPLEMENTED here (it's pure Python, no LLM).
          The routing decision is also implemented.
          HITL question generation (F-09) is stubbed for Sprint 2.
"""

from __future__ import annotations

import numpy as np

from config import Config
from schemas.state import ReviewBoardState


# Requirement: F-08
# Acceptance criteria: High-variance synthetic scores always trigger HITL;
#                      low-variance scores never do. Boundary behavior documented.
def conflict_index_node(state: ReviewBoardState) -> dict:
    """
    Conflict Index Node.
    Reads: state["agent_scores"]
    Writes: state["variance_history"], state["conflict_detected"]

    The routing decision (should_go_to_hitl / should_go_to_fusion) is made by
    the conditional edge function below, not inside this node.
    """
    from progress import update_stage
    update_stage(state.get("evaluation_id", ""), "conflict_index")

    scores = list(state["agent_scores"].values())
    if not scores:
        ci = 0.0
    else:
        ci = float(np.var(scores))  # Population variance — CI = Var(S1..S5)

    variance_history = list(state.get("variance_history", []))
    variance_history.append(ci)

    return {
        "variance_history": variance_history,
        "conflict_detected": ci > Config.thresholds.theta_conflict,
        # Store for HITL effectiveness logging (F-16)
        "hitl_ci_before": ci if ci > Config.thresholds.theta_conflict else state.get("hitl_ci_before"),
    }


def route_after_conflict(state: ReviewBoardState) -> str:
    """
    Conditional edge: routes to 'hitl' or 'fusion' based on conflict_detected.
    Also respects max_rounds to prevent infinite HITL loops.
    Per SRS F-08: routing threshold is strictly >, not >=.
    """
    if state["conflict_detected"] and state["round_count"] < state["max_rounds"]:
        return "hitl"
    return "fusion"
