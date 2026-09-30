"""
Node: Sensitivity Sweep (SRS F-14) — FULLY IMPLEMENTED
Responsibility: Perturb each agent's weight by ±10% and re-run fusion math to show
                how stable/fragile the final decision is.

This is pure deterministic Python — zero LLM calls.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from config import Config
from schemas.state import ReviewBoardState

logger = logging.getLogger(__name__)

DOMAINS = ["Finance", "Legal", "Market", "Operations", "Technology"]
PERTURBATIONS = [-0.20, -0.10, 0.0, +0.10, +0.20]  # ±20%, ±10%, baseline


def _fuse(
    scores: dict[str, float],
    confidences: dict[str, float],
    weights: dict[str, float],
    tau_approve: float,
    tau_confidence: float,
) -> dict:
    """Run the fusion math for a given weight assignment."""
    active = [d for d in scores if d in confidences and d in weights]
    if not active:
        return {"final_score": None, "final_confidence": 0.0, "decision": "REVIEW"}

    numerator = sum(weights[d] * confidences[d] * scores[d] for d in active)
    denominator = sum(weights[d] * confidences[d] for d in active)

    if denominator == 0:
        return {"final_score": None, "final_confidence": 0.0, "decision": "REVIEW"}

    final_score = numerator / denominator
    c_final = denominator

    if c_final < tau_confidence:
        decision = "REVIEW"
    elif final_score >= tau_approve:
        decision = "PROCEED"
    else:
        decision = "HIGH-RISK"

    return {"final_score": round(final_score, 2), "final_confidence": round(c_final, 4), "decision": decision}


def _renormalize_weights(
    base_weights: dict[str, float],
    perturbed_domain: str,
    delta: float,
) -> dict[str, float]:
    """
    Perturb one domain's weight by `delta` (absolute) and renormalize the rest
    so all weights still sum to 1.0.
    """
    new_w = dict(base_weights)
    new_w[perturbed_domain] = max(0.0, new_w[perturbed_domain] + delta)

    # Renormalize
    total = sum(new_w.values())
    if total == 0:
        return base_weights
    return {d: round(w / total, 6) for d, w in new_w.items()}


# Requirement: F-14
def sensitivity_sweep_node(state: ReviewBoardState) -> dict:
    """
    Sensitivity Sweep Node.
    For each domain, perturbs its weight by ±20%, ±10%, and baseline (0%),
    re-runs fusion math each time, and records the resulting Final_Score and decision.

    Reads:  state["agent_scores"], state["agent_confidences"], state["agent_weights"]
    Writes: state["sensitivity_sweep"]

    Output schema:
    {
        "by_domain": {
            "Finance": [
                {"delta_pct": -20, "weight": 0.17, "final_score": 61.3, "decision": "HIGH-RISK"},
                ...
            ],
            ...
        },
        "baseline": {"final_score": 68.5, "decision": "PROCEED"},
        "decision_flips": ["Finance", "Market"]  # domains where a flip occurred
    }
    """
    from progress import update_stage
    update_stage(state.get("evaluation_id", ""), "sensitivity_sweep")

    scores = state.get("agent_scores", {})
    confidences = state.get("agent_confidences", {})
    weights = state.get("agent_weights", {})

    if not scores or not weights:
        return {"sensitivity_sweep": None}

    tau_approve = Config.thresholds.tau_approve
    tau_confidence = Config.thresholds.tau_confidence

    # Baseline result
    baseline = _fuse(scores, confidences, weights, tau_approve, tau_confidence)

    by_domain: dict[str, list] = {}
    decision_flips: list[str] = []

    for domain in [d for d in DOMAINS if d in weights]:
        domain_series = []
        flipped = False
        base_weight = weights[domain]

        for delta_pct in [-20, -10, 0, +10, +20]:
            delta_abs = base_weight * (delta_pct / 100.0)
            perturbed_weights = _renormalize_weights(weights, domain, delta_abs)
            result = _fuse(scores, confidences, perturbed_weights, tau_approve, tau_confidence)

            domain_series.append({
                "delta_pct": delta_pct,
                "weight": round(perturbed_weights[domain], 4),
                "final_score": result["final_score"],
                "decision": result["decision"],
            })

            if delta_pct != 0 and result["decision"] != baseline["decision"]:
                flipped = True

        by_domain[domain] = domain_series
        if flipped:
            decision_flips.append(domain)

    sweep_result = {
        "baseline": baseline,
        "by_domain": by_domain,
        "decision_flips": decision_flips,
    }

    logger.info(
        f"[{state.get('evaluation_id', '')}] Sensitivity sweep complete. "
        f"Baseline={baseline['final_score']}, decision_flips={decision_flips}"
    )
    return {"sensitivity_sweep": sweep_result}
