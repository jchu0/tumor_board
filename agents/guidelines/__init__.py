"""Guidelines agent — the guideline-coverage sub-check of the tumor board.

Public surface is exactly one function:

    from agents.guidelines import check_guideline_coverage
    findings = check_guideline_coverage(patient)   # -> list[dict], contract (A)
"""

from __future__ import annotations

from .api import check_guideline_coverage
from .config import MODEL

__all__ = ["check_guideline_coverage", "MODEL"]
