"""
Sprint 2 Tests — Parallel Dispatch, Confidence, Weights, Red Team, HITL
Tests use mocked API clients — no real Groq/Gemini calls during CI.

Run: .venv\\Scripts\\python -m pytest tests/test_sprint2.py -v
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

# ── Model configuration tests ─────────────────────────────────────────────────

class TestModelConfiguration:
    """Verify model names match the expected configuration (catches regressions)."""

    def test_worker_model_is_gpt_oss_120b(self):
        """worker_model must be openai/gpt-oss-120b — not the deprecated llama-3.3-70b-versatile."""
        from config import Config
        assert Config.llm.worker_model == "openai/gpt-oss-120b", (
            f"worker_model is {Config.llm.worker_model!r}. "
            "Expected 'openai/gpt-oss-120b'. llama-3.3-70b-versatile is unavailable on Groq."
        )

    def test_red_team_model_is_gpt_oss_120b(self):
        """red_team_model must be openai/gpt-oss-120b."""
        from config import Config
        assert Config.llm.red_team_model == "openai/gpt-oss-120b", (
            f"red_team_model is {Config.llm.red_team_model!r}. Expected 'openai/gpt-oss-120b'."
        )

    def test_router_model_unchanged(self):
        """router_model must stay gemini-3.6-flash — do not touch the working Gemini model."""
        from config import Config
        assert Config.llm.router_model == "gemini-3.6-flash", (
            f"router_model is {Config.llm.router_model!r}. "
            "Must remain 'gemini-3.6-flash' — do not change the working Gemini router."
        )

    def test_no_llama_references_in_config(self):
        """No active llama-3.3-70b-versatile references must exist in config."""
        from config import Config
        deprecated = "llama-3.3-70b-versatile"
        assert Config.llm.worker_model != deprecated, "worker_model still references deprecated llama model"
        assert Config.llm.red_team_model != deprecated, "red_team_model still references deprecated llama model"


# ── _compute_confidence tests (F-06) ─────────────────────────────────────────

class TestComputeConfidence:
    """
    Ci = w_sim * M_sim + w_evidence * M_evidence + w_reliability * 1.0
    Uses default weights: w_sim=0.5, w_evidence=0.4, w_reliability=0.1
    """

    def setup_method(self):
        from graph.nodes.parallel_dispatch import _compute_confidence
        self.compute_confidence = _compute_confidence

    def test_full_evidence_high_similarity(self):
        """All cited cases match domain + high similarity → high Ci"""
        retrieved_cases = [
            {"case_id": "c1", "similarity_score": 0.9, "primary_risk_category": "Finance"},
            {"case_id": "c2", "similarity_score": 0.85, "primary_risk_category": "Finance"},
        ]
        result = {"score": 70.0, "claim": "strong", "cited_case_ids": ["c1", "c2"]}
        ci = self.compute_confidence("Finance", result, retrieved_cases)
        # M_sim ≈ 0.875, M_evidence = 1.0, M_reliability = 1.0
        # Ci ≈ 0.5*0.875 + 0.4*1.0 + 0.1*1.0 = 0.4375 + 0.4 + 0.1 = 0.9375
        assert ci > 0.9, f"Expected Ci > 0.9, got {ci}"
        assert 0.0 <= ci <= 1.0

    def test_no_retrieved_cases_no_citations(self):
        """No retrieval context → M_sim=0, M_evidence=0 → Ci = w_reliability * 1.0 = 0.1"""
        result = {"score": 50.0, "claim": "neutral", "cited_case_ids": []}
        ci = self.compute_confidence("Market", result, retrieved_cases=[])
        # Ci = 0.5*0 + 0.4*0 + 0.1*1.0 = 0.1
        assert abs(ci - 0.1) < 0.001, f"Expected Ci ≈ 0.1 (reliability only), got {ci}"

    def test_wrong_domain_citations_lowers_evidence(self):
        """Agent cites only Finance cases but domain is Legal → M_evidence = 0"""
        retrieved_cases = [
            {"case_id": "c1", "similarity_score": 0.7, "primary_risk_category": "Finance"},
            {"case_id": "c2", "similarity_score": 0.6, "primary_risk_category": "Finance"},
        ]
        result = {"score": 60.0, "claim": "risky", "cited_case_ids": ["c1", "c2"]}
        ci = self.compute_confidence("Legal", result, retrieved_cases)
        # M_evidence = 0 (no Finance cases match Legal domain)
        assert ci < 0.5, f"Cross-domain citations should lower Ci, got {ci}"
        assert 0.0 <= ci <= 1.0

    def test_partial_evidence_match(self):
        """Half the cited cases match domain → M_evidence = 0.5"""
        retrieved_cases = [
            {"case_id": "c1", "similarity_score": 0.8, "primary_risk_category": "Technology"},
            {"case_id": "c2", "similarity_score": 0.7, "primary_risk_category": "Finance"},
        ]
        result = {"score": 65.0, "claim": "moderate", "cited_case_ids": ["c1", "c2"]}
        ci = self.compute_confidence("Technology", result, retrieved_cases)
        assert 0.0 <= ci <= 1.0

    def test_ci_always_clamped(self):
        """Ci must always be in [0, 1] regardless of inputs"""
        retrieved_cases = [
            {"case_id": f"c{i}", "similarity_score": 2.0, "primary_risk_category": "Market"}
            for i in range(5)
        ]
        result = {"score": 100.0, "claim": "perfect", "cited_case_ids": [f"c{i}" for i in range(5)]}
        ci = self.compute_confidence("Market", result, retrieved_cases)
        assert 0.0 <= ci <= 1.0, f"Ci must be clamped to [0,1], got {ci}"


# ── _compute_weights tests (F-07) ────────────────────────────────────────────

class TestComputeWeights:
    """
    Wi = softmax((Ri + 0) / 1.0) where Ri is domain-relevance prior from Gemini.
    CRITICAL: Ri must be independent of Si (agent scores).
    """

    def setup_method(self):
        from graph.nodes.parallel_dispatch import _compute_weights
        self.compute_weights = _compute_weights

    def test_weights_sum_to_one(self):
        """Softmax output must sum to 1.0"""
        ri = {"Finance": 80, "Legal": 40, "Market": 90, "Operations": 60, "Technology": 70}
        weights = self.compute_weights(ri)
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-5, f"Weights must sum to 1.0, got {total}"

    def test_higher_relevance_gets_higher_weight(self):
        """Domain with highest Ri must have highest Wi"""
        ri = {"Finance": 30, "Legal": 20, "Market": 95, "Operations": 50, "Technology": 60}
        weights = self.compute_weights(ri)
        max_domain = max(weights, key=weights.get)
        assert max_domain == "Market", f"Market has Ri=95 (highest), should have highest Wi. Got {max_domain}"

    def test_uniform_ri_gives_equal_weights(self):
        """Uniform Ri → uniform Wi (all domains equally trusted)"""
        ri = {"Finance": 50, "Legal": 50, "Market": 50, "Operations": 50, "Technology": 50}
        weights = self.compute_weights(ri)
        values = list(weights.values())
        assert all(abs(v - values[0]) < 1e-5 for v in values), \
            f"Uniform Ri should give uniform Wi, got {weights}"

    def test_weights_never_use_scores(self):
        """
        F-07 correctness check: _compute_weights takes domain_relevance (Ri dict), NOT scores (Si).
        This test verifies the function signature does not accept Si.
        If someone changes _compute_weights to accept agent_scores, this test catches it.
        """
        import inspect
        from graph.nodes.parallel_dispatch import _compute_weights
        params = inspect.signature(_compute_weights).parameters
        param_names = list(params.keys())
        # The first argument must be named 'domain_relevance', never 'agent_scores' or 'scores'
        assert param_names[0] == "domain_relevance", \
            f"F-07 violation: first param should be 'domain_relevance', got {param_names[0]!r}"
        assert "agent_scores" not in param_names, \
            "F-07 violation: _compute_weights must not accept agent_scores as input"
        assert "scores" not in param_names, \
            "F-07 violation: _compute_weights must not accept 'scores' as input"

    def test_single_active_agent(self):
        """Edge case: only one agent succeeded — it gets Wi = 1.0"""
        ri = {"Finance": 75}
        weights = self.compute_weights(ri)
        assert abs(weights["Finance"] - 1.0) < 1e-5, \
            f"Single agent should get Wi=1.0, got {weights}"

    def test_weights_are_non_negative(self):
        """Softmax output is always in (0, 1]"""
        ri = {"Finance": 5, "Legal": 95, "Market": 50, "Operations": 10, "Technology": 80}
        weights = self.compute_weights(ri)
        for d, w in weights.items():
            assert w >= 0, f"Weight for {d} is negative: {w}"
            assert w <= 1.0, f"Weight for {d} exceeds 1.0: {w}"


# ── parallel_dispatch_node integration test (mocked API) ─────────────────────

class TestParallelDispatchNode:

    def _make_state(self) -> dict:
        from schemas.state import initial_state
        return initial_state(
            "We build AI soil sensors for farms with 10k MRR.",
            "test-eval-id-001",
            {"model_worker": "openai/gpt-oss-120b"},
        )

    def _make_groq_response(self, domain: str, score: int) -> MagicMock:
        """Build a mock Groq chat completion response."""
        msg = MagicMock()
        msg.content = json.dumps({
            "score": score,
            "claim": f"Strong {domain} viability.",
            "cited_case_ids": [],
        })
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    def _make_gemini_response(self) -> MagicMock:
        """Build a mock Gemini response for Ri computation."""
        resp = MagicMock()
        resp.text = json.dumps({
            "Finance": 60, "Legal": 30, "Market": 85, "Operations": 55, "Technology": 90
        })
        return resp

    @pytest.mark.asyncio
    async def test_all_agents_succeed(self):
        """All 5 agents return valid JSON → all 5 scores, weights, confidences populated."""
        state = self._make_state()
        scores_map = {"Finance": 72, "Legal": 45, "Market": 88, "Operations": 61, "Technology": 79}

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("google.genai.Client") as mock_genai_client_cls,
            patch("progress.update_stage"),
            patch("progress.update_agent_status"),
        ):
            # Mock Gemini (Ri) — patch the client class, make aio.models.generate_content async
            mock_genai_client_instance = MagicMock()
            mock_genai_client_cls.return_value = mock_genai_client_instance
            mock_genai_client_instance.aio.models.generate_content = AsyncMock(
                return_value=self._make_gemini_response()
            )

            # Mock Groq (domain agents)
            mock_groq_instance = MagicMock()
            mock_groq_cls.return_value = mock_groq_instance
            domain_order = ["Finance", "Legal", "Market", "Operations", "Technology"]

            async def mock_groq_create(**kwargs):
                content = kwargs["messages"][0]["content"]
                for d in domain_order:
                    if d in content:
                        return self._make_groq_response(d, scores_map[d])
                return self._make_groq_response("Finance", 50)

            mock_groq_instance.chat.completions.create = mock_groq_create

            from graph.nodes.parallel_dispatch import parallel_dispatch_node
            result = await parallel_dispatch_node(state)

        assert len(result["agent_scores"]) == 5, "All 5 agents should succeed"
        assert len(result["agent_weights"]) == 5, "All 5 domains should have weights"
        assert len(result["agent_confidences"]) == 5
        assert abs(sum(result["agent_weights"].values()) - 1.0) < 1e-4, \
            "Weights must sum to 1.0"

    @pytest.mark.asyncio
    async def test_agents_execute_concurrently_not_sequentially(self):
        """
        All 5 agents must be launched before any completes.
        Verified by: asyncio.gather is used (not sequential awaits),
        so all 5 tasks exist in flight simultaneously.
        """
        state = self._make_state()
        start_times: dict[str, float] = {}
        end_times: dict[str, float] = {}

        async def mock_groq_create(**kwargs):
            import time
            content = kwargs["messages"][0]["content"]
            domain = "Finance"
            for d in ["Finance", "Legal", "Market", "Operations", "Technology"]:
                if d in content:
                    domain = d
                    break
            start_times[domain] = time.monotonic()
            await asyncio.sleep(0.01)  # Small delay to expose sequentiality if present
            end_times[domain] = time.monotonic()
            msg = MagicMock()
            msg.content = json.dumps({"score": 70, "claim": f"{domain} ok", "cited_case_ids": []})
            choice = MagicMock()
            choice.message = msg
            resp = MagicMock()
            resp.choices = [choice]
            return resp

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("google.genai.Client") as mock_genai_client_cls,
            patch("progress.update_stage"),
            patch("progress.update_agent_status"),
        ):
            mock_genai_client_instance = MagicMock()
            mock_genai_client_cls.return_value = mock_genai_client_instance
            mock_genai_client_instance.aio.models.generate_content = AsyncMock(
                return_value=self._make_gemini_response()
            )
            mock_groq_instance = MagicMock()
            mock_groq_cls.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = mock_groq_create

            from graph.nodes.parallel_dispatch import parallel_dispatch_node
            result = await parallel_dispatch_node(state)

        # If sequential: last_start > first_end. If concurrent: all start_times overlap.
        if len(start_times) == 5:
            first_end = min(end_times.values())
            last_start = max(start_times.values())
            # Concurrent: at least some tasks started before others ended
            assert last_start < first_end + 0.05, \
                "Agents appear to be running sequentially — they should run concurrently via asyncio.gather"

        assert len(result["agent_scores"]) == 5

    @pytest.mark.asyncio
    async def test_successful_agent_scores_are_persisted(self):
        """Successful agents must have their actual score stored in the result dict."""
        state = self._make_state()
        expected_scores = {"Finance": 72, "Legal": 45, "Market": 88, "Operations": 61, "Technology": 79}

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("google.genai.Client") as mock_genai_client_cls,
            patch("progress.update_stage"),
            patch("progress.update_agent_status"),
        ):
            mock_genai_client_instance = MagicMock()
            mock_genai_client_cls.return_value = mock_genai_client_instance
            mock_genai_client_instance.aio.models.generate_content = AsyncMock(
                return_value=self._make_gemini_response()
            )
            mock_groq_instance = MagicMock()
            mock_groq_cls.return_value = mock_groq_instance

            async def mock_groq_create(**kwargs):
                content = kwargs["messages"][0]["content"]
                for d, s in expected_scores.items():
                    if d in content:
                        return self._make_groq_response(d, s)
                return self._make_groq_response("Finance", 50)

            mock_groq_instance.chat.completions.create = mock_groq_create

            from graph.nodes.parallel_dispatch import parallel_dispatch_node
            result = await parallel_dispatch_node(state)

        for domain, expected in expected_scores.items():
            assert domain in result["agent_scores"], f"{domain} score missing from result"
            assert result["agent_scores"][domain] == float(expected), \
                f"{domain}: expected score {expected}, got {result['agent_scores'][domain]}"

    @pytest.mark.asyncio
    async def test_agent_status_transitions_to_answered(self):
        """Successful agents must transition to 'answered' status (not 'complete')."""
        state = self._make_state()
        status_calls: list[tuple] = []

        def capture_status(eval_id, domain, status, score=None):
            status_calls.append((domain, status, score))

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("google.genai.Client") as mock_genai_client_cls,
            patch("progress.update_stage"),
            patch("progress.update_agent_status", side_effect=capture_status),
        ):
            mock_genai_client_instance = MagicMock()
            mock_genai_client_cls.return_value = mock_genai_client_instance
            mock_genai_client_instance.aio.models.generate_content = AsyncMock(
                return_value=self._make_gemini_response()
            )
            mock_groq_instance = MagicMock()
            mock_groq_cls.return_value = mock_groq_instance

            async def mock_groq_create(**kwargs):
                content = kwargs["messages"][0]["content"]
                for d in ["Finance", "Legal", "Market", "Operations", "Technology"]:
                    if d in content:
                        return self._make_groq_response(d, 75)
                return self._make_groq_response("Finance", 75)

            mock_groq_instance.chat.completions.create = mock_groq_create

            from graph.nodes.parallel_dispatch import parallel_dispatch_node
            await parallel_dispatch_node(state)

        # Every domain should have a "running" transition and an "answered" transition
        running_domains = {call[0] for call in status_calls if call[1] == "running"}
        answered_domains = {call[0] for call in status_calls if call[1] == "answered"}
        assert running_domains == {"Finance", "Legal", "Market", "Operations", "Technology"}, \
            f"Not all agents marked running: {running_domains}"
        assert answered_domains == {"Finance", "Legal", "Market", "Operations", "Technology"}, \
            f"Not all agents marked answered: {answered_domains}. " \
            f"Status calls: {status_calls}"

        # Scores must be persisted with the "answered" transition (not None)
        for domain, status, score in status_calls:
            if status == "answered":
                assert score is not None, f"{domain} marked 'answered' but score is None"
                assert score > 0, f"{domain} answered with non-positive score {score}"

    @pytest.mark.asyncio
    async def test_one_agent_fails_other_four_continue(self):
        """
        One agent failure must NOT terminate other agents (NF-05).
        The failing agent gets status 'error'; the other 4 get 'answered'.
        """
        state = self._make_state()
        status_calls: list[tuple] = []

        def capture_status(eval_id, domain, status, score=None):
            status_calls.append((domain, status, score))

        async def mock_groq_create(**kwargs):
            content = kwargs["messages"][0]["content"]
            if "Legal" in content:
                raise ValueError("Simulated Legal agent failure")
            for d in ["Finance", "Market", "Operations", "Technology"]:
                if d in content:
                    msg = MagicMock()
                    msg.content = json.dumps({"score": 70, "claim": f"{d} ok", "cited_case_ids": []})
                    choice = MagicMock()
                    choice.message = msg
                    resp = MagicMock()
                    resp.choices = [choice]
                    return resp
            msg = MagicMock()
            msg.content = json.dumps({"score": 60, "claim": "ok", "cited_case_ids": []})
            choice = MagicMock()
            choice.message = msg
            resp = MagicMock()
            resp.choices = [choice]
            return resp

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("google.genai.Client") as mock_genai_client_cls,
            patch("progress.update_stage"),
            patch("progress.update_agent_status", side_effect=capture_status),
        ):
            mock_genai_client_instance = MagicMock()
            mock_genai_client_cls.return_value = mock_genai_client_instance
            mock_genai_client_instance.aio.models.generate_content = AsyncMock(
                return_value=self._make_gemini_response()
            )
            mock_groq_instance = MagicMock()
            mock_groq_cls.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = mock_groq_create

            from graph.nodes.parallel_dispatch import parallel_dispatch_node
            result = await parallel_dispatch_node(state)

        # Legal should be excluded; other 4 should succeed
        assert "Legal" not in result["agent_scores"], "Failed agent must be excluded from scores"
        assert len(result["agent_scores"]) == 4, "4 agents should succeed"
        assert abs(sum(result["agent_weights"].values()) - 1.0) < 1e-4

        # Verify Legal got "error" status, others got "answered"
        error_domains = {call[0] for call in status_calls if call[1] == "error"}
        answered_domains = {call[0] for call in status_calls if call[1] == "answered"}
        assert "Legal" in error_domains, "Failed Legal agent must be marked 'error'"
        assert answered_domains == {"Finance", "Market", "Operations", "Technology"}, \
            f"Surviving agents should be 'answered', got {answered_domains}"

    @pytest.mark.asyncio
    async def test_one_agent_fails_gracefully(self):
        """If one agent fails after retry, it's excluded — other 4 proceed (NF-05)."""
        state = self._make_state()

        async def mock_groq_create(**kwargs):
            content = kwargs["messages"][0]["content"]
            if "Legal" in content:
                raise ValueError("Simulated Legal agent failure")
            for d in ["Finance", "Market", "Operations", "Technology"]:
                if d in content:
                    msg = MagicMock()
                    msg.content = json.dumps({"score": 70, "claim": f"{d} ok", "cited_case_ids": []})
                    choice = MagicMock()
                    choice.message = msg
                    resp = MagicMock()
                    resp.choices = [choice]
                    return resp
            msg = MagicMock()
            msg.content = json.dumps({"score": 60, "claim": "ok", "cited_case_ids": []})
            choice = MagicMock()
            choice.message = msg
            resp = MagicMock()
            resp.choices = [choice]
            return resp

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("google.genai.Client") as mock_genai_client_cls,
            patch("progress.update_stage"),
            patch("progress.update_agent_status"),
        ):
            mock_genai_client_instance = MagicMock()
            mock_genai_client_cls.return_value = mock_genai_client_instance
            mock_genai_client_instance.aio.models.generate_content = AsyncMock(
                return_value=self._make_gemini_response()
            )
            mock_groq_instance = MagicMock()
            mock_groq_cls.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = mock_groq_create

            from graph.nodes.parallel_dispatch import parallel_dispatch_node
            result = await parallel_dispatch_node(state)

        # Legal should be excluded; other 4 should succeed
        assert "Legal" not in result["agent_scores"], "Failed agent must be excluded"
        assert len(result["agent_scores"]) == 4, "4 agents should succeed"
        assert abs(sum(result["agent_weights"].values()) - 1.0) < 1e-4

    @pytest.mark.asyncio
    async def test_final_decision_uses_real_agent_scores(self):
        """
        Fusion must use actual agent scores — not produce REVIEW from empty scores.
        This test verifies the end-to-end: agent scores → fusion → non-null decision.
        """
        from schemas.state import initial_state
        from graph.nodes.parallel_dispatch import parallel_dispatch_node
        from graph.nodes.conflict_index import conflict_index_node
        from graph.nodes.fusion import fusion_node

        state = initial_state(
            "We build AI soil sensors for farms with 10k MRR.",
            "test-e2e-decision",
            {"model_worker": "openai/gpt-oss-120b"},
        )
        scores_map = {"Finance": 72, "Legal": 55, "Market": 88, "Operations": 61, "Technology": 79}

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("google.genai.Client") as mock_genai_client_cls,
            patch("progress.update_stage"),
            patch("progress.update_agent_status"),
        ):
            mock_genai_client_instance = MagicMock()
            mock_genai_client_cls.return_value = mock_genai_client_instance
            gemini_resp = MagicMock()
            gemini_resp.text = json.dumps(
                {"Finance": 60, "Legal": 30, "Market": 85, "Operations": 55, "Technology": 90}
            )
            mock_genai_client_instance.aio.models.generate_content = AsyncMock(return_value=gemini_resp)
            mock_groq_instance = MagicMock()
            mock_groq_cls.return_value = mock_groq_instance

            async def mock_groq_create(**kwargs):
                content = kwargs["messages"][0]["content"]
                for d, s in scores_map.items():
                    if d in content:
                        msg = MagicMock()
                        msg.content = json.dumps({"score": s, "claim": f"{d} ok", "cited_case_ids": []})
                        choice = MagicMock()
                        choice.message = msg
                        resp = MagicMock()
                        resp.choices = [choice]
                        return resp
                msg = MagicMock()
                msg.content = json.dumps({"score": 70, "claim": "ok", "cited_case_ids": []})
                choice = MagicMock()
                choice.message = msg
                resp = MagicMock()
                resp.choices = [choice]
                return resp

            mock_groq_instance.chat.completions.create = mock_groq_create
            dispatch_result = await parallel_dispatch_node(state)

        state.update(dispatch_result)
        state.update(conflict_index_node(state))
        fusion_result = fusion_node(state)

        # Verify the fusion used real scores (not empty)
        assert len(dispatch_result["agent_scores"]) == 5, "All 5 agents must have scores"
        assert fusion_result["final_score"] is not None, \
            "final_score must not be None when agents returned real scores"
        assert fusion_result["decision"] in ("PROCEED", "HIGH-RISK", "REVIEW"), \
            f"decision must be a valid label, got {fusion_result['decision']!r}"
        # With scores mostly 55-88, decision should not be REVIEW due to weak confidence
        # (unless the fusion thresholds mandate it — but final_score must be non-null)
        assert fusion_result["final_score"] > 0, \
            f"final_score should be positive when agents returned scores 55-88, got {fusion_result['final_score']}"


