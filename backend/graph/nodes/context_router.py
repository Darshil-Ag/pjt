"""
Node: Context Router
Responsibility: Parse free-text startup pitch → DigitalTwin JSON (SRS F-01)
LLM: Gemini 3.6 Flash (Google AI Studio free tier)
"""

from __future__ import annotations

import logging
from google import genai
from google.genai import types as genai_types

from config import Config
from schemas.digital_twin import DigitalTwin
from schemas.state import ReviewBoardState

logger = logging.getLogger(__name__)


# Requirement: F-01
# Acceptance criteria: For 20 sample pitches, all 4 mandatory fields populated;
#                      no hallucinated fields outside defined schema.
async def context_router_node(state: ReviewBoardState) -> dict:
    """
    Context Router Node.
    Reads: state["startup_pitch"]
    Writes: state["digital_twin"]
    """
    from progress import update_stage
    eval_id = state.get("evaluation_id", "")
    update_stage(eval_id, "context_router")

    pitch = state.get("startup_pitch", "").strip()
    if not pitch:
        raise ValueError("startup_pitch in state is empty.")

    api_key = Config.llm.google_api_key
    if not api_key or "your_google_api_key_here" in api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not configured or contains placeholder 'your_google_api_key_here'."
        )

    client = genai.Client(api_key=api_key)

    prompt = (
        "You are the Context Router for AIRB, an AI pitch evaluation system.\n"
        "Parse the following startup pitch into a structured JSON matching the DigitalTwin schema.\n"
        "Fields to extract if present: industry, location, budget (float in USD), business_model_summary, "
        "team_size (int), revenue_model, target_market, competitive_advantage, regulatory_environment, tech_stack, traction.\n"
        "Rule: Do NOT invent or hallucinate missing information. If a field is not mentioned or unclear, set it to null.\n\n"
        f"Pitch:\n{pitch}"
    )

    model_name = Config.llm.router_model
    logger.info(f"[{eval_id}] Calling Gemini API ({model_name}) asynchronously for context routing...")

    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        dt = DigitalTwin.model_validate_json(response.text)
        return {"digital_twin": dt.model_dump()}
    except Exception as exc:
        logger.error(f"[{eval_id}] Context Router Gemini call failed: {exc}")
        raise

