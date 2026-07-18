"""Patient fact extraction for trial matching.

Reuses the guidelines feature extractor (cancer, stage, age, sex, biomarkers
present, planned therapy class) and adds a biomarker *status* map (e.g.
HER2 -> "positive") that trial criteria often need. Both tools read the same
patient file; this is the trials-side view of it.
"""

from __future__ import annotations

from typing import Any

from ..guidelines.matcher import extract_features as _base_features
from ..guidelines.matcher import get_resources_by_type

Facts = dict[str, Any]


def extract_patient_facts(patient: dict) -> Facts:
    facts: Facts = dict(_base_features(patient))

    status: dict[str, str] = {}
    for obs in get_resources_by_type(patient).get("Observation", []):
        if not isinstance(obs, dict) or not obs.get("biomarker"):
            continue
        name = str(obs["biomarker"]).strip().lower()
        value = obs.get("valueString") or obs.get("value") or obs.get("interpretation")
        # "" means present-but-no-value -> treated as UNKNOWN by the evaluator.
        status[name] = str(value).strip().lower() if value is not None else ""
    facts["biomarker_status"] = status

    # Explicit override hook, mirroring the guidelines side.
    override = patient.get("features")
    if isinstance(override, dict):
        facts.update(override)
    return facts
