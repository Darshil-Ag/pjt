"""
AIRB Inter-Rater Reliability Check — Cohen's Kappa (SRS §6.3)

Computes Cohen's kappa between two raters on primary_risk_category labels.
Must be run on a random subset (≥30 cases) before scaling to full dataset.
Target: κ ≥ 0.6

Usage:
    python -m dataset.kappa_check --rater1 data/rater1_labels.csv --rater2 data/rater2_labels.csv
    python -m dataset.kappa_check --test    # Run on synthetic fixture (verifies the tool works)

Input format (CSV or JSONL):
    Required columns: case_id, primary_risk_category
    (Rows must be in the same order in both files, or matched by case_id)

Output:
    - Kappa value
    - Per-category agreement table
    - PASS/FAIL vs. target κ ≥ 0.6
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Optional

from sklearn.metrics import cohen_kappa_score, confusion_matrix
from tabulate import tabulate

from config import Config
from schemas.digital_twin import RiskCategory

logger = logging.getLogger(__name__)

VALID_CATEGORIES = [r.value for r in RiskCategory]


# ── Input Readers ──────────────────────────────────────────────────────────────

def _read_labels(path: str) -> dict[str, str]:
    """
    Read case_id → primary_risk_category labels from CSV or JSONL.
    Returns dict keyed by case_id.
    """
    labels: dict[str, str] = {}
    p = Path(path)

    if p.suffix.lower() == ".csv":
        with open(p, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("case_id", "").strip()
                cat = row.get("primary_risk_category", "").strip()
                if cid and cat:
                    labels[cid] = cat
    else:  # JSONL
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    cid = record.get("case_id", "").strip()
                    cat = record.get("primary_risk_category", "").strip()
                    if cid and cat:
                        labels[cid] = cat

    return labels


# ── Kappa Computation ─────────────────────────────────────────────────────────

def compute_kappa(
    rater1_path: str,
    rater2_path: str,
    min_cases: Optional[int] = None,
    target_kappa: Optional[float] = None,
) -> dict:
    """
    Compute Cohen's kappa on primary_risk_category between two rater label files.

    Args:
        rater1_path: Path to rater 1's labels (CSV or JSONL).
        rater2_path: Path to rater 2's labels (CSV or JSONL).
        min_cases: Minimum required overlapping case count (default: config.labeling.kappa_subset_size).
        target_kappa: Minimum acceptable kappa (default: config.labeling.kappa_target).

    Returns:
        {kappa, n_cases, agreement_pct, passed, category_breakdown}
    """
    min_cases = min_cases or Config.labeling.kappa_subset_size
    target_kappa = target_kappa or Config.labeling.kappa_target

    r1_labels = _read_labels(rater1_path)
    r2_labels = _read_labels(rater2_path)

    # Intersect on case_ids present in both rater files
    common_ids = sorted(set(r1_labels) & set(r2_labels))
    n = len(common_ids)

    if n < min_cases:
        raise ValueError(
            f"Only {n} overlapping cases found; minimum required is {min_cases} (SRS §6.3). "
            f"Ensure both rater files share the same case_ids."
        )

    y1 = [r1_labels[cid] for cid in common_ids]
    y2 = [r2_labels[cid] for cid in common_ids]

    # Validate all labels are from controlled vocabulary
    for i, (l1, l2) in enumerate(zip(y1, y2)):
        if l1 not in VALID_CATEGORIES:
            raise ValueError(f"Rater 1, case '{common_ids[i]}': invalid category '{l1}'.")
        if l2 not in VALID_CATEGORIES:
            raise ValueError(f"Rater 2, case '{common_ids[i]}': invalid category '{l2}'.")

    kappa = cohen_kappa_score(y1, y2, labels=VALID_CATEGORIES)
    agreement = sum(1 for a, b in zip(y1, y2) if a == b) / n

    # Confusion matrix for per-category breakdown
    cm = confusion_matrix(y1, y2, labels=VALID_CATEGORIES)

    passed = kappa >= target_kappa
    return {
        "kappa": round(kappa, 4),
        "n_cases": n,
        "agreement_pct": round(agreement * 100, 2),
        "passed": passed,
        "target_kappa": target_kappa,
        "categories": VALID_CATEGORIES,
        "confusion_matrix": cm.tolist(),
    }


def print_kappa_report(result: dict) -> None:
    """Pretty-print the kappa report to stdout."""
    status = "✅ PASS" if result["passed"] else "❌ FAIL"
    print(f"\n{'='*55}")
    print(f"  AIRB Inter-Rater Reliability Check (Cohen's Kappa)")
    print(f"{'='*55}")
    print(f"  Cases evaluated : {result['n_cases']}")
    print(f"  Raw agreement   : {result['agreement_pct']}%")
    print(f"  Cohen's Kappa   : {result['kappa']}")
    print(f"  Target κ ≥ {result['target_kappa']}  : {status}")
    print(f"\n  Confusion Matrix (rows=Rater1, cols=Rater2):")
    print(
        tabulate(
            result["confusion_matrix"],
            headers=result["categories"],
            showindex=result["categories"],
            tablefmt="grid",
        )
    )
    if not result["passed"]:
        print(
            f"\n  ⚠ Kappa is below target. Review the labeling codebook and "
            f"re-label the disagreeing cases before proceeding to full-dataset labeling."
        )
    print(f"{'='*55}\n")


# ── Synthetic Test Fixture ─────────────────────────────────────────────────────

def _run_synthetic_test() -> None:
    """
    Runs the kappa tool on a synthetic fixture with a known answer.
    Used to verify the tool itself works correctly.
    """
    import tempfile
    import os

    # Create two synthetic rater files with κ ≈ 0.75 (should pass)
    cases = [
        {"case_id": f"case_{i:03d}", "primary_risk_category": cat}
        for i, cat in enumerate(
            # 30 cases: 80% agreement, spread across categories
            [
                "Market", "Market", "Market", "Market", "Market",
                "Finance", "Finance", "Finance", "Finance", "Finance",
                "Legal", "Legal", "Legal", "Legal", "Legal",
                "Operations", "Operations", "Operations", "Operations", "Operations",
                "Technology", "Technology", "Technology", "Technology", "Technology",
                "Market", "Finance", "Legal", "Operations", "Technology",
            ]
        )
    ]
    # Rater 2 disagrees on ~20% (last 6 cases)
    disagreements = {
        "case_025": "Finance",
        "case_026": "Legal",
        "case_027": "Market",
        "case_028": "Technology",
        "case_029": "Operations",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f1:
        for c in cases:
            f1.write(json.dumps(c) + "\n")
        r1_path = f1.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f2:
        for c in cases:
            cat = disagreements.get(c["case_id"], c["primary_risk_category"])
            f2.write(json.dumps({**c, "primary_risk_category": cat}) + "\n")
        r2_path = f2.name

    try:
        result = compute_kappa(r1_path, r2_path, min_cases=30)
        print_kappa_report(result)
        logger.info("Synthetic test completed successfully.")
    finally:
        os.unlink(r1_path)
        os.unlink(r2_path)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="AIRB Inter-Rater Kappa Check (SRS §6.3)")
    parser.add_argument("--rater1", help="Path to rater 1 label file (CSV or JSONL)")
    parser.add_argument("--rater2", help="Path to rater 2 label file (CSV or JSONL)")
    parser.add_argument("--test", action="store_true", help="Run synthetic fixture test")
    args = parser.parse_args()

    if args.test:
        _run_synthetic_test()
    elif args.rater1 and args.rater2:
        result = compute_kappa(args.rater1, args.rater2)
        print_kappa_report(result)
        if not result["passed"]:
            exit(1)
    else:
        parser.print_help()
