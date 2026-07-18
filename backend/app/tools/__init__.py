"""Tool registry for the orchestrator.

Each sub-check is a plain function over canned data (README §5: no live clinical
APIs in the demo). ``TOOL_DEFS`` is the Anthropic tool-use schema list; ``dispatch``
routes a tool_use call to its implementation.
"""
from __future__ import annotations

from typing import Any, Callable

from . import (
    drug_interactions,
    guidelines,
    operability,
    practice_pattern,
    stale_data,
    trials,
)

# name -> (callable, tool schema)
_REGISTRY: dict[str, tuple[Callable[..., Any], dict]] = {
    "check_drug_interactions": (drug_interactions.run, drug_interactions.SCHEMA),
    "search_trials": (trials.run, trials.SCHEMA),
    "check_guideline_coverage": (guidelines.run, guidelines.SCHEMA),
    "flag_stale_data": (stale_data.run, stale_data.SCHEMA),
    "check_operability": (operability.run, operability.SCHEMA),
    # Tier 2 — safe to leave registered; the orchestrator calls it only if useful.
    "check_practice_pattern": (practice_pattern.run, practice_pattern.SCHEMA),
}

TOOL_DEFS: list[dict] = [schema for _, schema in _REGISTRY.values()]


def dispatch(name: str, tool_input: dict) -> Any:
    if name not in _REGISTRY:
        return {"error": f"unknown tool: {name}"}
    fn, _ = _REGISTRY[name]
    return fn(**tool_input)
