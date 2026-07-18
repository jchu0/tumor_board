"""Biomarker-completeness specialist (completeness check).

Holds a little custom logic (compare required vs present biomarkers) but pulls
its reference data — which biomarkers are required for this cancer — from the
shelf card's `requires` list, never hard-coded.
"""

from __future__ import annotations

from ..loader import get_cards
from ..matcher import Features, extract_features, match_cards
from .base import PartialFinding

SPECIALIST = "biomarker_completeness"
SOURCE_AGENT = "guidelines_agent/biomarker_completeness"


def triage_applies(features: Features) -> bool:
    return bool(features.get("cancer"))


def run(patient: dict) -> list[PartialFinding]:
    features = extract_features(patient)
    present = {b.lower() for b in features.get("biomarkers_present", [])}

    findings: list[PartialFinding] = []
    for card, matched in match_cards(get_cards(SPECIALIST), features):
        required = card.get("requires", [])
        missing = [b for b in required if str(b).lower() not in present]

        if missing:
            status = "gap"
            issue = "Required biomarkers not documented: " + ", ".join(missing) + "."
        else:
            status = "addressed"
            issue = "All required biomarkers documented: " + ", ".join(required) + "."

        findings.append(
            PartialFinding(
                domain=card.get("domain", "biomarker_completeness"),
                issue=issue,
                recommendation=card["recommendation"],
                evidence_ref=card["evidence_ref"],
                recommendation_grade=card["recommendation_grade"],
                status=status,
                source_agent=SOURCE_AGENT,
                matched_card_id=card.get("id", ""),
                applies_when=card.get("applies_when", {}),
                matched_on=matched,
                detail={
                    "required": list(required),
                    "present": sorted(present),
                    "missing": missing,
                },
            )
        )
    return findings
