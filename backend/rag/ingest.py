"""
AIRB Dataset Ingestion Pipeline
Implements SRS F-02 and F-03.

Responsibilities:
1. Parse CSV or JSONL files of historical startup cases.
2. Validate each case against HistoricalCase schema (reject/flag incomplete records).
3. Enforce the grounding/calibration/test split.
4. HARD GATE (F-03): Test-set case IDs must NEVER enter the vector index.
   This check is automated and run before every evaluation session.

Usage:
    python -m rag.ingest --input data/labeled_cases.jsonl --check-split
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from config import Config
from schemas.digital_twin import HistoricalCase, SplitLabel

logger = logging.getLogger(__name__)


# ── Split Manifest ─────────────────────────────────────────────────────────────

def load_split_manifest() -> dict[str, str]:
    """
    Load case_id → split mapping from the persisted split manifest.
    Returns {} if no manifest exists yet (first run).
    """
    manifest_path = Path(Config.dataset.split_manifest_path)
    if not manifest_path.exists():
        return {}
    with open(manifest_path, "r") as f:
        return json.load(f)


def save_split_manifest(manifest: dict[str, str]) -> None:
    """Persist case_id → split mapping."""
    manifest_path = Path(Config.dataset.split_manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Split manifest saved to {manifest_path}")


# ── Ingestion ──────────────────────────────────────────────────────────────────

def ingest_from_jsonl(input_path: str) -> list[HistoricalCase]:
    """
    Parse a JSONL file of historical cases.
    Each line must conform to HistoricalCase schema.
    Incomplete/malformed records are rejected with a logged warning (not silently dropped).

    Returns list of validated HistoricalCase objects.
    """
    cases: list[HistoricalCase] = []
    rejected = 0
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {input_path}")

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                case = HistoricalCase(**data)
                cases.append(case)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Line {line_num} rejected: {e}")
                rejected += 1

    logger.info(f"Ingested {len(cases)} valid cases; {rejected} rejected.")
    return cases


def ingest_from_csv(input_path: str) -> list[HistoricalCase]:
    """Parse a CSV file of historical cases. Column headers must match HistoricalCase fields."""
    cases: list[HistoricalCase] = []
    rejected = 0
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {input_path}")

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):  # start=2 accounts for header
            try:
                case = HistoricalCase(**row)
                cases.append(case)
            except ValidationError as e:
                logger.warning(f"Row {line_num} rejected: {e}")
                rejected += 1

    logger.info(f"Ingested {len(cases)} valid cases; {rejected} rejected.")
    return cases


# ── Split Assignment ───────────────────────────────────────────────────────────

def assign_splits(cases: list[HistoricalCase]) -> list[HistoricalCase]:
    """
    Assign cases to grounding/calibration/test splits per config ratios.
    Preserves existing assignments from the split manifest (IDs don't change between runs).
    New cases are split by ratio.

    INVARIANT: Once a case is assigned 'test', it stays 'test' forever.
    """
    import random
    manifest = load_split_manifest()

    # Separate cases with existing assignments from new cases
    assigned: list[HistoricalCase] = []
    new_cases: list[HistoricalCase] = []

    for case in cases:
        if case.case_id in manifest:
            # Re-use existing assignment (split stability)
            split = SplitLabel(manifest[case.case_id])
            assigned.append(case.model_copy(update={"split": split}))
        else:
            new_cases.append(case)

    # Shuffle new cases before splitting (reproducible with seed)
    import random
    rng = random.Random(42)
    rng.shuffle(new_cases)

    ratios = Config.dataset.split_ratios
    n_new = len(new_cases)
    n_ground = int(n_new * ratios["grounding"])
    n_cal = int(n_new * ratios["calibration"])
    # Remainder goes to test
    n_test = n_new - n_ground - n_cal

    splits_for_new = (
        [SplitLabel.GROUNDING] * n_ground +
        [SplitLabel.CALIBRATION] * n_cal +
        [SplitLabel.TEST] * n_test
    )

    newly_assigned: list[HistoricalCase] = []
    for case, split in zip(new_cases, splits_for_new):
        updated = case.model_copy(update={"split": split})
        newly_assigned.append(updated)
        manifest[case.case_id] = split.value

    # Persist updated manifest
    save_split_manifest(manifest)

    all_cases = assigned + newly_assigned
    ground_n = sum(1 for c in all_cases if c.split == SplitLabel.GROUNDING)
    cal_n = sum(1 for c in all_cases if c.split == SplitLabel.CALIBRATION)
    test_n = sum(1 for c in all_cases if c.split == SplitLabel.TEST)
    logger.info(f"Split: grounding={ground_n}, calibration={cal_n}, test={test_n}")
    return all_cases


# ── F-03 Hard Gate: Test Leak Prevention ─────────────────────────────────────

def get_test_case_ids() -> set[str]:
    """Return all case_ids assigned to the test split from the manifest."""
    manifest = load_split_manifest()
    return {cid for cid, split in manifest.items() if split == SplitLabel.TEST.value}


def check_no_test_cases_in_index(chroma_collection) -> bool:
    """
    SRS F-03 HARD GATE: Confirm zero overlap between test-set case IDs
    and any ID present in the vector index.

    Args:
        chroma_collection: ChromaDB Collection object

    Returns:
        True if clean (no leakage); raises AssertionError if leakage detected.

    Usage: Call this before every evaluation session.
    """
    test_ids = get_test_case_ids()
    if not test_ids:
        logger.info("No test cases in manifest yet — skip leakage check.")
        return True

    # Query all IDs currently in the ChromaDB collection
    results = chroma_collection.get(include=[])  # IDs only
    indexed_ids = set(results["ids"])

    leaked = test_ids & indexed_ids
    if leaked:
        raise AssertionError(
            f"CRITICAL — Test set leakage detected! "
            f"{len(leaked)} test-set case(s) found in vector index: {leaked}. "
            f"Re-build the index excluding test cases (SRS F-03)."
        )

    logger.info(f"F-03 check passed: 0 test-set cases in vector index ({len(indexed_ids)} total indexed).")
    return True


# ── Export helpers ─────────────────────────────────────────────────────────────

def save_cases_to_jsonl(cases: list[HistoricalCase], output_path: str) -> None:
    """Serialize cases to JSONL for downstream use."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for case in cases:
            f.write(case.model_dump_json() + "\n")
    logger.info(f"Saved {len(cases)} cases to {output_path}")


def load_cases_by_split(split: SplitLabel, jsonl_path: Optional[str] = None) -> list[HistoricalCase]:
    """Load all cases for a given split from JSONL file."""
    path = jsonl_path or Config.dataset.raw_data_path
    all_cases = ingest_from_jsonl(path)
    return [c for c in all_cases if c.split == split]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="AIRB Dataset Ingestion")
    parser.add_argument("--input", default=Config.dataset.raw_data_path)
    parser.add_argument("--output", default="data/historical_cases.jsonl")
    parser.add_argument(
        "--check-split",
        action="store_true",
        help="Only run the F-03 split manifest check, don't re-ingest"
    )
    args = parser.parse_args()

    if args.check_split:
        manifest = load_split_manifest()
        test_ids = {k for k, v in manifest.items() if v == "test"}
        logger.info(f"Test set IDs in manifest: {len(test_ids)}")
        logger.info("Run against a live ChromaDB collection to do the full F-03 check.")
        sys.exit(0)

    # Full ingestion
    ext = Path(args.input).suffix.lower()
    if ext == ".csv":
        cases = ingest_from_csv(args.input)
    else:
        cases = ingest_from_jsonl(args.input)

    cases = assign_splits(cases)
    save_cases_to_jsonl(cases, args.output)
    logger.info("Ingestion complete.")
