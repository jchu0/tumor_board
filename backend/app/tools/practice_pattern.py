"""check_practice_pattern (Tier 2) — canned 'historical decisions' lookup.

Strictly a QA/audit signal ("worth confirming this reflects patient-specific factors
rather than default habit"), NEVER pressure to conform. See README §1a Tier 2.
"""
from __future__ import annotations

from ._data import load

SCHEMA = {
    "name": "check_practice_pattern",
    "description": (
        "Look up how this board has historically chosen between two options for similar "
        "cases (canned table). Return the ratio as an audit signal only — never as a "
        "recommendation to conform."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "option_a": {"type": "string"},
            "option_b": {"type": "string"},
        },
        "required": ["option_a", "option_b"],
    },
}


def run(option_a: str, option_b: str) -> dict:
    table = load("practice_patterns.json")
    for row in table:
        pair = {row["option_a"].lower(), row["option_b"].lower()}
        if {option_a.lower(), option_b.lower()} == pair:
            return {**row, "framing": "audit_signal_only", "source": "practice_patterns.json"}
    return {"match": None, "framing": "audit_signal_only", "source": "practice_patterns.json"}
