"""search_trials — canned trial matcher with real logistics, not binary yes/no.

Reports partial eligibility ("4 of 5 criteria, missing confirmed EGFR"), plus
recruitment status and site distance so a molecularly-perfect but closed/far trial
isn't surfaced as a useful match (README §1a Tier 1.3).
"""
from __future__ import annotations

from ._data import load

SCHEMA = {
    "name": "search_trials",
    "description": (
        "Match the patient against the canned trial list by biomarker and staging. "
        "Returns per-trial eligibility (criteria met / missing), recruitment status, "
        "and site feasibility. Prefer trials that are OPEN and reachable."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "biomarkers": {"type": "array", "items": {"type": "string"}},
            "cancer_type": {"type": "string"},
            "stage": {"type": "string"},
        },
        "required": ["biomarkers", "cancer_type"],
    },
}


def run(biomarkers: list[str], cancer_type: str, stage: str | None = None) -> dict:
    trials = load("trials.json")
    wanted = {b.strip().lower() for b in biomarkers}
    matches = []
    for t in trials:
        if cancer_type.lower() not in t["cancer_type"].lower():
            continue
        criteria = t["inclusion_criteria"]
        met = [c for c in criteria if c["biomarker"].lower() in wanted or c.get("always_met")]
        missing = [c for c in criteria if c not in met]
        matches.append(
            {
                "nct_id": t["nct_id"],
                "title": t["title"],
                "criteria_met": f"{len(met)}/{len(criteria)}",
                "missing_criteria": [c["label"] for c in missing],
                "recruitment_status": t["recruitment_status"],
                "site_distance_miles": t["site_distance_miles"],
                "reported_benefit": t.get("reported_benefit"),
            }
        )
    return {"matches": matches, "source": "trials.json"}
