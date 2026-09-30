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
        logger.warning(
            f"[{eval_id}] Context Router Gemini call failed ({exc}). "
            "Falling back to Groq (llama-3.3-70b) for digital twin extraction..."
        )
        return await _context_router_groq_fallback(pitch, eval_id)


async def _context_router_groq_fallback(pitch: str, eval_id: str) -> dict:
    """
    Fallback Context Router using Groq when Gemini is unavailable (503, quota, etc.).
    Extracts the same DigitalTwin fields via JSON-mode prompt to llama-3.3-70b-versatile.
    """
    import json
    from groq import AsyncGroq

    groq_prompt = (
        "You are an AI that extracts structured startup information from a pitch text.\n"
        "Return ONLY valid JSON matching this schema (use null for missing fields):\n"
        '{"industry": str|null, "location": str|null, "budget": float|null, '
        '"business_model_summary": str|null, "team_size": int|null, '
        '"revenue_model": str|null, "target_market": str|null, '
        '"competitive_advantage": str|null, "regulatory_environment": str|null, '
        '"tech_stack": str|null, "traction": str|null}\n\n'
        f"PITCH:\n{pitch}\n\n"
        "Return ONLY the JSON object, no markdown, no explanation."
    )

    try:
        client = AsyncGroq(api_key=Config.llm.groq_api_key)
        response = await client.chat.completions.create(
            model=Config.llm.worker_model,
            messages=[{"role": "user", "content": groq_prompt}],
            temperature=0.1,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:].strip()
        data = json.loads(raw)
        dt = DigitalTwin.model_validate(data)
        logger.info(f"[{eval_id}] Groq fallback context router succeeded: {dt.model_dump()}")
        return {"digital_twin": dt.model_dump()}
    except Exception as fallback_exc:
        logger.error(
            f"[{eval_id}] Groq fallback also failed ({fallback_exc}). "
            "Using minimal digital twin with raw pitch as business_model_summary."
        )
        # Last-resort: return a minimal twin so the pipeline can still run
        dt = DigitalTwin.model_validate({
            "industry": None,
            "location": None,
            "budget": None,
            "business_model_summary": pitch[:500],
            "team_size": None,
            "revenue_model": None,
            "target_market": None,
            "competitive_advantage": None,
            "regulatory_environment": None,
            "tech_stack": None,
            "traction": None,
        })
        return {"digital_twin": dt.model_dump()}
