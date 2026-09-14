"""
Node: Sensitivity Sweep
Responsibility: After HITL resolution, re-run fusion across a small range of values
                for ONLY the digital-twin variable that triggered the conflict (SRS F-14)

Sprint 1: STUB — node signature defined; logic implemented Sprint 3.
"""

from __future__ import annotations

from schemas.state import ReviewBoardState


# Requirement: F-14
# Acceptance criteria:
#   - Only the one HITL-triggering variable varies across sweep points.
#   - At least one constructed case shows a decision flip within swept range.
#   - num_points is configurable (config.sensitivity.num_points).
def sensitivity_sweep_node(state: ReviewBoardState) -> dict:
    """
    Sensitivity Sweep Node — runs only when HITL was triggered in this evaluation.
    Reads: state["hitl_triggered_variable"], state["digital_twin"],
           state["agent_weights"], state["agent_confidences"]
    Writes: state["sensitivity_sweep"]

    Implementation (Sprint 3):
      1. Read hitl_triggered_variable to identify the swept field.
      2. Determine sweep range (configurable: Config.sensitivity.num_points values).
      3. For each value in range:
         a. Patch digital_twin[hitl_triggered_variable] = swept_value
         b. Re-run fusion math (deterministic, no LLM) with current weights/confidences.
         c. Record {variable_value, final_score, decision}
      4. Store results in state["sensitivity_sweep"].
      5. If HITL was NOT triggered, this node is bypassed (routing handles this).

    IMPORTANT: Only the one variable changes across sweep iterations.
               This is NOT a full grid search (BRD §4.2 stretch feature).
    """
    # Skip if no HITL was triggered in this run
    if not state.get("conflict_detected") or not state.get("hitl_triggered_variable"):
        return {"sensitivity_sweep": None}

    # TODO (Sprint 3): Implement sweep over hitl_triggered_variable range. See SRS F-14.
    raise NotImplementedError(
        "Sensitivity Sweep Node not yet implemented. "
        "See SRS F-14. Scheduled for Sprint 3."
    )
