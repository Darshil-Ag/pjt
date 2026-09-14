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


def _remove_additional_properties(schema: any) -> any:
    """Recursively strip 'additionalProperties' to comply with Gemini Developer API mode requirements."""
    if isinstance(schema, dict):
        return {
            k: _remove_additional_properties(v)
            for k, v in schema.items()
            if k != "additionalProperties"
        }
    if isinstance(schema, list):
        return [_remove_additional_properties(item) for item in schema]
    return schema


def get_gemini_digital_twin_schema() -> dict:
    """Return a Gemini Developer API compatible JSON schema dict for DigitalTwin."""
    return _remove_additional_properties(DigitalTwin.model_json_schema())


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
        "Extract structured startup information from the provided pitch into the DigitalTwin schema.\n"
        "Fields to extract if present: industry, location, budget (float in USD), business_model_summary, "
        "team_size (int), revenue_model, target_market, competitive_advantage, regulatory_environment, tech_stack, traction.\n"
        "Rules:\n"
        "- Do NOT invent or hallucinate missing information.\n"
        "- Extract all details that ARE explicitly stated or directly inferable from the pitch.\n"
        "- If a field is not mentioned or unclear, set it to null.\n\n"
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
                response_schema=get_gemini_digital_twin_schema(),
            ),
        )
        raw_text = response.text.strip() if response and response.text else "{}"
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        import json
        data = json.loads(raw_text)
        if isinstance(data, dict):
            if "digital_twin" in data and isinstance(data["digital_twin"], dict):
                data = data["digital_twin"]
            elif "DigitalTwin" in data and isinstance(data["DigitalTwin"], dict):
                data = data["DigitalTwin"]
            elif "result" in data and isinstance(data["result"], dict):
                data = data["result"]
            dt = DigitalTwin.model_validate(data)
        else:
            dt = DigitalTwin.model_validate_json(raw_text)

        logger.info(f"[{eval_id}] Context router extracted digital twin: {dt.model_dump()}")
        return {"digital_twin": dt.model_dump()}
    except Exception as exc:
        logger.error(f"[{eval_id}] Context Router Gemini call failed: {exc}")
        raise

