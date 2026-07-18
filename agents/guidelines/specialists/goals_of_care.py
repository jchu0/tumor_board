"""Goals-of-care specialist (staleness / completeness check).

Custom logic detects whether a goals-of-care conversation is documented and,
if so, how old it is. The staleness threshold (`staleness_days`) is reference
data read from the shelf card, not hard-coded.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..loader import get_cards
from ..matcher import Features, extract_features, get_resources_by_type, match_cards
from .base import PartialFinding

SPECIALIST = "goals_of_care"
SOURCE_AGENT = "guidelines_agent/goals_of_care"

_DEFAULT_KEYWORDS = ["goals of care", "goals-of-care", "advance care planning"]
_DEFAULT_STALENESS_DAYS = 180
_DATE_FIELDS = (
    "date",
    "recordedDate",
    "effectiveDateTime",
    "authored",
    "authoredOn",
    "created",
)


def _today() -> date:
    # Wrapped so tests can monkeypatch a fixed "today" if needed.
    return date.today()


def triage_applies(features: Features) -> bool:
    return bool(features.get("cancer"))


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _resource_date(resource: dict) -> date | None:
    for fieldname in _DATE_FIELDS:
        parsed = _parse_date(resource.get(fieldname))
        if parsed:
            return parsed
    period = resource.get("period")
    if isinstance(period, dict):
        return _parse_date(period.get("start"))
    return None


def _latest_goc_date(patient: dict, keywords: list[str]) -> date | None:
    import json

    lowered = [k.lower() for k in keywords]
    latest: date | None = None
    for resources in get_resources_by_type(patient).values():
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            text = json.dumps(resource, default=str).lower()
            if not any(k in text for k in lowered):
                continue
            found = _resource_date(resource)
            if found and (latest is None or found > latest):
                latest = found
    return latest


def run(patient: dict) -> list[PartialFinding]:
    features = extract_features(patient)
    findings: list[PartialFinding] = []

    for card, matched in match_cards(get_cards(SPECIALIST), features):
        keywords = (card.get("addressed_when") or {}).get(
            "any_resource_text"
        ) or _DEFAULT_KEYWORDS
        staleness_days = int(card.get("staleness_days", _DEFAULT_STALENESS_DAYS))
        last_date = _latest_goc_date(patient, keywords)

        if last_date is None:
            status = "gap"
            issue = "No goals-of-care conversation is documented."
            detail: dict[str, Any] = {"documented": False, "staleness_days": staleness_days}
        else:
            age_days = (_today() - last_date).days
            detail = {
                "documented": True,
                "last_date": last_date.isoformat(),
                "age_days": age_days,
                "staleness_days": staleness_days,
            }
            if age_days > staleness_days:
                status = "gap"
                issue = (
                    f"Goals-of-care conversation is stale: last documented "
                    f"{age_days} days ago (threshold {staleness_days} days)."
                )
                detail["stale"] = True
            else:
                status = "addressed"
                issue = (
                    f"Goals-of-care conversation documented {age_days} days ago "
                    f"(within {staleness_days}-day threshold)."
                )
                detail["stale"] = False

        findings.append(
            PartialFinding(
                domain=card.get("domain", "goals_of_care"),
                issue=issue,
                recommendation=card["recommendation"],
                evidence_ref=card["evidence_ref"],
                recommendation_grade=card["recommendation_grade"],
                status=status,
                source_agent=SOURCE_AGENT,
                matched_card_id=card.get("id", ""),
                applies_when=card.get("applies_when", {}),
                matched_on=matched,
                detail=detail,
            )
        )
    return findings
