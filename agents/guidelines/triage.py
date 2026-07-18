"""Deterministic triage.

Decides which specialists run for a given patient, from patient fields only —
no Claude call, no clinical thresholds (those live in the shelf cards). Each
specialist owns its own `triage_applies` predicate, so adding a specialist means
adding a module, not editing this file.
"""

from __future__ import annotations

from .matcher import extract_features
from .specialists import SPECIALISTS


def select_specialists(patient: dict) -> list[str]:
    """Return the names of the specialists that should run for this patient."""
    features = extract_features(patient)
    return [
        name
        for name, module in SPECIALISTS.items()
        if module.triage_applies(features)
    ]
