"""
Tests for live progress store and asynchronous /evaluate route.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from progress import (
    create_progress,
    update_stage,
    update_agent_status,
    mark_hitl_pending,
    mark_complete,
    mark_error,
    get_progress,
)


class TestProgressStore:
    """Test unit behavior of the in-memory progress store."""

    def test_create_and_get_progress(self):
        eval_id = "test-eval-001"
        create_progress(eval_id)

        prog = get_progress(eval_id)
        assert prog is not None
        assert prog["evaluation_id"] == eval_id
        assert prog["status"] == "queued"
        assert prog["current_stage"] is None
        assert len(prog["agent_status"]) == 5
        for agent in ["Finance", "Legal", "Market", "Operations", "Technology"]:
            assert prog["agent_status"][agent]["status"] == "pending"
            assert prog["agent_status"][agent]["score"] is None

    def test_update_stage_and_agent_status(self):
        eval_id = "test-eval-002"
        create_progress(eval_id)

        update_stage(eval_id, "parallel_dispatch")
        prog = get_progress(eval_id)
        assert prog["status"] == "running"
        assert prog["current_stage"] == "parallel_dispatch"

        update_agent_status(eval_id, "Finance", "complete", 85.5)
        prog = get_progress(eval_id)
        assert prog["agent_status"]["Finance"]["status"] == "complete"
        assert prog["agent_status"]["Finance"]["score"] == 85.5

    def test_mark_hitl_pending_and_complete(self):
        eval_id = "test-eval-003"
        create_progress(eval_id)

        mark_hitl_pending(eval_id)
        prog = get_progress(eval_id)
        assert prog["status"] == "hitl_pending"

        mark_complete(eval_id)
        prog = get_progress(eval_id)
        assert prog["status"] == "complete"

    def test_mark_error(self):
        eval_id = "test-eval-004"
        create_progress(eval_id)

        mark_error(eval_id, "API key failed")
        prog = get_progress(eval_id)
        assert prog["status"] == "error"
        assert prog["error_message"] == "API key failed"


class TestProgressAPI:
    """Test FastAPI endpoints for evaluate and status."""

    def test_evaluate_returns_immediately_and_status_polls(self):
        client = TestClient(app)
        payload = {"startup_pitch": "We are building an AI-powered agricultural sensor system."}

        response = client.post("/api/v1/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "evaluation_id" in data
        assert data["status"] == "queued"

        eval_id = data["evaluation_id"]

        status_resp = client.get(f"/api/v1/status/{eval_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["evaluation_id"] == eval_id
        assert status_data["status"] in ["queued", "running", "complete", "error"]
        assert "agent_status" in status_data

    def test_get_decision_returns_digital_twin(self):
        client = TestClient(app)
        eval_id = "test-decision-dt-001"
        create_progress(eval_id)
        
        mock_result = {
            "decision": "PROCEED",
            "final_score": 75.0,
            "final_confidence": 0.8,
            "final_score_uncertainty": 5.0,
            "digital_twin": {"industry": "FinTech", "revenue_model": "SaaS"},
            "retrieved_cases": [{"case_id": "case_004", "industry": "AgriTech"}],
            "retrieved_case_ids": ["case_004"],
            "agent_scores": {"Finance": 80.0},
            "agent_claims": {"Finance": "Strong"},
            "agent_weights": {"Finance": 1.0},
            "agent_confidences": {"Finance": 0.8},
            "agent_citations": {"Finance": []},
            "conflict_detected": False,
            "variance_history": [10.0],
            "red_team_flag": False,
            "red_team_severity": None,
            "red_team_reasoning": "None",
            "hitl_triggered": False,
            "hitl_question": None,
            "hitl_answer": None,
            "version_info": {},
        }
        from progress import store_result
        store_result(eval_id, mock_result)
        mark_complete(eval_id)

        resp = client.get(f"/api/v1/decision/{eval_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "digital_twin" in data
        assert data["digital_twin"] == {"industry": "FinTech", "revenue_model": "SaaS"}
        assert "retrieved_cases" in data
        assert "retrieved_case_ids" in data
        assert data["retrieved_case_ids"] == ["case_004"]


