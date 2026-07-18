"""Guideline-coverage specialist (pure lookup).

Surfaces guideline recommendations that apply to this patient and checks
whether the plan already addresses them.
"""

from __future__ import annotations

from ..matcher import Features
from .base import PartialFinding, lookup_specialist

SPECIALIST = "guideline_coverage"
SOURCE_AGENT = "guidelines_agent/guideline_coverage"


def triage_applies(features: Features) -> bool:
    return bool(features.get("cancer"))


def run(patient: dict) -> list[PartialFinding]:
    return lookup_specialist(
        patient,
        specialist_key=SPECIALIST,
        domain="guideline_coverage",
        source_agent=SOURCE_AGENT,
        default_issue="A guideline recommendation applies; confirm it is addressed in the plan.",
        addressed_keywords=["guideline addressed", "plan documented"],
    )
