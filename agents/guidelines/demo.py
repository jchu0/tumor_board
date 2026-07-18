"""Demo harness for the guidelines agent.

Runs check_guideline_coverage on the placeholder patient and pretty-prints the
findings. This is my teammate's integration target: it shows exactly the shape
(contract A) the orchestrator will consume.

Usage:
    python -m agents.guidelines.demo                 # uses LLM if a key is set
    python -m agents.guidelines.demo --offline       # deterministic, no network
"""

from __future__ import annotations

import argparse
import json
import os

from .api import check_guideline_coverage
from .config import PLACEHOLDER_PATIENT_PATH


def _load_patient(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _print_finding(index: int, f: dict) -> None:
    status_mark = {"gap": "⚠️  GAP", "addressed": "✅ ADDRESSED", "uncertain": "❓ UNCERTAIN"}
    print(f"\n[{index}] {status_mark.get(f['status'], f['status'].upper())}  ·  {f['domain']}")
    print(f"    source_agent         : {f['source_agent']}")
    print(f"    issue                : {f['issue']}")
    print(f"    recommendation       : {f['recommendation']}")
    print(f"    evidence_ref         : {f['evidence_ref']}")
    print(f"    recommendation_grade : {f['recommendation_grade']}   (from the shelf, verbatim)")
    print(f"    match_confidence     : {f['match_confidence']}")
    print(f"    confidence_rationale : {f['confidence_rationale']}")
    print(f"    patient_facing_note  : {f['patient_facing_note']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Guidelines agent demo")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the Claude synthesis call (deterministic fallback)",
    )
    parser.add_argument(
        "--patient",
        default=PLACEHOLDER_PATIENT_PATH,
        help="path to a patient JSON file (defaults to the placeholder fixture)",
    )
    args = parser.parse_args()

    use_llm = False if args.offline else None
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    mode = (
        "OFFLINE (deterministic fallback)"
        if args.offline
        else ("LLM synthesis (ANTHROPIC_API_KEY detected)" if has_key else "OFFLINE (no ANTHROPIC_API_KEY found)")
    )

    patient = _load_patient(args.patient)

    print("=" * 72)
    print("Tumor Board — guidelines agent demo")
    print(f"patient : {patient.get('id', '<unknown>')}")
    print(f"mode    : {mode}")
    print("=" * 72)

    findings = check_guideline_coverage(patient, use_llm=use_llm)

    gaps = sum(1 for f in findings if f["status"] == "gap")
    print(f"\n{len(findings)} finding(s) — {gaps} gap(s):")
    for i, finding in enumerate(findings):
        _print_finding(i, finding)

    print("\n" + "-" * 72)
    print("Raw contract (A) JSON (what the orchestrator receives):")
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
