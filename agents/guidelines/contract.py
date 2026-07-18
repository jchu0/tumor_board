"""Contract (A): the findings output shape shared with the orchestrator.

This is the boundary between the guidelines agent and my teammate's
orchestrator. Field names here are EXACT and must not drift. `validate_finding`
is the single source of truth for that shape and is exercised by the tests.
"""

from __future__ import annotations

from typing import Any

# The ten fields of contract (A), in a stable order.
FINDING_FIELDS: tuple[str, ...] = (
    "domain",
    "issue",
    "recommendation",
    "evidence_ref",
    "recommendation_grade",
    "match_confidence",
    "confidence_rationale",
    "patient_facing_note",
    "status",
    "source_agent",
)

MATCH_CONFIDENCE_VALUES = frozenset({"high", "moderate", "low"})
STATUS_VALUES = frozenset({"gap", "addressed", "uncertain"})


def validate_finding(finding: dict[str, Any]) -> None:
    """Raise ValueError if `finding` does not conform to contract (A)."""
    if not isinstance(finding, dict):
        raise ValueError(f"finding must be a dict, got {type(finding).__name__}")

    missing = [f for f in FINDING_FIELDS if f not in finding]
    if missing:
        raise ValueError(f"finding missing required fields: {missing}")

    extra = [k for k in finding if k not in FINDING_FIELDS]
    if extra:
        raise ValueError(f"finding has unexpected fields: {extra}")

    for field in FINDING_FIELDS:
        if not isinstance(finding[field], str):
            raise ValueError(
                f"finding field '{field}' must be a string, "
                f"got {type(finding[field]).__name__}"
            )

    if finding["match_confidence"] not in MATCH_CONFIDENCE_VALUES:
        raise ValueError(
            f"match_confidence must be one of {sorted(MATCH_CONFIDENCE_VALUES)}, "
            f"got {finding['match_confidence']!r}"
        )

    if finding["status"] not in STATUS_VALUES:
        raise ValueError(
            f"status must be one of {sorted(STATUS_VALUES)}, "
            f"got {finding['status']!r}"
        )

    # The confidence rationale is REQUIRED — it is what makes the two-axis
    # confidence model honest. An empty rationale is a contract violation.
    if not finding["confidence_rationale"].strip():
        raise ValueError("confidence_rationale must be a non-empty sentence")
