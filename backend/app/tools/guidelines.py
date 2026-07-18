"""check_guideline_coverage — did the room address the guideline-preferred options?"""
from __future__ import annotations

from ._data import load

SCHEMA = {
    "name": "check_guideline_coverage",
    "description": (
        "Look up guideline-preferred options for the patient's cancer type/stage/biomarker "
        "and return each with its Class-of-Recommendation / Level-of-Evidence grade. The "
        "orchestrator compares these against what the transcript actually discussed to find gaps."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cancer_type": {"type": "string"},
            "stage": {"type": "string"},
            "biomarkers": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["cancer_type"],
    },
}


def run(cancer_type: str, stage: str | None = None, biomarkers: list[str] | None = None) -> dict:
    table = load("guidelines.json")
    options = [
        g
        for g in table
        if cancer_type.lower() in g["cancer_type"].lower()
        and (stage is None or stage.lower() in g.get("stage", "").lower() or not g.get("stage"))
    ]
    return {"guideline_options": options, "source": "guidelines.json"}
