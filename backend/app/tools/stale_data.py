"""flag_stale_data — surface missing or aging chart data, incl. goals-of-care staleness.

Goals-of-care is first-class: if the plan trends aggressive and the documented GOC
conversation is old or doesn't cover this scenario, emit a 'revisit goals of care'
signal (README §1a Tier 1.5).
"""
from __future__ import annotations

from datetime import date

SCHEMA = {
    "name": "flag_stale_data",
    "description": (
        "Given chart fields with 'last updated' dates, flag anything missing or older than "
        "a freshness threshold. Pass goals_of_care_date and whether the emerging plan is "
        "aggressive to check goals-of-care staleness/mismatch."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "last_updated": {"type": "string", "description": "ISO date or null."},
                    },
                    "required": ["name"],
                },
            },
            "as_of": {"type": "string", "description": "ISO date to measure against (the board date)."},
            "stale_after_days": {"type": "integer", "default": 180},
            "goals_of_care_date": {"type": "string"},
            "plan_is_aggressive": {"type": "boolean", "default": False},
        },
        "required": ["fields", "as_of"],
    },
}


def _age_days(iso: str | None, as_of: date) -> int | None:
    if not iso:
        return None
    try:
        return (as_of - date.fromisoformat(iso)).days
    except ValueError:
        return None


def run(fields, as_of, stale_after_days=180, goals_of_care_date=None, plan_is_aggressive=False):
    as_of_d = date.fromisoformat(as_of)
    flags = []
    for f in fields:
        age = _age_days(f.get("last_updated"), as_of_d)
        if age is None:
            flags.append({"field": f["name"], "reason": "missing or undated"})
        elif age > stale_after_days:
            flags.append({"field": f["name"], "reason": f"last updated {age} days ago"})

    goc_age = _age_days(goals_of_care_date, as_of_d)
    if plan_is_aggressive and (goc_age is None or goc_age > stale_after_days):
        flags.append(
            {
                "field": "goals_of_care",
                "reason": "plan trends aggressive but goals-of-care is missing/stale — consider revisiting with the patient",
            }
        )
    return {"stale_or_missing": flags}
