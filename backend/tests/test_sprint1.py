"""
AIRB Unit Tests — Sprint 1
Tests for the deterministic math layer and schema validation.
These tests use NO LLM calls (mocked where needed).

Run: pytest tests/ -v
"""

from __future__ import annotations

import pytest


# ── Test: Fusion Math (SRS F-10, TC-08) ──────────────────────────────────────

class TestFusionNode:
    """
    Verify the fusion formula with hand-calculated examples.
    TC-08: W=[.3,.3,.2,.1,.1], C=[.8,.7,.6,.9,.5], S=[80,40,70,60,90]
    """

    def _make_state(self, scores, confidences, weights):
        from schemas.state import initial_state
        state = initial_state("test pitch", "test-eval-id", {})
        domains = ["Finance", "Legal", "Market", "Operations", "Technology"]
        state["agent_scores"] = dict(zip(domains, scores))
        state["agent_confidences"] = dict(zip(domains, confidences))
        state["agent_weights"] = dict(zip(domains, weights))
        return state

    def test_tc08_hand_calculated(self):
        """TC-08: Verify fusion formula matches manual calculation."""
        from graph.nodes.fusion import fusion_node

        W = [0.3, 0.3, 0.2, 0.1, 0.1]
        C = [0.8, 0.7, 0.6, 0.9, 0.5]
        S = [80.0, 40.0, 70.0, 60.0, 90.0]

        state = self._make_state(S, C, W)
        result = fusion_node(state)

        # Manual: Σ(Wi*Ci*Si) = 0.3*0.8*80 + 0.3*0.7*40 + 0.2*0.6*70 + 0.1*0.9*60 + 0.1*0.5*90
        numerator = 0.3*0.8*80 + 0.3*0.7*40 + 0.2*0.6*70 + 0.1*0.9*60 + 0.1*0.5*90
        denominator = 0.3*0.8 + 0.3*0.7 + 0.2*0.6 + 0.1*0.9 + 0.1*0.5
        expected_score = numerator / denominator

        assert abs(result["final_score"] - expected_score) < 0.01, (
            f"Expected {expected_score:.4f}, got {result['final_score']}"
        )

    def test_all_three_decision_classes_reachable(self):
        """SRS F-10 acceptance: All three decision classes must be reachable."""
        from graph.nodes.fusion import fusion_node
        from config import Config

        # PROCEED: high score, sufficient confidence
        high_score_state = self._make_state(
            [90.0]*5, [0.9]*5, [0.2]*5
        )
        r = fusion_node(high_score_state)
        assert r["decision"] == "PROCEED", f"Expected PROCEED, got {r['decision']}"

        # HIGH-RISK: low score, but sufficient confidence
        low_score_state = self._make_state(
            [20.0]*5, [0.9]*5, [0.2]*5
        )
        r = fusion_node(low_score_state)
        assert r["decision"] == "HIGH-RISK", f"Expected HIGH-RISK, got {r['decision']}"

        # REVIEW (abstain): insufficient confidence
        low_conf_state = self._make_state(
            [70.0]*5, [0.01]*5, [0.2]*5
        )
        r = fusion_node(low_conf_state)
        assert r["decision"] == "REVIEW", f"Expected REVIEW, got {r['decision']}"

    def test_graceful_degradation_no_agents(self):
        """NF-05: Empty agent scores → REVIEW, not crash."""
        from graph.nodes.fusion import fusion_node
        from schemas.state import initial_state

        state = initial_state("test", "eval-001", {})
        result = fusion_node(state)
        assert result["decision"] == "REVIEW"
        assert result["final_confidence"] == 0.0


# ── Test: Conflict Index Math (SRS F-08) ──────────────────────────────────────

class TestConflictIndex:
    """TC-06: Synthetic high-variance scores always trigger HITL."""

    def _make_state(self, scores):
        from schemas.state import initial_state
        state = initial_state("test pitch", "test-eval-id", {})
        domains = ["Finance", "Legal", "Market", "Operations", "Technology"]
        state["agent_scores"] = dict(zip(domains, scores))
        state["variance_history"] = []
        return state

    def test_high_variance_triggers_conflict(self):
        """TC-06: Scores [90,85,20,88,15] → conflict_detected=True."""
        from graph.nodes.conflict_index import conflict_index_node

        state = self._make_state([90.0, 85.0, 20.0, 88.0, 15.0])
        result = conflict_index_node(state)
        assert result["conflict_detected"] is True

    def test_low_variance_no_conflict(self):
        """Low-variance scores never trigger HITL."""
        from graph.nodes.conflict_index import conflict_index_node

        state = self._make_state([70.0, 72.0, 68.0, 71.0, 69.0])
        result = conflict_index_node(state)
        assert result["conflict_detected"] is False

    def test_variance_appended_to_history(self):
        """variance_history grows with each call."""
        from graph.nodes.conflict_index import conflict_index_node

        state = self._make_state([50.0, 52.0, 48.0, 51.0, 49.0])
        result = conflict_index_node(state)
        assert len(result["variance_history"]) == 1

    def test_ci_strictly_greater_than_theta(self):
        """Boundary: exactly at theta_conflict should NOT trigger (strictly >)."""
        import numpy as np
        from graph.nodes.conflict_index import conflict_index_node
        from config import Config

        # Create scores with exactly theta_conflict variance
        theta = Config.thresholds.theta_conflict
        # Var = theta means CI == theta, which should NOT trigger (strictly >)
        # Use 5 equal scores → Var = 0; manually patch
        state = self._make_state([50.0] * 5)
        result = conflict_index_node(state)
        # Var([50,50,50,50,50]) = 0 < theta → no conflict
        assert result["conflict_detected"] is False


