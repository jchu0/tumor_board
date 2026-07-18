"""Patient feature extraction + the generic `applies_when` matcher.

Two responsibilities, kept separate so each specialist stays thin:

1. `extract_features` turns a FHIR-ish patient file into a flat dict of
   matchable attributes (cancer, stage, age, biomarkers present, ...). This is
   the only place that knows the patient's on-disk shape.

2. `match_cards` / `patient_satisfies` is a GENERIC matcher over contract (B)
   `applies_when` blocks. Every specialist reuses it.

The patient file follows the schema the physician authors (see README, contract
for the patient). It is FHIR-*flavoured*: resources grouped by type, with a few
plain convenience fields on each resource (`cancer`, `stage`, `biomarker`,
`therapy_class`) that a real FHIR mapping layer would derive from coded fields.
A top-level `features` block can override anything, which keeps testing trivial.
"""

from __future__ import annotations

from datetime import date
from typing import Any

Features = dict[str, Any]

# applies_when keys that are numeric bounds rather than list membership.
_AGE_MIN = "age_min"
_AGE_MAX = "age_max"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _lower_strs(values: Any) -> list[str]:
    return [str(v).strip().lower() for v in _as_list(values) if str(v).strip()]


def get_resources_by_type(patient: dict) -> dict[str, list[dict]]:
    """Return the {resourceType: [resources]} mapping, tolerant of layout."""
    for path in (
        ("encounter_fhir", "resources_by_type"),
        ("resources_by_type",),
        ("resources",),
    ):
        node: Any = patient
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                node = None
                break
        if isinstance(node, dict):
            return {k: _as_list(v) for k, v in node.items()}
    return {}


def _get_patient_resource(patient: dict) -> dict:
    ctx = patient.get("patient_context")
    if isinstance(ctx, dict) and isinstance(ctx.get("patient"), dict):
        return ctx["patient"]
    if isinstance(patient.get("patient"), dict):
        return patient["patient"]
    return {}


def _age_from_birthdate(birth: str) -> int | None:
    try:
        b = date.fromisoformat(birth[:10])
    except (ValueError, TypeError):
        return None
    today = date.today()
    years = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    return years if years >= 0 else None


def extract_features(patient: dict) -> Features:
    """Flatten a patient file into matchable attributes."""
    resources = get_resources_by_type(patient)
    patient_res = _get_patient_resource(patient)

    cancers: list[str] = []
    stages: list[str] = []
    for cond in resources.get("Condition", []):
        if not isinstance(cond, dict):
            continue
        if cond.get("cancer"):
            cancers.extend(_lower_strs(cond["cancer"]))
        stage = cond.get("stage")
        if isinstance(stage, dict):  # FHIR-style stage.summary.text
            stage = (stage.get("summary") or {}).get("text") if isinstance(
                stage.get("summary"), dict
            ) else stage.get("summary")
        if stage:
            stages.extend(_lower_strs(stage))

    biomarkers: list[str] = []
    for obs in resources.get("Observation", []):
        if isinstance(obs, dict) and obs.get("biomarker"):
            biomarkers.extend(_lower_strs(obs["biomarker"]))

    therapy_classes: list[str] = []
    for med in resources.get("MedicationRequest", []):
        if isinstance(med, dict) and med.get("therapy_class"):
            therapy_classes.extend(_lower_strs(med["therapy_class"]))

    age: int | None = None
    if isinstance(patient_res.get("age"), (int, float)):
        age = int(patient_res["age"])
    elif patient_res.get("birthDate"):
        age = _age_from_birthdate(patient_res["birthDate"])

    features: Features = {
        "cancer": sorted(set(cancers)),
        "stage": sorted(set(stages)),
        "sex": (patient_res.get("gender") or "").strip().lower() or None,
        "age": age,
        "biomarkers_present": sorted(set(biomarkers)),
        "planned_therapy_class": sorted(set(therapy_classes)),
    }

    # Explicit overrides win — the simplest possible authoring/testing hook.
    override = patient.get("features")
    if isinstance(override, dict):
        features.update(override)
    return features


def patient_satisfies(applies_when: dict, features: Features) -> tuple[bool, dict]:
    """Does the patient satisfy every constraint in an `applies_when` block?

    Returns (satisfied, matched_on) where matched_on records the specific
    patient facts that satisfied each constraint — used to build the rationale.
    A missing/empty patient value for a stated constraint means NOT satisfied
    (conservative: we do not fire a card on data the patient can't back up).
    """
    matched: dict[str, Any] = {}
    for key, constraint in (applies_when or {}).items():
        if key in (_AGE_MIN, _AGE_MAX):
            age = features.get("age")
            if age is None:
                return False, {}
            if key == _AGE_MIN and age < constraint:
                return False, {}
            if key == _AGE_MAX and age > constraint:
                return False, {}
            matched["age"] = age
            continue

        allowed = set(_lower_strs(constraint))
        have = _lower_strs(features.get(key))
        intersection = [h for h in have if h in allowed]
        if not intersection:
            return False, {}
        matched[key] = intersection
    return True, matched


def match_cards(cards: list[dict], features: Features) -> list[tuple[dict, dict]]:
    """Return [(card, matched_on), ...] for every card the patient satisfies."""
    results: list[tuple[dict, dict]] = []
    for card in cards:
        ok, matched = patient_satisfies(card.get("applies_when", {}), features)
        if ok:
            results.append((card, matched))
    return results
