"""
Node: Context Router
Responsibility: Parse free-text startup pitch → DigitalTwin JSON (SRS F-01)
LLM: Gemini 2.5 Flash (Google AI Studio free tier)

Sprint 1: STUB — schema and node signature defined; logic implemented in Sprint 2.
"""

from __future__ import annotations

from schemas.state import ReviewBoardState


# Requirement: F-01
# Acceptance criteria: For 20 sample pitches, all 4 mandatory fields populated;
#                      no hallucinated fields outside defined schema.
async def context_router_node(state: ReviewBoardState) -> dict:
    """
    Context Router Node.
    Reads: state["startup_pitch"]
    Writes: state["digital_twin"]

    Implementation (Sprint 2):
      1. Call Gemini 2.5 Flash with a structured extraction prompt.
      2. Parse response into DigitalTwin Pydantic model.
      3. Serialize to dict and return.
      4. Missing fields → None (never hallucinate). Validate via Pydantic.
    """
    # TODO (Sprint 2): Implement via Gemini API call. See SRS F-01.
    raise NotImplementedError(
        "Context Router not yet implemented. "
        "See SRS F-01. Scheduled for Sprint 2."
    )