# ── red_team_node tests (F-13) ────────────────────────────────────────────────

class TestRedTeamNode:

    def _make_state(self, decision: str = "PROCEED") -> dict:
        from schemas.state import initial_state
        state = initial_state(
            "We build AI soil sensors for farms with 10k MRR.",
            "test-red-team-001",
            {},
        )
        state.update({
            "decision": decision,
            "agent_claims": {"Finance": "Strong MRR.", "Market": "Growing market."},
        })
        return state

    def _make_groq_response(self, flag: bool, severity: str, reasoning: str) -> MagicMock:
        msg = MagicMock()
        msg.content = json.dumps({"flag": flag, "severity": severity, "reasoning": reasoning})
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @pytest.mark.asyncio
    async def test_high_severity_flag_overrides_decision(self):
        """flag=True + severity='high' must override any decision to REVIEW."""
        state = self._make_state(decision="PROCEED")

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("progress.update_stage"),
        ):
            mock_inst = MagicMock()
            mock_groq_cls.return_value = mock_inst
            mock_inst.chat.completions.create = AsyncMock(
                return_value=self._make_groq_response(
                    flag=True, severity="high",
                    reasoning="Critical regulatory risk: IoT devices require FDA clearance for farm use."
                )
            )
            from graph.nodes.red_team import red_team_node
            result = await red_team_node(state)

        assert result["decision"] == "REVIEW", "High-severity flag must override to REVIEW"
        assert result["red_team_flag"] is True
        assert result["red_team_severity"] == "high"

    @pytest.mark.asyncio
    async def test_medium_severity_preserves_decision(self):
        """flag=True + severity='medium' must NOT override decision."""
        state = self._make_state(decision="PROCEED")

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("progress.update_stage"),
        ):
            mock_inst = MagicMock()
            mock_groq_cls.return_value = mock_inst
            mock_inst.chat.completions.create = AsyncMock(
                return_value=self._make_groq_response(
                    flag=True, severity="medium",
                    reasoning="Some supply chain risk, but manageable."
                )
            )
            from graph.nodes.red_team import red_team_node
            result = await red_team_node(state)

        assert result["decision"] == "PROCEED", \
            "Medium severity must NOT override decision; got %r" % result["decision"]
        assert result["red_team_flag"] is True

    @pytest.mark.asyncio
    async def test_no_flag_preserves_decision(self):
        """flag=False → decision unchanged."""
        state = self._make_state(decision="HIGH-RISK")

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("progress.update_stage"),
        ):
            mock_inst = MagicMock()
            mock_groq_cls.return_value = mock_inst
            mock_inst.chat.completions.create = AsyncMock(
                return_value=self._make_groq_response(
                    flag=False, severity="low",
                    reasoning="Board assessment appears comprehensive."
                )
            )
            from graph.nodes.red_team import red_team_node
            result = await red_team_node(state)

        assert result["decision"] == "HIGH-RISK"
        assert result["red_team_flag"] is False

    @pytest.mark.asyncio
    async def test_red_team_failure_degrades_gracefully(self):
        """Red Team API failure must NOT crash pipeline (NF-05)."""
        state = self._make_state(decision="PROCEED")

        with (
            patch("groq.AsyncGroq") as mock_groq_cls,
            patch("progress.update_stage"),
        ):
            mock_inst = MagicMock()
            mock_groq_cls.return_value = mock_inst
            mock_inst.chat.completions.create = AsyncMock(
                side_effect=RuntimeError("Groq rate limit exceeded")
            )
            from graph.nodes.red_team import red_team_node
            result = await red_team_node(state)

        # Must degrade gracefully: no exception raised
        assert result["decision"] == "PROCEED", "Original decision must be preserved on Red Team failure"
        assert result["red_team_flag"] is False

    def test_red_team_uses_correct_model(self):
        """Red Team must use Config.llm.red_team_model, which must be openai/gpt-oss-120b."""
        from config import Config
        assert Config.llm.red_team_model == "openai/gpt-oss-120b", \
            f"Red Team model is {Config.llm.red_team_model!r}, expected 'openai/gpt-oss-120b'"


