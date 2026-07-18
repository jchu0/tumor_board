"""The planted fertility-preservation gap is caught."""

from __future__ import annotations

import json

from agents.guidelines.api import check_guideline_coverage
from agents.guidelines.config import PLACEHOLDER_PATIENT_PATH


def _patient() -> dict:
    with open(PLACEHOLDER_PATIENT_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_fertility_gap_is_caught():
    findings = check_guideline_coverage(_patient(), use_llm=False)
    fertility = [
        f for f in findings if f["source_agent"] == "guidelines_agent/fertility"
    ]
    assert fertility, "fertility specialist should have produced a finding"
    assert any(
        f["status"] == "gap" and f["domain"] == "fertility_preservation"
        for f in fertility
    ), "the placeholder fertility gap should be flagged as a gap"


def test_documented_item_is_not_a_gap():
    # If the chart documents fertility counseling, the item should flip to
    # 'addressed' — proving addressed-detection actually reads the chart.
    patient = _patient()
    patient["encounter_fhir"]["resources_by_type"]["Procedure"] = [
        {
            "resourceType": "Procedure",
            "code": {"text": "oncofertility referral completed"},
        }
    ]
    findings = check_guideline_coverage(patient, use_llm=False)
    fertility = [
        f for f in findings if f["source_agent"] == "guidelines_agent/fertility"
    ]
    assert fertility
    assert all(f["status"] == "addressed" for f in fertility)
