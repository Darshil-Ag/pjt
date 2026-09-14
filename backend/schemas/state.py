"""
AIRB LangGraph State Schema (TypedDict)
Implements SRS §6.2 — ReviewBoardState.

CRITICAL: This TypedDict is the single source of truth for all inter-node
state in LangGraph. Do not add or remove fields without a schema version bump
and a corresponding update to the versioning config. Every node reads from
and writes back to this one object — no side-channel passing.
"""

from __future__ import annotations

from typing import Optional, TypedDict


class ReviewBoardState(TypedDict):
    """
    Full LangGraph state object — exact field list from SRS §6.2.
    No additions. No deletions. Comments cite the relevant SRS requirement.
    """

    # ── Input ──────────────────────────────────────────────────────────────────
    startup_pitch: str                          # Raw free-text pitch from user

    # ── Context Router output (F-01) ──────────────────────────────────────────
    digital_twin: dict                          # DigitalTwin as dict after Pydantic parse

    # ── Retrieval output (F-04) ───────────────────────────────────────────────
    retrieved_cases: list[dict]                 # List of HistoricalCase dicts (top-k)

    # ── Iteration control ─────────────────────────────────────────────────────
    round_count: int                            # How many agent evaluation rounds have run
    max_rounds: int                             # Maximum rounds before forced resolution

    # ── Agent outputs (F-05) ──────────────────────────────────────────────────
    agent_scores: dict[str, float]             # Si — {domain: score 0-100}
    agent_confidences: dict[str, float]        # Ci — {domain: confidence 0-1}
    agent_weights: dict[str, float]            # Wi — {domain: calibrated weight}
    agent_claims: dict[str, str]               # {domain: claim string}
    agent_citations: dict[str, list]           # {domain: [cited_case_ids]}

    # ── Conflict detection (F-08) ─────────────────────────────────────────────
    variance_history: list[float]              # CI values across rounds
    conflict_detected: bool                    # True if CI > theta_conflict

    # ── HITL (F-09) ───────────────────────────────────────────────────────────
    hitl_pending: bool                         # True while waiting for user response
    hitl_question: Optional[str]               # Clarifying question sent to user
    hitl_answer: Optional[str]                 # User's response (merged into digital_twin)
    hitl_triggered_variable: Optional[str]     # Digital-twin field that caused the conflict

    # ── Fusion output (F-10) ──────────────────────────────────────────────────
    final_score: Optional[float]               # Weighted fused score
    final_confidence: Optional[float]          # C_final = sum(Wi*Ci)
    decision: Optional[str]                    # PROCEED | HIGH-RISK | REVIEW

    # ── Red Team (F-13) ───────────────────────────────────────────────────────
    red_team_flag: bool                        # True if Red Team flagged a risk
    red_team_severity: Optional[str]           # low | medium | high | None
    red_team_reasoning: Optional[str]          # Red Team's explanation

    # ── Sensitivity Sweep (F-14) ──────────────────────────────────────────────
    sensitivity_sweep: Optional[list[dict]]    # [{variable_value, final_score, decision}]

    # ── Uncertainty Band (F-15) ───────────────────────────────────────────────
    final_score_uncertainty: Optional[float]   # Confidence-weighted spread

    # ── HITL Effectiveness (F-16) ─────────────────────────────────────────────
    hitl_ci_before: Optional[float]            # CI immediately before HITL question
    hitl_ci_after: Optional[float]             # CI immediately after answer incorporated
    hitl_effectiveness: Optional[float]        # CI_before − CI_after

    # ── Reproducibility (F-17) ────────────────────────────────────────────────
    evaluation_id: str                         # Unique ID for this run
    version_info: dict                         # model/prompt/rag_index/dataset/weights/thresholds


def initial_state(startup_pitch: str, evaluation_id: str, version_info: dict) -> ReviewBoardState:
    """
    Factory function: returns a fully-initialized ReviewBoardState with safe defaults.
    Call this at the start of every new LangGraph run.
    """
    return ReviewBoardState(
        startup_pitch=startup_pitch,
        digital_twin={},
        retrieved_cases=[],
        round_count=0,
        max_rounds=1,  # Default: allow at most 1 HITL re-evaluation round
        agent_scores={},
        agent_confidences={},
        agent_weights={},
        agent_claims={},
        agent_citations={},
        variance_history=[],
        conflict_detected=False,
        hitl_pending=False,
        hitl_question=None,
        hitl_answer=None,
        hitl_triggered_variable=None,
        final_score=None,
        final_confidence=None,
        decision=None,
        red_team_flag=False,
        red_team_severity=None,
        red_team_reasoning=None,
        sensitivity_sweep=None,
        final_score_uncertainty=None,
        hitl_ci_before=None,
        hitl_ci_after=None,
        hitl_effectiveness=None,
        evaluation_id=evaluation_id,
        version_info=version_info,
    )