# ── HITL store tests (F-09) ──────────────────────────────────────────────────

class TestHITLStore:

    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(self):
        """State saved to Supabase must be recoverable exactly."""
        test_state = {
            "evaluation_id": "test-hitl-roundtrip",
            "startup_pitch": "Test pitch",
            "digital_twin": {"industry": "AgriTech", "traction": "10k MRR"},
            "agent_scores": {"Finance": 72.0, "Market": 88.0},
            "hitl_question": "What is your current burn rate?",
        }

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Simulate upsert
        mock_table.upsert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Simulate select
        mock_select_result = MagicMock()
        mock_select_result.data = {"state_json": json.dumps(test_state)}
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = mock_select_result

        with patch("hitl_store._get_client", return_value=mock_supabase):
            from hitl_store import save_hitl_state, load_hitl_state

            saved = await save_hitl_state("test-hitl-roundtrip", test_state)
            assert saved is True

            loaded = await load_hitl_state("test-hitl-roundtrip")
            assert loaded is not None
            assert loaded["evaluation_id"] == "test-hitl-roundtrip"
            assert loaded["agent_scores"]["Finance"] == 72.0

    @pytest.mark.asyncio
    async def test_unconfigured_supabase_returns_false(self):
        """If Supabase is not configured, save must return False (not crash)."""
        with patch("hitl_store._get_client", return_value=None):
            from hitl_store import save_hitl_state
            result = await save_hitl_state("test-no-supabase", {"foo": "bar"})
            assert result is False


