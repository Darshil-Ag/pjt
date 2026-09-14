"""
Node: Red Team Check (SRS F-13)
Responsibility: Adversarial escalation review AFTER the Decision node.
                A high-severity flag overrides the decision to REVIEW.
                Does NOT join the weighted fusion math — never a sixth vote.

LLM: Llama 3.3 70B via Groq (same tier as worker agents).

Design constraint (Architecture Doc §3):
  Red Team runs STRICTLY AFTER the Fusion/Decision node. This is deliberate —
  it is a BRAKE, not an accelerator. It can only push decisions toward REVIEW,
  never toward PROCEED. Red Team output is NEVER fed back into Wi, Ci, or Si.

Pulled into Sprint 2 rationale:
  Shared Groq infrastructure with Parallel Dispatch — no new API client needed.
  Avoids a second deploy cycle. Does not touch fusion math.
"""

from __future__ import annotations

import json
import logging

from config import Config
from schemas.state import ReviewBoardState

logger = logging.getLogger(__name__)

_RED_TEAM_PROMPT = """\
You are an adversarial reviewer stress-testing an investment board's decision on a startup.
Your job is to find the ONE most dangerous unconsidered risk — the thing the board may have missed.

STARTUP PITCH:
{pitch}

BOARD'S DECISION: {decision}

BOARD MEMBER ASSESSMENTS:
{claims_json}

Search for:
- Regulatory landmines not mentioned by the board
- Market timing risks (too early, too late, crowded)
- Founder/team execution risks not surfaced
- Technology feasibility issues
- Ethical/reputational risks

If you find a significant unconsidered risk, flag it. If the board's assessment looks comprehensive, say so.

Respond with ONLY valid JSON, no commentary, no markdown:
{{"flag": <true or false>, "severity": "<low|medium|high>", "reasoning": "<one paragraph explaining the risk or confirming board thoroughness>"}}"""


# Requirement: F-13
# Acceptance criteria:
#   - Red Team runs exactly once, after fusion, never before.
#   - High-severity flag reliably forces REVIEW in constructed test cases.
#   - Low/medium/no flag leaves original decision unchanged.
async def red_team_node(state: ReviewBoardState) -> dict:
    """
    Red Team Node.
    Reads: state["startup_pitch"], state["agent_claims"], state["decision"]
    Writes: state["red_team_flag"], state["red_team_severity"],
            state["red_team_reasoning"], state["decision"] (may override to REVIEW)

    Escalation logic:
      flag=True AND severity="high"  → override decision to "REVIEW"
      flag=True AND severity!="high" → record flag, leave decision unchanged
      flag=False                     → no change
    """
    from progress import update_stage
    from groq import AsyncGroq

    eval_id = state.get("evaluation_id", "")
    update_stage(eval_id, "red_team")

    current_decision = state.get("decision", "REVIEW")
    claims = state.get("agent_claims", {})
    startup_pitch = state.get("startup_pitch", "")

    client = AsyncGroq(api_key=Config.llm.groq_api_key)
    prompt = _RED_TEAM_PROMPT.format(
        pitch=startup_pitch,
        decision=current_decision,
        claims_json=json.dumps(claims, indent=2, default=str),
    )

    last_exc = None
    for attempt in range(2):  # One retry on malformed JSON (consistent with F-05 pattern)
        try:
            resp = await client.chat.completions.create(
                model=Config.llm.red_team_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=400,
            )
            raw = resp.choices[0].message.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            parsed = json.loads(raw)

            flag = bool(parsed["flag"])
            severity = str(parsed.get("severity", "low")).lower()
            if severity not in ("low", "medium", "high"):
                severity = "low"
            reasoning = str(parsed.get("reasoning", ""))

            # Escalation gate: high-severity only (F-13 acceptance criteria)
            final_decision = current_decision
            if flag and severity == "high":
                final_decision = "REVIEW"
                logger.warning(
                    f"[{eval_id}] Red Team overriding decision to REVIEW: {reasoning[:120]}..."
                )
            else:
                logger.info(
                    f"[{eval_id}] Red Team: flag={flag}, severity={severity}. "
                    f"Decision unchanged ({current_decision})."
                )

            return {
                "red_team_flag": flag,
                "red_team_severity": severity,
                "red_team_reasoning": reasoning,
                "decision": final_decision,
            }

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            last_exc = exc
            if attempt == 0:
                logger.warning(f"[{eval_id}] Red Team malformed output (attempt 1/2): {exc}. Retrying...")

        except Exception as exc:
            logger.error(f"[{eval_id}] Red Team unexpected error (attempt {attempt+1}/2): {exc}")
            last_exc = exc
            break

    # Red Team failure: log and degrade gracefully — do NOT crash the pipeline (NF-05)
    logger.error(
        f"[{eval_id}] Red Team FAILED after retry: {last_exc}. "
        "Passing through with flag=False (no override). Decision preserved."
    )
    return {
        "red_team_flag": False,
        "red_team_severity": None,
        "red_team_reasoning": f"Red Team check failed: {last_exc}",
        "decision": current_decision,
    }
