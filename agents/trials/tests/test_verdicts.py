"""The three verdicts are produced deterministically and offline."""

from __future__ import annotations

from agents.trials.api import search_trials


def _patient(**overrides) -> dict:
    features = {
        "cancer": ["breast"],
        "stage": ["II"],
        "age": 34,
        "sex": "female",
        "biomarkers_present": ["er", "pr"],
        "planned_therapy_class": ["gonadotoxic"],
    }
    features.update(overrides)
    # biomarker_status is read from Observations; supply it via resources.
    observations = [
        {"resourceType": "Observation", "biomarker": "ER", "valueString": "positive"},
        {"resourceType": "Observation", "biomarker": "PR", "valueString": "positive"},
    ]
    return {
        "id": "TEST-PT",
        "features": features,
        "encounter_fhir": {"resources_by_type": {"Observation": observations}},
    }


def _by_id(findings):
    return {f["trial_id"]: f for f in findings}


def test_all_four_factice_trials_screened():
    findings = search_trials(_patient(), use_llm=False)
    ids = {f["trial_id"] for f in findings}
    assert {"NCT-FACTICE-001", "NCT-FACTICE-002", "NCT-FACTICE-003", "NCT-FACTICE-004"} <= ids


def test_could_enter_when_all_binary_pass():
    f = _by_id(search_trials(_patient(), use_llm=False))["NCT-FACTICE-001"]
    assert f["verdict"] == "could_enter"
    assert f["match_confidence"] == "high"


def test_cannot_enter_names_the_decisive_criterion():
    # Trial 002 requires ER-negative; the patient is ER-positive -> blocked.
    f = _by_id(search_trials(_patient(), use_llm=False))["NCT-FACTICE-002"]
    assert f["verdict"] == "cannot_enter"
    assert f["criteria_blocking"]
    assert any("ER-negative" in c for c in f["criteria_blocking"])


def test_possible_when_a_binary_fact_is_missing():
    # Trial 003 needs HER2 status; the patient has none recorded.
    f = _by_id(search_trials(_patient(), use_llm=False))["NCT-FACTICE-003"]
    assert f["verdict"] == "possible_with_more_info"
    assert any("HER2" in c for c in f["criteria_missing_info"])


def test_freetext_criteria_are_unknown_offline_not_guessed():
    # Trial 004 has free-text criteria; offline they must be unknown (never a
    # fabricated pass/fail), yielding a "need info" verdict rather than a wrong
    # eligibility call.
    f = _by_id(search_trials(_patient(), use_llm=False))["NCT-FACTICE-004"]
    assert f["verdict"] == "possible_with_more_info"
    assert any("organ function" in c for c in f["criteria_missing_info"])


def test_documented_biomarker_flips_the_verdict():
    # Give the patient HER2-positive and trial 003 becomes enterable.
    patient = _patient(biomarkers_present=["er", "pr", "her2"])
    patient["encounter_fhir"]["resources_by_type"]["Observation"].append(
        {"resourceType": "Observation", "biomarker": "HER2", "valueString": "positive"}
    )
    f = _by_id(search_trials(patient, use_llm=False))["NCT-FACTICE-003"]
    assert f["verdict"] == "could_enter"
