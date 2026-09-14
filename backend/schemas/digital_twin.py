"""
AIRB Digital Twin & Historical Case Schemas (Pydantic)
Implements SRS §6.1 (HistoricalCase) and F-01 (DigitalTwin).

These are the frozen schema definitions for Sprint 1.
Do NOT add or remove fields without a documented schema version bump.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Enumerations ──────────────────────────────────────────────────────────────

class OutcomeLabel(str, Enum):
    """Controlled vocabulary for case outcomes (SRS §6.1)."""
    SUCCESS = "success"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class RiskCategory(str, Enum):
    """Fixed taxonomy — no free-text categories allowed (SRS §6.3)."""
    MARKET = "Market"
    FINANCE = "Finance"
    LEGAL = "Legal"
    OPERATIONS = "Operations"
    TECHNOLOGY = "Technology"


class SplitLabel(str, Enum):
    """Dataset partition labels (SRS F-03)."""
    GROUNDING = "grounding"
    CALIBRATION = "calibration"
    TEST = "test"


# ── Digital Twin (F-01) ───────────────────────────────────────────────────────

class DigitalTwin(BaseModel):
    """
    Structured JSON representation of a startup pitch.
    Produced by the Context Router (F-01) from free-text input.
    Minimum required fields per SRS F-01; additional fields may be present
    but must not be hallucinated — missing = None, never invented.
    """
    industry: Optional[str] = Field(
        default=None,
        description="Industry sector (e.g., 'FinTech', 'HealthTech', 'SaaS')"
    )
    location: Optional[str] = Field(
        default=None,
        description="Primary operating geography"
    )
    budget: Optional[float] = Field(
        default=None,
        description="Stated budget or funding ask in USD (None if not mentioned)"
    )
    business_model_summary: Optional[str] = Field(
        default=None,
        description="2–3 sentence summary of the business model"
    )
    # Extended fields that agents may use — all Optional to prevent hallucination
    team_size: Optional[int] = Field(default=None)
    revenue_model: Optional[str] = Field(default=None)
    target_market: Optional[str] = Field(default=None)
    competitive_advantage: Optional[str] = Field(default=None)
    regulatory_environment: Optional[str] = Field(default=None)
    tech_stack: Optional[str] = Field(default=None)
    traction: Optional[str] = Field(default=None)  # e.g., "2000 MAU, 15% MoM growth"

    model_config = ConfigDict(extra="allow")  # Allow additional fields from router

    @field_validator(
        "industry",
        "location",
        "business_model_summary",
        "revenue_model",
        "target_market",
        "competitive_advantage",
        "regulatory_environment",
        "tech_stack",
        "traction",
        mode="before",
    )
    @classmethod
    def coerce_to_string(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, list):
            return ", ".join(str(item) for item in v)
        if isinstance(v, dict):
            return ", ".join(f"{k}: {val}" for k, val in v.items())
        return str(v)

    @field_validator("budget", mode="before")
    @classmethod
    def parse_budget(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.replace("$", "").replace(",", "").strip().lower()
            if s.endswith("k"):
                try:
                    return float(s[:-1]) * 1000.0
                except ValueError:
                    pass
            elif s.endswith("m"):
                try:
                    return float(s[:-1]) * 1000000.0
                except ValueError:
                    pass
            try:
                return float(s)
            except ValueError:
                return None
        return None


# ── Historical Case (SRS §6.1) ────────────────────────────────────────────────

class HistoricalCase(BaseModel):
    """
    Schema for a single historical startup case in the dataset.
    Exact schema from SRS §6.1 — no fields added or removed.
    Used for: RAG corpus ingestion, calibration set, and test set.
    """
    case_id: str = Field(description="Unique identifier for this case")
    industry: str = Field(description="Industry sector of the startup")
    outcome: OutcomeLabel = Field(description="Known outcome: success | failed | inconclusive")
    primary_risk_category: RiskCategory = Field(
        description="Single dominant risk domain (controlled vocabulary)"
    )
    root_cause_summary: str = Field(
        description="2–3 sentence root cause explanation for the outcome"
    )
    raw_text: str = Field(description="Raw narrative text about the startup case")
    split: SplitLabel = Field(description="Dataset partition: grounding | calibration | test")

    @field_validator("case_id")
    @classmethod
    def case_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("case_id must not be empty")
        return v.strip()

    @field_validator("raw_text")
    @classmethod
    def raw_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_text must not be empty")
        return v


# ── Agent Output ──────────────────────────────────────────────────────────────

class AgentOutput(BaseModel):
    """
    Return type for each domain agent (SRS F-05).
    All five agents must conform to this schema; malformed output triggers one retry.
    """
    score: float = Field(ge=0.0, le=100.0, description="Risk/feasibility score 0–100")
    claim: str = Field(description="Domain-specific assessment claim")
    cited_case_ids: list[str] = Field(
        default_factory=list,
        description="IDs of historical cases cited as evidence (must exist in retrieved set)"
    )


# ── Red Team Output (F-13) ────────────────────────────────────────────────────

class RedTeamOutput(BaseModel):
    """
    Return type for the Red Team adversarial check (SRS F-13).
    Not fused into Wi/Ci/Si — escalation only.
    """
    flag: bool = Field(description="True if a significant unconsidered risk was found")
    severity: str = Field(
        description="Risk severity: low | medium | high",
        pattern="^(low|medium|high)$"
    )
    reasoning: str = Field(description="Explanation of the flagged risk")


# ── Decision Trace (for persistence / replay — F-17) ─────────────────────────

class DecisionTrace(BaseModel):
    """
    Full auditable record of a single evaluation run.
    Stored in SQLite; returned by GET /decision/{id} and GET /replay/{id}.
    """
    evaluation_id: str
    startup_pitch: str
    digital_twin: DigitalTwin
    retrieved_case_ids: list[str]
    agent_scores: dict[str, float]
    agent_confidences: dict[str, float]
    agent_weights: dict[str, float]
    agent_claims: dict[str, str]
    agent_citations: dict[str, list[str]]
    conflict_index: float
    hitl_triggered: bool
    hitl_question: Optional[str]
    hitl_answer: Optional[str]
    hitl_ci_before: Optional[float]
    hitl_ci_after: Optional[float]
    hitl_effectiveness: Optional[float]
    final_score: float
    final_confidence: float
    final_score_uncertainty: float
    decision: str  # PROCEED | HIGH-RISK | REVIEW
    sensitivity_sweep: Optional[list[dict]]
    red_team_flag: bool
    red_team_severity: Optional[str]
    red_team_reasoning: Optional[str]
    version_info: dict
