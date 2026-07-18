"""Demo harness for the trials agent.

Screens the shared placeholder patient against the factice trials and prints the
three-way verdict for each.

    python -m agents.trials.demo            # uses the agent (LLM) if a key is set
    python -m agents.trials.demo --offline  # deterministic only, no network
"""

from __future__ import annotations

import argparse
import json
import os

from ..guidelines.config import PLACEHOLDER_PATIENT_PATH
from .api import search_trials

_MARK = {
    "could_enter": "✅ COULD ENTER",
    "cannot_enter": "❌ CANNOT ENTER",
    "possible_with_more_info": "🟡 COULD ENTER IF WE GET INFO",
}


def _load_patient(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _print(f: dict) -> None:
    print(f"\n{_MARK.get(f['verdict'], f['verdict'])}  ·  {f['trial_id']} — {f['title']}")
    print(f"    recruitment_status   : {f['recruitment_status']}")
    print(f"    match_confidence     : {f['match_confidence']}")
    if f["criteria_met"]:
        print(f"    met                  : {', '.join(f['criteria_met'])}")
    if f["criteria_blocking"]:
        print(f"    blocking             : {', '.join(f['criteria_blocking'])}")
    if f["criteria_missing_info"]:
        print(f"    missing info         : {', '.join(f['criteria_missing_info'])}")
    print(f"    confidence_rationale : {f['confidence_rationale']}")
    print(f"    patient_facing_note  : {f['patient_facing_note']}")
    if f["live_question"]:
        print(f"    live_question        : {f['live_question']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trials agent demo")
    parser.add_argument("--offline", action="store_true", help="skip the agent (LLM) call")
    parser.add_argument("--patient", default=PLACEHOLDER_PATIENT_PATH)
    args = parser.parse_args()

    use_llm = False if args.offline else None
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    mode = (
        "OFFLINE (binary criteria only)"
        if args.offline
        else ("AGENT (ANTHROPIC_API_KEY detected)" if has_key else "OFFLINE (no ANTHROPIC_API_KEY)")
    )

    patient = _load_patient(args.patient)
    print("=" * 72)
    print("Tumor Board — trials agent demo")
    print(f"patient : {patient.get('id', '<unknown>')}")
    print(f"mode    : {mode}")
    print("=" * 72)

    findings = search_trials(patient, use_llm=use_llm)
    counts = {v: sum(1 for f in findings if f["verdict"] == v) for v in _MARK}
    print(
        f"\n{len(findings)} trial(s): "
        f"{counts['could_enter']} could enter, "
        f"{counts['possible_with_more_info']} need info, "
        f"{counts['cannot_enter']} cannot enter"
    )
    for f in findings:
        _print(f)

    print("\n" + "-" * 72)
    print("Raw JSON (what the orchestrator receives):")
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
