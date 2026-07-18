"""Ingestion robustness: partial, unknown, and real-shaped data must all fit."""
from app.ingest import ingest
from app.ingest.fhir_adapter import from_record
from app.ingest.transcript import parse
from app.tools._data import load


def test_bundled_case_normalizes():
    case = ingest(load("case_nsclc_egfr.json"))
    assert case.diagnosis and "lung" in (case.diagnosis.primary_site or "").lower()
    assert case.diagnosis.staging and case.diagnosis.staging.overall_stage
    genes = {b.gene for b in case.biomarkers}
    assert "EGFR" in genes and "PD-L1" in {b.name.upper()[:5] for b in case.biomarkers} or "EGFR" in genes
    assert case.performance_status and case.performance_status.scale == "ECOG"
    assert any(c.name == "Severe COPD" for c in case.comorbidities)
    assert case.goals_of_care and case.goals_of_care.summary
    # Nothing essential should be flagged missing for the full case.
    assert case.completeness() == []


def test_partial_data_still_fits_and_flags_gaps():
    """A sparse record must ingest without error and surface what's absent."""
    sparse = {
        "id": "sparse-1",
        "encounter_fhir": {"related_resources": {
            "Condition": [{"resourceType": "Condition", "code": "Breast carcinoma"}],
        }},
    }
    case = ingest(sparse)
    assert case.diagnosis.primary_site == "Breast carcinoma"
    missing = {m.field for m in case.completeness()}
    assert "biomarkers" in missing
    assert "performance_status" in missing
    assert "goals_of_care" in missing


def test_unknown_resource_type_is_preserved_not_dropped():
    rec = {
        "id": "x",
        "encounter_fhir": {"related_resources": {
            "FamilyMemberHistory": [{"resourceType": "FamilyMemberHistory", "note": "mother, breast ca"}],
        }},
    }
    case = ingest(rec)
    assert len(case.unmapped) == 1
    assert case.unmapped[0]["resourceType"] == "FamilyMemberHistory"


def test_reads_real_fhir_codeableconcept_and_quantity():
    """Adapter must handle full FHIR shapes, not just simplified strings."""
    rec = {
        "id": "fhir-shape",
        "encounter_fhir": {"related_resources": {
            "Observation": [
                {"resourceType": "Observation",
                 "code": {"text": "ECOG performance status"},
                 "valueQuantity": {"value": 2, "unit": "score"}},
                {"resourceType": "Observation",
                 "code": {"coding": [{"display": "EGFR mutation"}]},
                 "valueString": "L858R positive"},
            ],
        }},
    }
    case = from_record(rec)
    assert case.performance_status.value == "2"
    assert any(b.gene == "EGFR" and b.status.value == "positive" for b in case.biomarkers)


def test_transcript_string_parses_to_lines():
    lines = parse("ONCOLOGIST: hello there.\nsecond line continues.\nSURGEON: my turn.")
    assert lines[0]["speaker"] == "ONCOLOGIST"
    assert "second line continues" in lines[0]["text"]  # continuation appended
    assert lines[1]["speaker"] == "SURGEON"
