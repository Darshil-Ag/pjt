"""
Node: HITL Pause & Question Generator (SRS F-09)
Responsibility: When Conflict Index > theta_conflict, generate a targeted clarifying
                question for the founder and persist full state to Supabase before
                suspending graph execution.

LLM: Gemini 3.6 Flash — question generation only (Groq is for the 5 worker agents).

Persistence (F-09 hard gate):
  State is written to Supabase BEFORE this function returns. A server restart between
  HITL pause and /hitl-respond resume will NOT lose the evaluation state.
  See hitl_store.py for the Supabase integration details.

HITL resume path:
  POST /hitl-respond → _resume_evaluation() in routes.py
  → loads state from Supabase, merges answer, calls parallel_dispatch again.
  The resume path is handled in routes.py, not here.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from config import Config
from schemas.state import ReviewBoardState

logger = logging.getLogger(__name__)

DOMAINS = ["Finance", "Legal", "Market", "Operations", "Technology"]

# Map the most-conflicting domain to the DigitalTwin field most likely driving it.
# These are the fields that HITL answers will be merged into (hitl_triggered_variable).
# Chosen to match actual DigitalTwin schema fields (schemas/digital_twin.py).
DOMAIN_TO_FIELD: dict[str, str] = {
    "Finance": "traction",                  # Revenue / growth traction most Finance-critical
    "Legal": "regulatory_environment",      # Regulatory exposure drives Legal conflict
    "Market": "target_market",              # Market definition drives Market conflict
    "Operations": "team_size",              # Team capacity is the core Operations signal
    "Technology": "tech_stack",             # Technology choice drives Technology conflict
}

_HITL_QUESTION_PROMPT = """\
Two investment board specialists disagree most sharply on this startup:

- {domain_low} specialist gives it {score_low}/100 and says: "{claim_low}"
- {domain_high} specialist gives it {score_high}/100 and says: "{claim_high}"

The likely source of disagreement is the startup's {triggered_field}.

Generate ONE concise, direct clarifying question to ask the founder that would give the board
the specific information needed to resolve this disagreement.
Requirements:
- Specific to this startup's situation (not a generic question)
- Single question only — not a list
- Plain English, no jargon
- Answerable in 2-3 sentences by the founder

