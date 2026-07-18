"""Deterministic evaluation of binary trial criteria.

A criterion with a `check` block is evaluated straight from the patient facts
into one of three results: PASS / FAIL / UNKNOWN. UNKNOWN means the patient file
simply does not contain the fact — which is what drives the "could enter if we
get X" verdict.
"""

from __future__ import annotations

from typing import Any

from ..guidelines.matcher import _lower_strs  # shared list-normaliser
from .extract import Facts

PASS = "pass"
FAIL = "fail"
UNKNOWN = "unknown"

# Fields a binary `check` can pull directly from the patient file.
_LIST_FIELDS = ("cancer", "stage", "biomarkers_present", "planned_therapy_class")


def _resolve(check: dict, facts: Facts) -> Any:
    """Return the patient's value for a check's field, or None if absent."""
    field = check.get("field")
    if field == "biomarker":
        name = str(check.get("biomarker", "")).strip().lower()
        value = facts.get("biomarker_status", {}).get(name)
        return value or None  # "" (present-no-value) -> None -> UNKNOWN
    if field == "age":
        return facts.get("age")
    if field == "sex":
        return facts.get("sex")
    if field in _LIST_FIELDS:
        return facts.get(field) or None
    return None  # unknown field name -> UNKNOWN


def evaluate_check(check: dict, facts: Facts) -> str:
    patient_val = _resolve(check, facts)
    if patient_val is None or patient_val == "":
        return UNKNOWN

    op = check.get("op")
    value = check.get("value")

    if op in ("in", "not_in"):
        allowed = set(_lower_strs(value))
        have = set(_lower_strs(patient_val))
        hit = bool(have & allowed)
        if op == "in":
            return PASS if hit else FAIL
        return FAIL if hit else PASS

    if op == "equals":
        return PASS if str(patient_val).strip().lower() == str(value).strip().lower() else FAIL

    if op in ("gte", "lte", "gt", "lt"):
        try:
            pv, v = float(patient_val), float(value)
        except (TypeError, ValueError):
            return UNKNOWN
        ok = {
            "gte": pv >= v,
            "lte": pv <= v,
            "gt": pv > v,
            "lt": pv < v,
        }[op]
        return PASS if ok else FAIL

    return UNKNOWN