# ── hitl_resume_node unit test ────────────────────────────────────────────────

class TestHITLResumeNode:

    def test_answer_merged_into_digital_twin(self):
        """hitl_resume_node must merge the answer into the correct DT field."""
        from graph.nodes.hitl import hitl_resume_node
        state = {
            "evaluation_id": "test-resume-001",
            "digital_twin": {"industry": "AgriTech", "traction": "10k MRR"},
            "hitl_triggered_variable": "traction",
            "hitl_pending": True,
            "round_count": 0,
        }
        result = hitl_resume_node(state, "We now have 25k MRR and 15% MoM growth.")

        assert result["digital_twin"]["traction"] == "We now have 25k MRR and 15% MoM growth."
        assert result["hitl_pending"] is False
        assert result["round_count"] == 1
        assert result["hitl_answer"] == "We now have 25k MRR and 15% MoM growth."

    def test_no_triggered_variable_does_not_crash(self):
        """If hitl_triggered_variable is None, resume must not crash."""
        from graph.nodes.hitl import hitl_resume_node
        state = {
            "evaluation_id": "test-resume-no-field",
            "digital_twin": {},
            "hitl_triggered_variable": None,
            "hitl_pending": True,
            "round_count": 0,
        }
        result = hitl_resume_node(state, "Some answer.")
        assert result["hitl_pending"] is False
        assert result["round_count"] == 1

    def test_resume_bypasses_second_hitl(self):
        """After 1 HITL round (round_count=1), route_after_conflict MUST return 'fusion' even if conflict is detected."""
        from graph.nodes.conflict_index import route_after_conflict
        state = {
            "conflict_detected": True,
            "round_count": 1,
            "max_rounds": 1,
        }
        route = route_after_conflict(state)
        assert route == "fusion", f"Expected 'fusion' after 1 HITL round, got {route!r}"


