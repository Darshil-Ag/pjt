"""
Node: Parallel Dispatch
Responsibility: Invoke all 5 domain agents in parallel → collect scores, claims, citations (SRS F-05)
Also computes Ci (confidence, SRS F-06) and Wi (calibrated weight, SRS F-07) deterministically.

LLM calls:
  - Gemini 3.6 Flash (1 call) → domain-relevance priors Ri, BEFORE agent calls (F-07)
  - Groq Llama 3.3 70B (5 concurrent calls) → per-agent {score, claim, cited_case_ids} (F-05)

F-07 HARD RULE:
  Wi = softmax((Ri + bi) / T)
  Ri = domain-relevance prior from Gemini — computed INDEPENDENTLY of agent scores.
  Using Si (agent scores) as weight input is EXPLICITLY PROHIBITED: it conflates
  "how much to trust this agent on this pitch" with "what this agent said" — the
  exact naive-baseline flaw AIRB exists to beat (BRD §2, problem statement).
  Sprint 2: bi=0, T=1 (uncalibrated). Grid-search calibration is Sprint 3.

F-06 HARD RULE:
  Ci computation (confidence) uses ZERO LLM calls — metadata lookup only.
  This is the auditability boundary. Never put an LLM call in _compute_confidence().
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import numpy as np

from config import Config
from schemas.state import ReviewBoardState

logger = logging.getLogger(__name__)

DOMAINS = ["Finance", "Legal", "Market", "Operations", "Technology"]

# ── Prompts ───────────────────────────────────────────────────────────────────

_RI_PROMPT = """\
You are rating the importance of five investment review domains for evaluating a specific startup pitch.
Assign a relevance score 0-100 to each domain. Higher = this domain is MORE critical for THIS specific pitch.
Be discriminating: a pure B2C app should score Legal lower than a biotech; a hardware startup scores Operations higher.
Do NOT assign the same score to all domains — they must vary based on the pitch content.

PITCH:
{pitch}

Respond with ONLY valid JSON, no commentary, no markdown:
{{"Finance": <0-100>, "Legal": <0-100>, "Market": <0-100>, "Operations": <0-100>, "Technology": <0-100>}}"""

_AGENT_PROMPT = """\
You are the {domain} specialist on an AI investment review board evaluating a startup pitch.
Assess ONLY from a {domain} perspective. Do not comment on other domains.

STARTUP PITCH:
{pitch}

STRUCTURED STARTUP PROFILE:
{digital_twin_json}

SIMILAR HISTORICAL CASES FOR REFERENCE:
{cases_json}

Score this startup 0-100 on {domain} viability (0=fatal flaw, 50=neutral, 100=exceptional).
Cite any historical case IDs above that most influenced your assessment.