Return ONLY the question text. No JSON, no preamble, no labels."""


async def _generate_hitl_question(
    domain_low: str,
    score_low: float,
    claim_low: str,
    domain_high: str,
    score_high: float,
    claim_high: str,
    triggered_field: str,
    eval_id: str,
) -> str:
    """Generate a targeted clarifying question via Gemini (F-09)."""
    from google import genai

    client = genai.Client(api_key=Config.llm.google_api_key)
    prompt = _HITL_QUESTION_PROMPT.format(
        domain_low=domain_low,
        score_low=int(score_low),
        claim_low=claim_low or f"low {domain_low} viability",
        domain_high=domain_high,
        score_high=int(score_high),
        claim_high=claim_high or f"high {domain_high} viability",
        triggered_field=triggered_field.replace("_", " "),
    )

    try:
        response = await client.aio.models.generate_content(
            model=Config.llm.router_model,
            contents=prompt,
        )
        question = response.text.strip().strip('"\'')
        logger.info(f"[{eval_id}] HITL question generated: {question!r}")
        return question
    except Exception as exc:
        # Fallback to a deterministic question if Gemini fails
        fallback = (
            f"The board is divided on your startup's {triggered_field.replace('_', ' ')}. "
            f"The {domain_low} specialist rated it {int(score_low)}/100 while the {domain_high} "
            f"specialist rated it {int(score_high)}/100. "
            f"Can you provide more detail about your {triggered_field.replace('_', ' ')}?"
        )
        logger.warning(f"[{eval_id}] Gemini HITL question failed ({exc}), using fallback.")
        return fallback


# ── hitl_node ─────────────────────────────────────────────────────────────────

# Requirement: F-09
# Acceptance criteria: Graph state survives a server restart between pause and resume.
#                      Verified by: restart Render service mid-pause → POST /hitl-respond
#                      → evaluation completes (Supabase checkpoint still present).
async def hitl_node(state: ReviewBoardState) -> dict:
    """
    HITL Node.
    Reads: state["agent_scores"], state["agent_claims"], state["digital_twin"]
    Writes: state["hitl_pending"], state["hitl_question"], state["hitl_triggered_variable"]

    Side effects (ordered — must not reorder):
      1. Identify two most-conflicting agents (by score spread).
      2. Map conflict domain to DigitalTwin field (DOMAIN_TO_FIELD).
      3. Generate targeted clarifying question via Gemini.
      4. Persist FULL state to Supabase (F-09 hard gate).
      5. Update progress store to hitl_pending with the question.
      6. Return — graph suspends until POST /hitl-respond.
    """
    from progress import update_stage, mark_hitl_pending
    from hitl_store import save_hitl_state

    eval_id = state.get("evaluation_id", "")
    update_stage(eval_id, "hitl")

    scores = state.get("agent_scores", {})
    claims = state.get("agent_claims", {})

    # ── Step 1: Identify most-conflicting agent pair ──────────────────────────
    if len(scores) >= 2:
        sorted_by_score = sorted(scores.items(), key=lambda x: x[1])
        domain_low, score_low = sorted_by_score[0]
        domain_high, score_high = sorted_by_score[-1]
    elif len(scores) == 1:
        only_domain = list(scores.keys())[0]
        domain_low, score_low = only_domain, list(scores.values())[0]
        domain_high, score_high = domain_low, score_low
    else:
        domain_low, score_low = "Finance", 30.0
        domain_high, score_high = "Market", 70.0

    # ── Step 2: Map to DigitalTwin field ─────────────────────────────────────
    triggered_field = DOMAIN_TO_FIELD.get(domain_low, "business_model_summary")
    logger.info(
        f"[{eval_id}] HITL triggered. Conflict: {domain_low}={score_low:.0f} vs "
        f"{domain_high}={score_high:.0f}. Triggered field: {triggered_field}"
    )

    # ── Step 3: Generate question via Gemini ──────────────────────────────────
    question = await _generate_hitl_question(
        domain_low=domain_low,
        score_low=score_low,
        claim_low=claims.get(domain_low, ""),
        domain_high=domain_high,
        score_high=score_high,
        claim_high=claims.get(domain_high, ""),
        triggered_field=triggered_field,
        eval_id=eval_id,
    )

    # ── Step 4: Persist state to Supabase (F-09 blocker) ─────────────────────
    # Build the state snapshot to persist — includes the HITL fields we're about to return.
    state_snapshot = dict(state)
    state_snapshot["hitl_pending"] = True
    state_snapshot["hitl_question"] = question
    state_snapshot["hitl_triggered_variable"] = triggered_field
    state_snapshot["hitl_ci_before"] = float(
        state.get("variance_history", [0.0])[-1]
        if state.get("variance_history") else 0.0
    )

    persisted = await save_hitl_state(eval_id, state_snapshot)
    if not persisted:
        logger.critical(
            f"[{eval_id}] F-09 VIOLATED: HITL state not persisted to Supabase. "
            "Evaluation CANNOT survive a server restart. Configure SUPABASE_URL and SUPABASE_KEY."
        )

    # ── Step 5: Update progress store ────────────────────────────────────────
    mark_hitl_pending(eval_id, hitl_question=question)

    return {
        "hitl_pending": True,
        "hitl_question": question,
        "hitl_triggered_variable": triggered_field,
        "hitl_ci_before": state_snapshot["hitl_ci_before"],
    }


# ── hitl_resume_node (called from routes._resume_evaluation) ─────────────────

def hitl_resume_node(state: dict, answer: str) -> dict:
    """
    Merge HITL answer into the digital twin and increment round_count.
    This is a SYNCHRONOUS utility called from routes._resume_evaluation —
    not registered as a LangGraph node directly (resume is handled in routes.py).

    Reads: state["hitl_triggered_variable"], state["digital_twin"], state["round_count"]
    Writes: state["digital_twin"] (updated), state["hitl_pending"] (False),
            state["hitl_answer"], state["round_count"] (incremented)
    """
    triggered_field = state.get("hitl_triggered_variable")
    digital_twin = dict(state.get("digital_twin", {}))

    if triggered_field:
        digital_twin[triggered_field] = answer
        logger.info(
            f"[{state.get('evaluation_id', '')}] HITL answer merged: "
            f"{triggered_field!r} = {answer!r}"
        )
    else:
        logger.warning("hitl_triggered_variable is None — answer not merged into digital_twin.")

    return {
        "digital_twin": digital_twin,
        "hitl_pending": False,
        "hitl_answer": answer,
        "round_count": state.get("round_count", 0) + 1,
    }
