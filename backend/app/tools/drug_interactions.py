"""check_drug_interactions — canned interaction table lookup."""
from __future__ import annotations

from ._data import load

SCHEMA = {
    "name": "check_drug_interactions",
    "description": (
        "Check a proposed drug against the patient's current medications for known "
        "interactions, using the canned interaction table. Returns matching rows with "
        "severity. Use before recommending any new systemic therapy."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "proposed_drug": {"type": "string"},
            "current_meds": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The patient's current medication names.",
            },
        },
        "required": ["proposed_drug", "current_meds"],
    },
}


def run(proposed_drug: str, current_meds: list[str]) -> dict:
    table = load("interactions.json")
    proposed = proposed_drug.strip().lower()
    current = {m.strip().lower() for m in current_meds}
    hits = [
        row
        for row in table
        if {row["drug_a"].lower(), row["drug_b"].lower()} <= (current | {proposed})
        and proposed in {row["drug_a"].lower(), row["drug_b"].lower()}
    ]
    return {"proposed_drug": proposed_drug, "interactions": hits, "source": "interactions.json"}
