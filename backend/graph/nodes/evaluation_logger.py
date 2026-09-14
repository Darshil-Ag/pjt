"""
Node: Evaluation Logger
Responsibility: Assign unique evaluation_id; persist full decision trace + version metadata (SRS F-17)

Sprint 1: STUB — UUID generation + version_info structure implemented;
          SQLite persistence implemented in Sprint 3 (requires DB schema in place).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from config import Config
from schemas.state import ReviewBoardState


# Requirement: F-17
# Acceptance criteria:
#   - Every evaluation produces a unique evaluation_id (no collisions across 100+ runs).
#   - GET /replay/{id} returns identical output without live LLM calls.
def evaluation_logger_node(state: ReviewBoardState) -> dict:
    """
    Evaluation Logger Node.
    Reads: entire state
    Writes: state["evaluation_id"], state["version_info"]
            (also persists DecisionTrace to SQLite — Sprint 3)

    Implementation (Sprint 3 for persistence):
      1. Build version_info dict from Config.versioning + active thresholds.
      2. Serialize full state as DecisionTrace Pydantic model.
      3. Persist to SQLite evaluation_traces table.
      4. Return evaluation_id and version_info.

    Replay (GET /replay/{id}):
      - Loads stored DecisionTrace from SQLite.
      - Returns it directly; ZERO live LLM calls are made.
    """
    from progress import update_stage
    update_stage(state.get("evaluation_id", ""), "evaluation_logger")

    version_info = {
        "model_worker": Config.llm.worker_model,
        "model_router": Config.llm.router_model,
        "model_red_team": Config.llm.red_team_model,
        "prompt_template_version": Config.versioning.prompt_template_version,
        "rag_index_version": Config.versioning.rag_index_version,
        "dataset_version": Config.versioning.dataset_version,
        "weight_calibration_version": Config.versioning.weight_calibration_version,
        "thresholds": {
            "theta_conflict": Config.thresholds.theta_conflict,
            "tau_approve": Config.thresholds.tau_approve,
            "tau_confidence": Config.thresholds.tau_confidence,
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    # evaluation_id may already be set (from graph initialization); ensure it's set
    evaluation_id = state.get("evaluation_id") or str(uuid.uuid4())

    # TODO (Sprint 3): Persist full DecisionTrace to SQLite. See SRS F-17.
    # For Sprint 1: version_info is computed but not persisted yet.

    return {
        "evaluation_id": evaluation_id,
        "version_info": version_info,
    }