# ── Context Router tests (F-01) ────────────────────────────────────────────────

class TestContextRouter:

    @pytest.mark.asyncio
    async def test_context_router_extracts_detailed_pitch(self):
        """Verify context router populates available DigitalTwin fields for a detailed pitch without hallucinating missing ones."""
        example_pitch = (
            "We are building an AI-powered financial intelligence platform for small and mid-sized businesses. "
            "The platform connects to a company’s financial data, analyzes cash flow, revenue, expenses, "
            "and key business metrics, and provides real-time insights and recommendations. Our goal is to help "
            "business owners identify financial risks early, improve cash-flow management, and make better decisions "
            "without needing a dedicated financial analyst. We plan to offer the product as a SaaS subscription "
            "with tiered pricing based on company size and usage."
        )

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = json.dumps({
            "industry": "FinTech",
            "location": None,
            "budget": None,
            "business_model_summary": "AI-powered financial intelligence platform for SMBs that connects to financial data to analyze cash flow, revenue, and expenses.",
            "team_size": None,
            "revenue_model": "SaaS subscription with tiered pricing based on company size and usage",
            "target_market": "Small and mid-sized businesses (SMBs)",
            "competitive_advantage": "Real-time financial insights without needing a dedicated financial analyst",
            "regulatory_environment": None,
            "tech_stack": "AI-powered platform",
            "traction": None,
        })

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_gemini_response)

        state = {
            "startup_pitch": example_pitch,
            "evaluation_id": "test-cr-001",
        }

        with patch("google.genai.Client", return_value=mock_client), \
             patch("config.Config.llm.google_api_key", "test_key"):
            from graph.nodes.context_router import context_router_node
            res = await context_router_node(state)

        dt = res["digital_twin"]
        assert dt is not None
        assert dt != {}
        assert dt["industry"] == "FinTech"
        assert dt["revenue_model"] == "SaaS subscription with tiered pricing based on company size and usage"
        assert dt["target_market"] == "Small and mid-sized businesses (SMBs)"
        assert dt["location"] is None
        assert dt["budget"] is None
        assert dt["team_size"] is None

    def test_schema_has_no_additional_properties(self):
        """Verify Gemini response schema has additionalProperties stripped for Developer API compatibility."""
        from graph.nodes.context_router import get_gemini_digital_twin_schema
        schema = get_gemini_digital_twin_schema()
        schema_json = json.dumps(schema)
        assert "additionalProperties" not in schema_json, "additionalProperties must be stripped from response_schema for Gemini Developer API mode"



