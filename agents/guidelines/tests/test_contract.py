"""Every finding validates against contract (A)."""

from __future__ import annotations

import json

from agents.guidelines.api import check_guideline_coverage
from agents.guidelines.config import PLACEHOLDER_PATIENT_PATH
from agents.guidelines.contract import FINDING_FIELDS, validate_finding


def _patient() -> dict:
    with open(PLACEHOLDER_PATIENT_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_findings_are_produced():
    findings = check_guideline_coverage(_patient(), use_llm=False)
    assert findings, "expected the placeholder patient to produce findings"


def test_every_finding_matches_contract_a():
    findings = check_guideline_coverage(_patient(), use_llm=False)
    for finding in findings:
        # Raises on any violation (fields, types, enum values, empty rationale).
        validate_finding(finding)
        # Exact field set — no missing, no extra.
        assert set(finding.keys()) == set(FINDING_FIELDS)


def test_rationale_is_non_empty_for_every_finding():
    findings = check_guideline_coverage(_patient(), use_llm=False)
    assert findings
    for finding in findings:
        assert finding["confidence_rationale"].strip()
