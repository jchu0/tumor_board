"""flag_stale_data — surface missing or aging chart data.

Goals-of-care staleness is NOT handled here. It is owned by the goals-of-care
precondition (app/goc.py), which evaluates it deterministically before guidance
rather than as a tool the model may or may not call. This tool covers general
chart-field staleness only.
"""
from __future__ import annotations

from datetime import date

SCHEMA = {
    "name": "flag_stale_data",
    "description": (
        "Given chart fields with 'last updated' dates, flag anything missing or older than "
        "a freshness threshold."
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


def run(fields, as_of, stale_after_days=180):
    as_of_d = date.fromisoformat(as_of)
    flags = []
    for f in fields:
        age = _age_days(f.get("last_updated"), as_of_d)
        if age is None:
            flags.append({"field": f["name"], "reason": "missing or undated"})
        elif age > stale_after_days:
            flags.append({"field": f["name"], "reason": f"last updated {age} days ago"})
    return {"stale_or_missing": flags}
