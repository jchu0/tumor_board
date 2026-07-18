"""Tool registry for the orchestrator.

The guideline and trial checks are backed by the repo-root ``agents/`` packages
(deterministic matching + bounded LLM synthesis over factice data, with a canned
fallback); the rest are plain functions over canned tables. ``TOOL_DEFS`` is the
Anthropic tool-use schema list; ``dispatch`` routes a tool_use call to its impl.

The repo root is put on ``sys.path`` here (once, at package import) so
``import agents.guidelines`` resolves the packages one level above ``backend/`` —
without moving them. This is the TOP-LEVEL ``agents`` package (guidelines/trials),
distinct from ``app.agents`` (the enrichment agent).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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
