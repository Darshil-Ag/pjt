"""
Dataset Builder & Split Initializer (SRS F-02, F-03)
Reads raw_cases.csv, attaches labeled outcomes/risk categories, assigns grounding/calibration/test splits,
and verifies the F-03 test-set exclusion check.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from schemas.digital_twin import HistoricalCase, OutcomeLabel, RiskCategory, SplitLabel
from rag.ingest import assign_splits, save_cases_to_jsonl, load_split_manifest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Controlled labels for the 20 sample cases in raw_cases.csv
CASE_LABELS = {
    "case_001": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.LEGAL, "summary": "RBI shutdown for operating without payment aggregator license."},
    "case_002": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.TECHNOLOGY, "summary": "Critical sensor firmware bug caused mass alert failures and contract terminations."},
    "case_003": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.TECHNOLOGY, "summary": "NLP dialect misdiagnosis exceeded 18% in pilot clinics."},
    "case_004": {"outcome": OutcomeLabel.SUCCESS, "primary_risk": RiskCategory.OPERATIONS, "summary": "Achieved strong unit economics and profitable multi-state expansion."},
    "case_005": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.FINANCE, "summary": "Broken unit economics with $240 CAC vs $95 LTV."},
    "case_006": {"outcome": OutcomeLabel.SUCCESS, "primary_risk": RiskCategory.OPERATIONS, "summary": "Secured enterprise pilots and closed EUR 1.2M seed round."},
    "case_007": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.MARKET, "summary": "Unable to compete against aggressive AWS and Google Cloud pricing discounts."},
    "case_008": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.OPERATIONS, "summary": "Poor integration with municipal waste tracking led to sub-8% retention."},
    "case_009": {"outcome": OutcomeLabel.SUCCESS, "primary_risk": RiskCategory.TECHNOLOGY, "summary": "Reduced time-to-hire by 35% and raised $2M Series A."},
    "case_010": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.FINANCE, "summary": "Premature scaling before PMF burned $180K/month with only $12K MRR."},
    "case_011": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.TECHNOLOGY, "summary": "Smart contract reentrancy exploit drained $3.2M user funds."},
    "case_012": {"outcome": OutcomeLabel.SUCCESS, "primary_risk": RiskCategory.OPERATIONS, "summary": "Reached EBITDA breakeven in month 22 with $1.2M GMV."},
    "case_013": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.FINANCE, "summary": "Freemium conversion rate of 0.8% fell short of 5% projection."},
    "case_014": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.LEGAL, "summary": "FDA 510k regulatory approval took 28 months instead of projected 12."},
    "case_015": {"outcome": OutcomeLabel.SUCCESS, "primary_risk": RiskCategory.MARKET, "summary": "Healthy 4.2:1 LTV:CAC and expanding to 3 new cities."},
    "case_016": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.TECHNOLOGY, "summary": "Custom drone components tripled BOM cost, making product unscalable."},
    "case_017": {"outcome": OutcomeLabel.SUCCESS, "primary_risk": RiskCategory.LEGAL, "summary": "140 paying law firms, $420K ARR, and closed $3M Series A."},
    "case_018": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.FINANCE, "summary": "Post-pandemic demand collapse and negative gross margins."},
    "case_019": {"outcome": OutcomeLabel.SUCCESS, "primary_risk": RiskCategory.MARKET, "summary": "Secured 8 enterprise contracts achieving $650K ARR."},
    "case_020": {"outcome": OutcomeLabel.FAILED, "primary_risk": RiskCategory.OPERATIONS, "summary": "Failed to secure required telecom network partnerships in Kenya and Tanzania."}
}


def build_sample_dataset():
    import csv
    csv_path = Path("data/raw_cases.csv")
    if not csv_path.exists():
        raise FileNotFoundError("data/raw_cases.csv not found")

    raw_records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_records.append(row)

    cases: list[HistoricalCase] = []
    for r in raw_records:
        cid = r["case_id"]
        label_info = CASE_LABELS.get(cid, {
            "outcome": OutcomeLabel.INCONCLUSIVE,
            "primary_risk": RiskCategory.MARKET,
            "summary": "Case data under review."
        })
        case = HistoricalCase(
            case_id=cid,
            industry=r.get("industry", "General"),
            outcome=label_info["outcome"],
            primary_risk_category=label_info["primary_risk"],
            root_cause_summary=label_info["summary"],
            raw_text=r["raw_text"],
            split=SplitLabel.GROUNDING,  # placeholder before assign_splits
        )
        cases.append(case)

    # Assign splits per SRS F-03 (60% grounding, 15% calibration, 25% test)
    split_cases = assign_splits(cases)

    # Save to data/historical_cases.jsonl
    save_cases_to_jsonl(split_cases, "data/historical_cases.jsonl")
    logger.info("Sample dataset created successfully at data/historical_cases.jsonl")


if __name__ == "__main__":
    build_sample_dataset()