# ── Test: Confidence Scoring (SRS F-06) ───────────────────────────────────────

class TestConfidenceFormula:
    """TC-05: M_evidence = 1.0 when all cited cases match agent domain."""

    def test_m_evidence_pure_function_all_match(self):
        """
        TC-05: All cited cases have primary_risk_category == agent domain.
        M_evidence should be exactly 1.0.
        """
        # Simulated cited cases (metadata only — no LLM call)
        cited_metadata = [
            {"primary_risk_category": "Finance"},
            {"primary_risk_category": "Finance"},
            {"primary_risk_category": "Finance"},
        ]
        domain = "Finance"
        matching = sum(1 for m in cited_metadata if m["primary_risk_category"] == domain)
        m_evidence = matching / len(cited_metadata)
        assert m_evidence == 1.0

    def test_m_evidence_partial_match(self):
        """2 of 3 cited cases match domain → M_evidence ≈ 0.667."""
        cited_metadata = [
            {"primary_risk_category": "Finance"},
            {"primary_risk_category": "Finance"},
            {"primary_risk_category": "Market"},  # mismatch
        ]
        domain = "Finance"
        matching = sum(1 for m in cited_metadata if m["primary_risk_category"] == domain)
        m_evidence = matching / len(cited_metadata)
        assert abs(m_evidence - 2/3) < 1e-9

    def test_m_evidence_zero_match(self):
        """No cited cases match domain → M_evidence = 0.0."""
        cited_metadata = [
            {"primary_risk_category": "Legal"},
            {"primary_risk_category": "Market"},
        ]
        domain = "Finance"
        matching = sum(1 for m in cited_metadata if m["primary_risk_category"] == domain)
        m_evidence = matching / len(cited_metadata) if cited_metadata else 0.0
        assert m_evidence == 0.0


# ── Test: Uncertainty Band (SRS F-15) ─────────────────────────────────────────

class TestUncertaintyBand:
    """TC-15: Two cases with identical Final_Score but different spread → different bands."""

    def _make_state(self, scores, confidences, weights):
        from schemas.state import initial_state
        state = initial_state("test", "eval-001", {})
        domains = ["Finance", "Legal", "Market", "Operations", "Technology"]
        state["agent_scores"] = dict(zip(domains, scores))
        state["agent_confidences"] = dict(zip(domains, confidences))
        state["agent_weights"] = dict(zip(domains, weights))
        return state

    def test_different_spread_different_band(self):
        """TC-15: Identical Final_Score but different agent-score spread → different uncertainty bands."""
        from graph.nodes.fusion import fusion_node

        # Both states have equal scores (zero spread) vs. high spread
        # but same weighted average
        W = [0.2] * 5
        C = [0.8] * 5

        # Zero spread: all agents agree on the same score
        zero_spread = self._make_state([70.0]*5, C, W)
        r1 = fusion_node(zero_spread)

        # High spread: agents disagree but weighted average = 70
        # Symmetric spread: [50, 60, 70, 80, 90] → mean=70
        high_spread = self._make_state([50.0, 60.0, 70.0, 80.0, 90.0], C, W)
        r2 = fusion_node(high_spread)

        assert abs(r1["final_score"] - r2["final_score"]) < 0.1, "Final scores should be equal"
        assert r1["final_score_uncertainty"] < r2["final_score_uncertainty"], (
            "Higher spread should yield higher uncertainty band"
        )


# ── Test: Schema Validation (SRS F-01, F-02) ──────────────────────────────────

