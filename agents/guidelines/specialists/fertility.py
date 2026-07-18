"""Fertility-preservation specialist (pure lookup).

Fires when a fertility-preservation card applies (e.g. a premenopausal patient
facing gonadotoxic therapy) and the chart shows no fertility counseling.
"""

from __future__ import annotations

from ..matcher import Features
from .base import PartialFinding, lookup_specialist

SPECIALIST = "fertility_preservation"
SOURCE_AGENT = "guidelines_agent/fertility"


def triage_applies(features: Features) -> bool:
    # Fertility preservation is only meaningful when we know cancer + age.
    return bool(features.get("cancer")) and features.get("age") is not None


def run(patient: dict) -> list[PartialFinding]:
    return lookup_specialist(
        patient,
        specialist_key=SPECIALIST,
        domain="fertility_preservation",
        source_agent=SOURCE_AGENT,
        default_issue="Fertility preservation may apply but is not documented.",
        addressed_keywords=[
            "fertility",
            "oncofertility",
            "reproductive endocrinology",
            "sperm banking",
            "egg preservation",
        ],
    )
