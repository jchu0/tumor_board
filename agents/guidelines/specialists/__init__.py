"""Specialist registry.

Each specialist is an independently-callable module exposing:
  - SPECIALIST      : the shelf key (card `specialist` value) it reads
  - SOURCE_AGENT    : its source_agent string in contract (A)
  - triage_applies(features) -> bool : deterministic triage predicate
  - run(patient)    -> list[PartialFinding]

Because the registry is just data, a Claude tool-use loop can later replace the
deterministic triage by exposing each `run` as a tool — without touching the
specialists themselves.
"""

from __future__ import annotations

from . import (
    biomarker_completeness,
    fertility,
    germline,
    goals_of_care,
    guideline_coverage,
)

SPECIALISTS = {
    guideline_coverage.SPECIALIST: guideline_coverage,
    biomarker_completeness.SPECIALIST: biomarker_completeness,
    fertility.SPECIALIST: fertility,
    germline.SPECIALIST: germline,
    goals_of_care.SPECIALIST: goals_of_care,
}

__all__ = ["SPECIALISTS"]
