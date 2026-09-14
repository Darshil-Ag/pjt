"""
AIRB LLM-Assisted Labeling Pipeline (BRD §6)
Implements the first-pass labeling step using Gemini 2.5 Flash.

Workflow:
1. Read raw startup case text (CSV or JSONL with case_id + raw_text).
2. Call Gemini to propose: primary_risk_category, outcome, root_cause_summary.
3. Write labeled JSONL for human verification.
4. Human corrects labels; the corrected file feeds kappa_check.py.

This keeps labeling cost sub-linear in team hours (BRD §6 tip).
Human verification is REQUIRED — this pipeline produces proposals, not ground truth.

Usage:
    python -m dataset.label_pipeline --input data/raw_cases.csv --output data/labeled_draft.jsonl
    python -m dataset.label_pipeline --input data/raw_cases.csv --limit 30  # subset for kappa
"""

from __future__ import annotations

import csv
import json
import logging
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types as genai_types

from config import Config
from schemas.digital_twin import OutcomeLabel, RiskCategory

logger = logging.getLogger(__name__)

# ── Taxonomy (SRS §6.3 — fixed, no free-text categories) ─────────────────────
VALID_OUTCOMES = [o.value for o in OutcomeLabel]
VALID_RISK_CATEGORIES = [r.value for r in RiskCategory]

LABEL_PROMPT_TEMPLATE = """You are an expert startup analyst helping label historical startup cases for an academic dataset.

Given the following startup case text, output a JSON object with EXACTLY these three fields:
1. "outcome": one of exactly ["success", "failed", "inconclusive"]
2. "primary_risk_category": the SINGLE dominant risk domain, one of exactly ["Market", "Finance", "Legal", "Operations", "Technology"]
3. "root_cause_summary": 2-3 sentence explanation of the primary outcome driver

Rules:
- Use ONLY the exact values listed above. No free-text variations.
- "primary_risk_category" must be the SINGLE most dominant risk, not multiple.
- "root_cause_summary" must be factual, not speculative.
- Output ONLY valid JSON, no markdown, no explanation.

Startup Case:
---
{raw_text}
---

JSON:"""


# ── Gemini Helper ─────────────────────────────────────────────────────────────

def _get_gemini_model() -> genai.Client:
    api_key = Config.llm.google_api_key
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not set (NF-03).")
    return genai.Client(api_key=api_key)


def _call_gemini_label(client: genai.Client, raw_text: str) -> Optional[dict]:
    """Call Gemini to produce a label proposal. Returns dict or None on failure."""
    prompt = LABEL_PROMPT_TEMPLATE.format(raw_text=raw_text[:4000])  # safety trim
    try:
        response = client.models.generate_content(
            model=Config.llm.router_model,
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Gemini label call failed: {e}")
        return None


def _validate_label(label: dict) -> bool:
    """Validate that proposed label uses controlled vocabulary."""
    if label.get("outcome") not in VALID_OUTCOMES:
        return False
    if label.get("primary_risk_category") not in VALID_RISK_CATEGORIES:
        return False
    if not label.get("root_cause_summary", "").strip():
        return False
    return True


# ── Input Readers ──────────────────────────────────────────────────────────────

def read_raw_csv(path: str) -> list[dict]:
    """
    Read raw cases from CSV. Required columns: case_id, raw_text.
    Optional: industry (used in output but not required for labeling).
    """
    records = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("case_id") or not row.get("raw_text"):
                logger.warning(f"Skipping row with missing case_id or raw_text: {row}")
                continue
            records.append(dict(row))
    return records


def read_raw_jsonl(path: str) -> list[dict]:
    """Read raw cases from JSONL. Each line: {case_id, raw_text, [industry]}."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON line: {e}")
    return records


# ── Main Labeling Function ─────────────────────────────────────────────────────

def run_labeling_pipeline(
    input_path: str,
    output_path: str,
    limit: Optional[int] = None,
    delay_seconds: float = 1.0,
) -> int:
    """
    Run the LLM-assisted labeling pipeline.

    Args:
        input_path: CSV or JSONL of raw cases (case_id + raw_text required).
        output_path: JSONL output with proposed labels (for human verification).
        limit: Optional max number of cases to label (useful for kappa subset).
        delay_seconds: Delay between API calls to stay within free-tier rate limits.

    Returns:
        Number of successfully labeled cases.
    """
    path = Path(input_path)
    if path.suffix.lower() == ".csv":
        records = read_raw_csv(input_path)
    else:
        records = read_raw_jsonl(input_path)

    if limit:
        records = records[:limit]

    logger.info(f"Labeling {len(records)} cases from {input_path}...")
    client = _get_gemini_model()

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    success_count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for i, record in enumerate(records, start=1):
            case_id = record["case_id"]
            raw_text = record["raw_text"]

            label = _call_gemini_label(client, raw_text)

            if label is None or not _validate_label(label):
                logger.warning(f"[{i}/{len(records)}] {case_id}: label failed or invalid — skipping.")
                continue

            output_record = {
                "case_id": case_id,
                "raw_text": raw_text,
                "industry": record.get("industry", ""),
                "outcome": label["outcome"],
                "primary_risk_category": label["primary_risk_category"],
                "root_cause_summary": label["root_cause_summary"],
                "split": "grounding",  # Default; assign_splits() will reassign
                # Flag for human verification
                "_llm_proposed": True,
                "_human_verified": False,
            }
            f.write(json.dumps(output_record) + "\n")
            success_count += 1

            logger.info(
                f"[{i}/{len(records)}] {case_id}: "
                f"outcome={label['outcome']}, risk={label['primary_risk_category']}"
            )

            # Rate limiting
            if i < len(records):
                time.sleep(delay_seconds)

    logger.info(f"Labeling complete: {success_count}/{len(records)} cases labeled → {output_path}")
    return success_count


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="AIRB LLM-Assisted Labeling Pipeline")
    parser.add_argument("--input", default=Config.labeling.raw_input_path)
    parser.add_argument("--output", default=Config.labeling.output_path)
    parser.add_argument("--limit", type=int, default=None, help="Max cases to label")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")
    args = parser.parse_args()

    run_labeling_pipeline(args.input, args.output, limit=args.limit, delay_seconds=args.delay)
