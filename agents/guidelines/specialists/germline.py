"""Germline-testing specialist (pure lookup).

Fires when a germline-testing card applies and the chart shows no genetics
referral / germline testing.
"""

from __future__ import annotations

from ..matcher import Features
from .base import PartialFinding, lookup_specialist

SPECIALIST = "germline_testing"
SOURCE_AGENT = "guidelines_agent/germline"


def triage_applies(features: Features) -> bool:
    return bool(features.get("cancer"))


def run(patient: dict) -> list[PartialFinding]:
    return lookup_specialist(
        patient,
        specialist_key=SPECIALIST,
        domain="germline_testing",
        source_agent=SOURCE_AGENT,
        default_issue="Germline genetic testing may apply but is not documented.",
        addressed_keywords=[
            "germline",
            "genetic counseling",
            "genetic testing",
            "genetics referral",
            "brca",
        ],
    )
