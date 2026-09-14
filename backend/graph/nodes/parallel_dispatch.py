"""
Node: Parallel Dispatch
Responsibility: Invoke all 5 domain agents in parallel → collect scores, claims, citations (SRS F-05)
Also computes Ci (confidence, SRS F-06) and Wi (calibrated weight, SRS F-07) deterministically.
LLM: Llama 3.3 70B via Groq (free tier) — one call per agent, all 5 concurrent.

Sprint 1: STUB — node and sub-agent signatures defined; logic in Sprint 2.
"""

from __future__ import annotations

from schemas.state import ReviewBoardState

DOMAINS = ["Finance", "Legal", "Market", "Operations", "Technology"]


# Requirement: F-05 (agent calls), F-06 (confidence), F-07 (weights)
# Acceptance criteria (F-05): 95%+ valid JSON across 20-pitch batch; malformed → one retry.
# Acceptance criteria (F-06): M_evidence computed via metadata lookup only — no LLM call.
# Acceptance criteria (F-07): Calibrated weights >= uncalibrated accuracy on calibration set.
async def parallel_dispatch_node(state: ReviewBoardState) -> dict:
    """
    Parallel Dispatch Node.
    Reads: state["digital_twin"], state["retrieved_cases"]
    Writes: state["agent_scores"], state["agent_confidences"],
            state["agent_weights"], state["agent_claims"], state["agent_citations"]

    Implementation (Sprint 2):
      1. Load calibrated weight vector from config.calibration.output_path.
      2. asyncio.gather() all 5 domain agent coroutines (one per DOMAINS entry).
      3. Each agent call: format prompt with digital_twin + retrieved_cases,
         call Groq API, parse AgentOutput JSON. One retry on malformed JSON (F-05).
      4. Deterministic Python (NO LLM) computes:
           Ci = w_sim * M_sim + w_evidence * M_evidence + w_reliability * M_reliability
             where M_evidence = fraction of cited_case_ids whose primary_risk_category
             matches the agent's domain (metadata lookup only — SRS F-06).
      5. Wi = softmax((Ri + bi) / T) using calibrated bi, T (SRS F-07).
      6. If one agent fails after retry, log warning and exclude from fusion (NF-05).

    HARD RULE: No LLM call inside Ci or Wi computation. This is the auditability boundary.
    """
    # TODO (Sprint 2): Implement agent calls + confidence/weight math. See SRS F-05/F-06/F-07.
    raise NotImplementedError(
        "Parallel Dispatch Node not yet implemented. "
        "See SRS F-05, F-06, F-07. Scheduled for Sprint 2."
    )


async def _single_agent_call(domain: str, digital_twin: dict, retrieved_cases: list[dict]) -> dict:
    """
    Single domain agent coroutine.
    Returns raw AgentOutput dict on success; raises on failure (caller handles retry).

    Args:
        domain: One of DOMAINS
        digital_twin: Structured pitch data
        retrieved_cases: Top-k historical cases with similarity scores

    Returns:
        {"score": float, "claim": str, "cited_case_ids": list[str]}
    """
    # TODO (Sprint 2): Implement via Groq API. See SRS F-05.
    raise NotImplementedError(f"Agent call for {domain} not yet implemented.")
