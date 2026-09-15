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

    F-16 note: On the post-HITL re-evaluation round (detected by hitl_answer being set
    in state), this node captures hitl_ci_after = new CI and computes
    hitl_effectiveness = hitl_ci_before − hitl_ci_after.
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

    result: dict = {
        "variance_history": variance_history,
        "conflict_detected": ci > Config.thresholds.theta_conflict,
        # Preserve or update hitl_ci_before
        "hitl_ci_before": ci if ci > Config.thresholds.theta_conflict else state.get("hitl_ci_before"),
    }

    # ── F-16: HITL Effectiveness ─────────────────────────────────────────────
    # Detect post-HITL round: hitl_answer has been merged but hitl_ci_after not yet recorded.
    # Condition: hitl_answer is set (answer was submitted) AND hitl_ci_after not yet captured.
    hitl_ci_before = state.get("hitl_ci_before")
    if (
        state.get("hitl_answer") is not None
        and hitl_ci_before is not None
        and state.get("hitl_ci_after") is None
    ):
        hitl_ci_after = ci
        hitl_effectiveness = round(hitl_ci_before - hitl_ci_after, 4)
        result["hitl_ci_after"] = hitl_ci_after
        result["hitl_effectiveness"] = hitl_effectiveness
        import logging as _log
        _log.getLogger(__name__).info(
            f"[{state.get('evaluation_id', '')}] F-16 HITL Effectiveness: "
            f"CI_before={hitl_ci_before:.2f}, CI_after={hitl_ci_after:.2f}, "
            f"effectiveness={hitl_effectiveness:.4f}"
        )

    return result


def route_after_conflict(state: ReviewBoardState) -> str:
    """
    Conditional edge: routes to 'hitl' or 'fusion' based on conflict_detected.
    Also respects max_rounds to prevent infinite HITL loops.
    Per SRS F-08: routing threshold is strictly >, not >=.
    """
    max_rounds = state.get("max_rounds", 1)
    round_count = state.get("round_count", 0)
    conflict_detected = state.get("conflict_detected", False)
    if conflict_detected and round_count < max_rounds:
        return "hitl"
    return "fusion"
