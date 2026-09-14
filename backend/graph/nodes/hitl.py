"""
Node: HITL Pause & Prompt Generator
Responsibility: Evaluate variance → pause execution & construct structured human question if CI > theta (SRS F-08)
LLM: Gemini 3.6 Flash — question generation only.

Sprint 1: STUB — node signature defined; question generation implemented Sprint 2.
          Checkpoint persistence mechanism (SQLite via LangGraph) is wired in graph.py.
"""

from __future__ import annotations

from schemas.state import ReviewBoardState


# Requirement: F-09
# Acceptance criteria: Graph state survives a server restart between pause and resume
#                      (tested via checkpointer persistence, not in-memory state).
async def hitl_node(state: ReviewBoardState) -> dict:
    """
    HITL Node.
    Reads: state["digital_twin"], state["agent_scores"], state["agent_claims"]
    Writes: state["hitl_pending"], state["hitl_question"], state["hitl_triggered_variable"]

    Implementation (Sprint 2):
      1. Identify the two most-conflicting agents (by score spread).
      2. Identify the specific digital-twin field most likely driving the conflict.
      3. Generate ONE targeted clarifying question via Gemini (not a generic question).
      4. Set hitl_pending=True, hitl_question=<generated question>.
      5. Store hitl_triggered_variable for use by sensitivity_sweep_node (F-14).
      6. LangGraph checkpointer persists state to SQLite here.
      7. Graph execution pauses; FastAPI returns the question to the frontend.
      8. Resumption happens via POST /hitl-respond which calls graph.resume().

    HARD RULE: Graph state must be persisted to the checkpointer DB before returning,
               not held only in server memory (SRS F-09 acceptance criterion).
    """
    from progress import update_stage, mark_hitl_pending
    update_stage(state.get("evaluation_id", ""), "hitl")

    # TODO (Sprint 2): Implement question generation + checkpoint persistence. See SRS F-09.
    # Call mark_hitl_pending(state["evaluation_id"]) after setting hitl_pending=True.
    raise NotImplementedError(
        "HITL Node not yet implemented. "
        "See SRS F-09. Scheduled for Sprint 2."
    )


async def hitl_resume_node(state: ReviewBoardState) -> dict:
    """
    HITL Resume Node — called after user submits answer via POST /hitl-respond.
    Reads: state["hitl_answer"], state["hitl_triggered_variable"]
    Writes: state["digital_twin"] (merged with answer), state["hitl_pending"],
            state["round_count"], state["hitl_ci_before"]

    Implementation (Sprint 2):
      1. Merge hitl_answer into digital_twin at hitl_triggered_variable field.
      2. Set hitl_pending=False, increment round_count.
      3. Store current CI as hitl_ci_before for effectiveness logging (F-16).
      4. Graph execution continues to parallel_dispatch for re-evaluation.
    """
    # TODO (Sprint 2): Implement answer merge + round increment. See SRS F-09.
    raise NotImplementedError(
        "HITL Resume Node not yet implemented. "
        "See SRS F-09. Scheduled for Sprint 2."
    )
