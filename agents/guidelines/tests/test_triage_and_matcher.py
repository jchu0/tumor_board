"""Triage selection and the generic matcher behave deterministically."""

from __future__ import annotations

from agents.guidelines.matcher import extract_features, patient_satisfies
from agents.guidelines.triage import select_specialists


def test_no_cancer_selects_nothing():
    assert select_specialists({"features": {}}) == []


def test_cancer_without_age_skips_fertility():
    patient = {"features": {"cancer": ["breast"], "age": None}}
    selected = select_specialists(patient)
    assert "fertility_preservation" not in selected
    assert "guideline_coverage" in selected


def test_cancer_with_age_selects_fertility():
    patient = {"features": {"cancer": ["breast"], "age": 34}}
    assert "fertility_preservation" in select_specialists(patient)


def test_matcher_respects_age_bounds():
    aw = {"cancer": ["breast"], "age_min": 18, "age_max": 45}
    ok, _ = patient_satisfies(aw, {"cancer": ["breast"], "age": 34})
    assert ok
    too_old, _ = patient_satisfies(aw, {"cancer": ["breast"], "age": 60})
    assert not too_old


def test_matcher_requires_present_data():
    # A stated constraint the patient can't back up means no match.
    aw = {"cancer": ["breast"], "stage": ["II"]}
    ok, _ = patient_satisfies(aw, {"cancer": ["breast"], "stage": []})
    assert not ok


def test_matcher_is_case_insensitive():
    ok, matched = patient_satisfies({"cancer": ["Breast"]}, {"cancer": ["BREAST"]})
    assert ok
    assert matched["cancer"] == ["breast"]


def test_extract_features_reads_fhir_ish_patient():
    patient = {
        "patient_context": {"patient": {"gender": "female", "age": 34}},
        "encounter_fhir": {
            "resources_by_type": {
                "Condition": [{"cancer": "breast", "stage": "II"}],
                "Observation": [{"biomarker": "ER"}, {"biomarker": "PR"}],
                "MedicationRequest": [{"therapy_class": "gonadotoxic"}],
            }
        },
    }
    features = extract_features(patient)
    assert features["cancer"] == ["breast"]
    assert features["stage"] == ["ii"]
    assert features["age"] == 34
    assert set(features["biomarkers_present"]) == {"er", "pr"}
    assert features["planned_therapy_class"] == ["gonadotoxic"]