Respond with ONLY valid JSON, no commentary, no markdown:
{{"score": <integer 0-100>, "claim": "<one concise sentence summarizing your {domain} assessment>", "cited_case_ids": [<case_id strings from the historical cases above, may be empty list>]}}"""


# ── Ri: Domain Relevance Prior (F-07) ─────────────────────────────────────────

async def _get_domain_relevance(startup_pitch: str, eval_id: str) -> dict[str, float]:
    """
    Single Gemini call: rate relevance of each domain to THIS specific pitch (0-100).

    Returns {domain: Ri} — these are the weight inputs for Wi = softmax((Ri + bi) / T).
    Ri is computed BEFORE the 5 agent calls and is INDEPENDENT of agent scores (Si).

    F-07 hard rule: this function must never read state["agent_scores"]. If you find
    yourself passing Si into this function, you are violating the auditability boundary.
    """
    from google import genai
    client = genai.Client(api_key=Config.llm.google_api_key)
    prompt = _RI_PROMPT.format(pitch=startup_pitch)

    try:
        response = await client.aio.models.generate_content(
            model=Config.llm.router_model,
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown code fences if model wraps output
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:].strip()
        ri = json.loads(text)
        # Validate: all domains present, values in [0, 100]
        result = {}
        for d in DOMAINS:
            val = float(ri.get(d, 50.0))
            result[d] = max(0.0, min(100.0, val))
        logger.info(f"[{eval_id}] Domain relevance Ri (F-07): {result}")
        return result
    except Exception as exc:
        logger.warning(
            f"[{eval_id}] Gemini Ri call failed ({exc}), falling back to uniform Ri=50. "
            "Weights will be equal — log this as a calibration gap."
        )
        return {d: 50.0 for d in DOMAINS}


# ── Single Agent Call (F-05) ──────────────────────────────────────────────────

async def _single_agent_call(
    domain: str,
    startup_pitch: str,
    digital_twin: dict,
    retrieved_cases: list[dict],
    eval_id: str,
) -> Optional[dict]:
    """
    Single domain agent coroutine.

    Returns {score, claim, cited_case_ids} on success.
    Returns None after one retry on malformed JSON (F-05 acceptance criterion).
    Failure is logged and the agent is excluded from fusion — does NOT crash the run (NF-05).
    """
    from progress import update_agent_status
    from groq import AsyncGroq

    update_agent_status(eval_id, domain, "running")

    client = AsyncGroq(api_key=Config.llm.groq_api_key)
    prompt = _AGENT_PROMPT.format(
        domain=domain,
        pitch=startup_pitch,
        digital_twin_json=json.dumps(digital_twin, indent=2, default=str),
        cases_json=json.dumps(retrieved_cases, indent=2, default=str) if retrieved_cases else "[]",
    )

    last_exc: Optional[Exception] = None
    for attempt in range(2):  # Attempt 0 + one retry (F-05)
        try:
            resp = await client.chat.completions.create(
                model=Config.llm.worker_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown code fences if model wraps output
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            parsed = json.loads(raw)

            # Validate required fields
            score = float(parsed["score"])
            if not (0 <= score <= 100):
                raise ValueError(f"score out of range: {score}")
            claim = str(parsed["claim"])
            cited = [str(c) for c in parsed.get("cited_case_ids", [])]

            update_agent_status(eval_id, domain, "complete", score=score)
            logger.info(f"[{eval_id}] {domain} agent: score={score:.0f}, cited={cited}")
            return {"score": score, "claim": claim, "cited_case_ids": cited}

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            last_exc = exc
            if attempt == 0:
                logger.warning(
                    f"[{eval_id}] {domain} agent returned malformed output (attempt 1/2): {exc}. Retrying..."
                )
            # Fall through to retry

        except Exception as exc:
            logger.error(f"[{eval_id}] {domain} agent unexpected error (attempt {attempt+1}/2): {exc}")
            last_exc = exc
            break  # Non-JSON errors (network, auth) don't benefit from retry

    logger.error(f"[{eval_id}] {domain} agent FAILED after retry: {last_exc}. Excluding from fusion (NF-05).")
    update_agent_status(eval_id, domain, "error")
    return None


# ── Ci: Confidence Score (F-06) ───────────────────────────────────────────────

def _compute_confidence(
    domain: str,
    result: dict,
    retrieved_cases: list[dict],
) -> float:
    """
    Deterministic confidence score — ZERO LLM calls (SRS F-06 hard rule).
    This is the auditability boundary for the confidence component.

    Ci = w_sim * M_sim + w_evidence * M_evidence + w_reliability * M_reliability

    M_sim:         Mean cosine similarity of retrieved cases from RAG metadata.
                   Higher similarity → more relevant evidence → higher confidence.
    M_evidence:    Fraction of cited_case_ids whose primary_risk_category matches domain.
                   Penalizes agents that cite irrelevant cross-domain cases.
    M_reliability: Fixed at 1.0 for curated labeled dataset (SRS F-06 spec).

    All weights from Config.confidence (config.yaml — NF-04: never hardcode thresholds).
    """
    w_sim = Config.confidence.w_sim               # default 0.5
    w_evidence = Config.confidence.w_evidence     # default 0.4
    w_reliability = Config.confidence.w_reliability  # default 0.1

    # M_sim: mean cosine similarity from retrieval
    if retrieved_cases:
        sim_scores = [float(c.get("similarity_score", 0.5)) for c in retrieved_cases]
        m_sim = float(np.mean(sim_scores))
    else:
        m_sim = 0.0  # No retrieval context → minimal confidence contribution

    # M_evidence: fraction of cited cases matching this domain's risk category
    cited_ids = set(result.get("cited_case_ids", []))
    if cited_ids:
        # RiskCategory enum values match DOMAINS strings exactly (Finance, Legal, etc.)
        domain_matches = sum(
            1 for c in retrieved_cases
            if c.get("case_id") in cited_ids
            and c.get("primary_risk_category", "").lower() == domain.lower()
        )
        m_evidence = domain_matches / len(cited_ids)
    else:
        m_evidence = 0.0  # No citations → no evidence support

    m_reliability = 1.0  # Curated dataset (SRS F-06)

    ci = w_sim * m_sim + w_evidence * m_evidence + w_reliability * m_reliability
    return round(float(np.clip(ci, 0.0, 1.0)), 4)


# ── Wi: Calibrated Weight (F-07) ──────────────────────────────────────────────

def _compute_weights(
    domain_relevance: dict[str, float],
    bias: float = 0.0,
    temperature: float = 1.0,
) -> dict[str, float]:
    """
    Calibrated weights per SRS F-07:
        Wi = softmax((Ri + bi) / T)

    Args:
        domain_relevance: {domain: Ri} from _get_domain_relevance() via Gemini.
                          NEVER pass agent scores (Si) here — see F-07 hard rule above.
        bias:             Per-domain bias bi. Sprint 2: 0.0 (uncalibrated).
                          Real bi is fitted by grid search on calibration set in Sprint 3.
        temperature:      Softmax temperature T. Sprint 2: 1.0 (uncalibrated).
                          Real T is fitted by grid search in Sprint 3.

    Returns:
        {domain: Wi} summing to 1.0 (softmax output).
    """
    # Sprint 2: bi=0, T=1 for all domains (uncalibrated — calibration is Sprint 3)
    logger.info(
        "[UNCALIBRATED] Sprint 2 weights use bi=0, T=1.0. "
        "Calibration grid-search deferred to Sprint 3. "
        "Weights reflect domain relevance Ri only."
    )
    domains = list(domain_relevance.keys())
    ri_arr = np.array([domain_relevance[d] for d in domains], dtype=float)
    logits = (ri_arr + bias) / temperature
    # Numerically stable softmax: subtract max before exp
    logits -= logits.max()
    exp_logits = np.exp(logits)
    softmax = exp_logits / exp_logits.sum()
    return {d: round(float(softmax[i]), 6) for i, d in enumerate(domains)}


# ── Node Entry Point (F-05, F-06, F-07) ──────────────────────────────────────

async def parallel_dispatch_node(state: ReviewBoardState) -> dict:
    """
    Parallel Dispatch Node.

    Reads:  state["startup_pitch"], state["digital_twin"], state["retrieved_cases"]
    Writes: state["agent_scores"], state["agent_confidences"],
            state["agent_weights"], state["agent_claims"], state["agent_citations"]

    Execution order (order matters for F-07 correctness):
      1. Gemini call → Ri dict   [MUST run before agents — Ri independent of Si]
      2. asyncio.gather → 5 concurrent Groq agent calls
      3. Deterministic Ci per successful agent (no LLM — F-06)
      4. Deterministic Wi = softmax(Ri/T) over active agents (no LLM — F-07)

    Failed agents (after retry) are excluded from fusion per NF-05 graceful degradation.
    If ALL agents fail, returns empty dicts — fusion_node handles this case.
    """
    from progress import update_stage, update_agent_status

    eval_id = state.get("evaluation_id", "")
    update_stage(eval_id, "parallel_dispatch")

    startup_pitch = state["startup_pitch"]
    digital_twin = state.get("digital_twin", {})
    retrieved_cases = state.get("retrieved_cases", [])

    # ── Step 1: Compute domain-relevance priors Ri (F-07) ────────────────────
    # This MUST run before agent calls — Ri must be independent of Si.
    domain_relevance = await _get_domain_relevance(startup_pitch, eval_id)

    # ── Step 2: Run all 5 agents concurrently (F-05) ─────────────────────────
    # Mark all running before gather so progress store shows immediate activity
    for domain in DOMAINS:
        update_agent_status(eval_id, domain, "running")

    agent_tasks = [
        _single_agent_call(domain, startup_pitch, digital_twin, retrieved_cases, eval_id)
        for domain in DOMAINS
    ]
    raw_results: list[Optional[dict]] = await asyncio.gather(*agent_tasks)

    # ── Step 3: Collect successful results + compute Ci (F-06) ───────────────
    agent_scores: dict[str, float] = {}
    agent_claims: dict[str, str] = {}
    agent_citations: dict[str, list] = {}
    agent_confidences: dict[str, float] = {}
    active_relevance: dict[str, float] = {}

    for domain, result in zip(DOMAINS, raw_results):
        if result is None:
            logger.warning(f"[{eval_id}] Agent '{domain}' excluded from fusion (failed after retry).")
            continue
        agent_scores[domain] = result["score"]
        agent_claims[domain] = result["claim"]
        agent_citations[domain] = result["cited_case_ids"]
        agent_confidences[domain] = _compute_confidence(domain, result, retrieved_cases)
        active_relevance[domain] = domain_relevance[domain]  # Only for agents that succeeded

    if not agent_scores:
        logger.error(
            f"[{eval_id}] All 5 domain agents failed. "
            "Fusion will degrade to REVIEW (NF-05 graceful degradation)."
        )

    # ── Step 4: Compute calibrated weights Wi (F-07) ─────────────────────────
    # Input: Ri from Gemini (independent of Si). NEVER pass agent_scores here.
    agent_weights = _compute_weights(active_relevance) if active_relevance else {}

    logger.info(
        f"[{eval_id}] Parallel dispatch complete. "
        f"Scores={agent_scores}, Weights={agent_weights}, Confidences={agent_confidences}"
    )

    return {
        "agent_scores": agent_scores,
        "agent_confidences": agent_confidences,
        "agent_weights": agent_weights,
        "agent_claims": agent_claims,
        "agent_citations": agent_citations,
    }
