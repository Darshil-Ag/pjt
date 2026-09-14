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