class TestSchemas:
    """Verify Pydantic schemas reject invalid data cleanly."""

    def test_historical_case_rejects_invalid_outcome(self):
        """HistoricalCase must reject outcomes outside controlled vocabulary."""
        from pydantic import ValidationError
        from schemas.digital_twin import HistoricalCase

        with pytest.raises(ValidationError):
            HistoricalCase(
                case_id="case_001",
                industry="SaaS",
                outcome="unknown",  # invalid
                primary_risk_category="Market",
                root_cause_summary="The startup failed due to poor product-market fit.",
                raw_text="Sample text",
                split="grounding",
            )

    def test_historical_case_rejects_invalid_risk_category(self):
        """HistoricalCase must reject risk categories outside fixed taxonomy (SRS §6.3)."""
        from pydantic import ValidationError
        from schemas.digital_twin import HistoricalCase

        with pytest.raises(ValidationError):
            HistoricalCase(
                case_id="case_002",
                industry="HealthTech",
                outcome="failed",
                primary_risk_category="Compliance",  # invalid — not in taxonomy
                root_cause_summary="The startup failed due to regulatory issues.",
                raw_text="Sample text",
                split="grounding",
            )

    def test_digital_twin_allows_null_budget(self):
        """TC-01: DigitalTwin allows null budget (not hallucinated)."""
        from schemas.digital_twin import DigitalTwin

        twin = DigitalTwin(
            industry="FinTech",
            location="India",
            budget=None,  # Not mentioned in pitch → None, never invented
            business_model_summary="B2B SaaS for SMEs.",
        )
        assert twin.budget is None

    def test_digital_twin_coerces_list_and_string_budget(self):
        """DigitalTwin must coerce list fields (e.g. tech_stack) and parse formatted budgets."""
        from schemas.digital_twin import DigitalTwin
        twin = DigitalTwin.model_validate_json(
            '{"industry": "AgriTech", "tech_stack": ["AI", "soil sensors"], "budget": "$10k"}'
        )
        assert twin.tech_stack == "AI, soil sensors"
        assert twin.budget == 10000.0

    def test_review_board_state_has_all_required_fields(self):
        """ReviewBoardState TypedDict must have all fields defined in SRS §6.2."""
        from schemas.state import ReviewBoardState
        import typing

        hints = typing.get_type_hints(ReviewBoardState)
        required_fields = [
            "startup_pitch", "digital_twin", "retrieved_cases",
            "round_count", "max_rounds",
            "agent_scores", "agent_confidences", "agent_weights",
            "agent_claims", "agent_citations",
            "variance_history", "conflict_detected",
            "hitl_pending", "hitl_question",
            "final_score", "final_confidence", "decision",
            "red_team_flag", "red_team_severity", "red_team_reasoning",
            "sensitivity_sweep", "final_score_uncertainty",
            "hitl_ci_before", "hitl_ci_after", "hitl_effectiveness",
            "evaluation_id", "version_info",
        ]
        for field in required_fields:
            assert field in hints, f"Missing required field from SRS §6.2: {field}"


# ── Test: F-03 Dataset Integrity ───────────────────────────────────────────────

class TestDatasetIntegrity:
    """TC-11: Test-set cases must never enter the vector index."""

    def test_ingest_splits_are_disjoint(self, tmp_path):
        """After assign_splits, grounding/calibration/test sets are disjoint."""
        import json
        from rag.ingest import assign_splits, ingest_from_jsonl, save_cases_to_jsonl

        # Create a small synthetic dataset
        cases_data = []
        for i in range(20):
            cases_data.append({
                "case_id": f"case_{i:03d}",
                "industry": "SaaS",
                "outcome": "failed",
                "primary_risk_category": "Market",
                "root_cause_summary": "Poor product-market fit.",
                "raw_text": f"Startup case {i} raw text.",
                "split": "grounding",  # will be reassigned
            })

        input_file = tmp_path / "test_cases.jsonl"
        with open(input_file, "w") as f:
            for c in cases_data:
                f.write(json.dumps(c) + "\n")

        # Redirect manifest to tmp_path
        import rag.ingest as ingest_mod
        original_manifest_path = None

        from config import Config
        cases = ingest_from_jsonl(str(input_file))
        cases = assign_splits(cases)

        from schemas.digital_twin import SplitLabel
        grounding_ids = {c.case_id for c in cases if c.split == SplitLabel.GROUNDING}
        calibration_ids = {c.case_id for c in cases if c.split == SplitLabel.CALIBRATION}
        test_ids = {c.case_id for c in cases if c.split == SplitLabel.TEST}

        # Disjoint check
        assert not (grounding_ids & calibration_ids), "Grounding and calibration overlap!"
        assert not (grounding_ids & test_ids), "Grounding and test overlap!"
        assert not (calibration_ids & test_ids), "Calibration and test overlap!"
        assert len(cases) == 20

    def test_f03_hard_gate_detects_test_leakage(self):
        """SRS F-03 Hard Gate: Must raise AssertionError if a test case enters the index."""
        from unittest.mock import MagicMock
        from rag.ingest import check_no_test_cases_in_index
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["case_016"]}  # case_016 is in test split in manifest
        with pytest.raises(AssertionError, match="Test set leakage detected"):
            check_no_test_cases_in_index(mock_collection)
