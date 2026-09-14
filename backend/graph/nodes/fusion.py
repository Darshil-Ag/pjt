"""
Node: Fusion + Decision
Responsibility: Compute Final_Score, C_final, uncertainty band; classify decision (SRS F-10, F-15)
This is PURELY deterministic Python — no LLM call.

Sprint 1: Core fusion MATH is implemented here (pure Python/NumPy, no LLM).
          All thresholds come from Config (never hardcoded).
"""

from __future__ import annotations

import numpy as np

from config import Config
from schemas.state import ReviewBoardState

DOMAINS = ["Finance", "Legal", "Market", "Operations", "Technology"]


# Requirement: F-10 (fusion + decision), F-15 (uncertainty band)
# Acceptance criteria (F-10): All three decision classes reachable; thresholds configurable.
# Acceptance criteria (F-15): Two cases with same Final_Score but different score spread
#                             produce different uncertainty bands.
def fusion_node(state: ReviewBoardState) -> dict:
    """
    Fusion Node.
    Reads: state["agent_scores"], state["agent_confidences"], state["agent_weights"]
    Writes: state["final_score"], state["final_confidence"],
            state["final_score_uncertainty"], state["decision"]

    Formula (SRS F-10):
        Final_Score = Σ(Wi * Ci * Si) / Σ(Wi * Ci)
        C_final     = Σ(Wi * Ci)          [unnormalized; used for abstention check]

    Decision classification (SRS F-10):
        PROCEED   — Final_Score >= tau_approve  (AND C_final >= tau_confidence)
        HIGH-RISK — Final_Score <  tau_approve  AND C_final >= tau_confidence
        REVIEW    — C_final < tau_confidence    (abstain; evidence too weak)

    Uncertainty band (SRS F-15):
        Heuristic: confidence-weighted spread of individual agent scores.
        band = sqrt( Σ(Wi*Ci*(Si - Final_Score)^2) / Σ(Wi*Ci) )
        Documented as distinct from ablation bootstrap CIs — never conflate.
    """
    scores = state["agent_scores"]
    confidences = state["agent_confidences"]
    weights = state["agent_weights"]

    if not scores:
        # Degrade gracefully if all agents failed (NF-05)
        return {
            "final_score": None,
            "final_confidence": 0.0,
            "final_score_uncertainty": None,
            "decision": "REVIEW",
        }

    # Compute fusion over available agents (handles partial failures per NF-05)
    active_domains = [d for d in scores if d in confidences and d in weights]
    
    numerator = 0.0
    denominator = 0.0
    for d in active_domains:
        wi = weights[d]
        ci = confidences[d]
        si = scores[d]
        numerator += wi * ci * si
        denominator += wi * ci

    if denominator == 0:
        return {
            "final_score": None,
            "final_confidence": 0.0,
            "final_score_uncertainty": None,
            "decision": "REVIEW",
        }

    final_score = numerator / denominator
    c_final = denominator

    # Uncertainty band (F-15) — confidence-weighted variance of individual scores
    variance_sum = sum(
        weights[d] * confidences[d] * (scores[d] - final_score) ** 2
        for d in active_domains
    )
    uncertainty = float(np.sqrt(variance_sum / denominator))

    # Decision classification (F-10) — strictly per config thresholds
    tau_approve = Config.thresholds.tau_approve
    tau_confidence = Config.thresholds.tau_confidence

    if c_final < tau_confidence:
        decision = "REVIEW"          # Abstain: evidence too weak
    elif final_score >= tau_approve:
        decision = "PROCEED"
    else:
        decision = "HIGH-RISK"

    return {
        "final_score": round(final_score, 4),
        "final_confidence": round(c_final, 4),
        "final_score_uncertainty": round(uncertainty, 4),
        "decision": decision,
    }
