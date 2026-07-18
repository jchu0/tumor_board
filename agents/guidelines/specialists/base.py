"""Shared building blocks for specialists.

`PartialFinding` carries everything the CODE is allowed to decide (issue,
recommendation, evidence_ref, recommendation_grade, status, ...) plus context
the synthesis Claude call reasons over. The three confidence/plain-language
fields are added later by synthesis.py — never here.

`lookup_specialist` implements the pure-lookup pattern (match cards, then decide
gap/addressed from the chart) so the lookup-only specialists — guideline
coverage, fertility, germline — are each just a couple of lines.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..loader import get_cards
from ..matcher import extract_features, match_cards


@dataclass
class PartialFinding:
    # Code-owned fields (become contract (A) verbatim; grade/rec/ref come
    # straight from the card and are never touched by the model).
    domain: str
    issue: str
    recommendation: str
    evidence_ref: str
    recommendation_grade: str
    status: str  # "gap" | "addressed" | "uncertain"
    source_agent: str

    # Provenance + context passed to the synthesis call and the offline
    # fallback. Not part of contract (A).
    matched_card_id: str = ""
    applies_when: dict = field(default_factory=dict)
    matched_on: dict = field(default_factory=dict)
    detail: dict = field(default_factory=dict)

    def public_base(self) -> dict[str, str]:
        """The seven code-owned contract (A) fields."""
        return {
            "domain": self.domain,
            "issue": self.issue,
            "recommendation": self.recommendation,
            "evidence_ref": self.evidence_ref,
            "recommendation_grade": self.recommendation_grade,
            "status": self.status,
            "source_agent": self.source_agent,
        }


def patient_text_blob(patient: dict) -> str:
    """Whole patient file as one lowercased string, for keyword scanning."""
    return json.dumps(patient, default=str).lower()


def is_addressed(card: dict, patient: dict, default_keywords: list[str]) -> bool:
    """Decide whether the chart already documents this item.

    Uses the card's optional `addressed_when.any_resource_text` keywords if the
    physician authored them; otherwise falls back to sensible defaults so the
    physician is never forced to write `addressed_when`.
    """
    addressed_when = card.get("addressed_when") or {}
    keywords = addressed_when.get("any_resource_text") or default_keywords
    blob = patient_text_blob(patient)
    return any(str(k).lower() in blob for k in keywords)


def lookup_specialist(
    patient: dict,
    *,
    specialist_key: str,
    domain: str,
    source_agent: str,
    default_issue: str,
    addressed_keywords: list[str],
) -> list[PartialFinding]:
    """The generic pure-lookup flow shared by lookup-only specialists."""
    features = extract_features(patient)
    findings: list[PartialFinding] = []
    for card, matched in match_cards(get_cards(specialist_key), features):
        addressed = is_addressed(card, patient, addressed_keywords)
        findings.append(
            PartialFinding(
                domain=card.get("domain", domain),
                issue=card.get("issue", default_issue),
                recommendation=card["recommendation"],
                evidence_ref=card["evidence_ref"],
                recommendation_grade=card["recommendation_grade"],
                status="addressed" if addressed else "gap",
                source_agent=source_agent,
                matched_card_id=card.get("id", ""),
                applies_when=card.get("applies_when", {}),
                matched_on=matched,
                detail={"addressed": addressed},
            )
        )
    return findings
