"""Trials agent — the trial-eligibility sub-check of the tumor board.

Parallel to the guidelines agent; one public callable:

    from agents.trials import search_trials
    findings = search_trials(patient)   # -> list[dict]
"""

from __future__ import annotations

from .api import search_trials
from .config import MODEL

__all__ = ["search_trials", "MODEL"]
