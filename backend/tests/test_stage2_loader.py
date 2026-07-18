"""Per-patient folder loader — the isolation guarantees must hold (no API key)."""
import pathlib

import pytest

from app.stage2.loader import (
    MixedPatientDataError,
    discover_patients,
    load_all,
    load_patient_folder,
)

PATIENTS = pathlib.Path(__file__).parents[2] / "fixtures" / "patients"


def test_discover_lists_patient_folders():
    names = {p.name for p in discover_patients(PATIENTS)}
    assert {"patient-001", "patient-002"} <= names
    # a reserved reference dataset name would be skipped
    assert "abridge" not in names


def test_one_folder_one_bundle_no_cross_contamination():
    """The core guarantee: loading patient-001 yields ONLY patient-001's data."""
    b1 = load_patient_folder(PATIENTS / "patient-001")
    b2 = load_patient_folder(PATIENTS / "patient-002")

    # patient-001 is the lung/EGFR case; NONE of patient-002's data leaks in.
    assert "lung" in (b1.diagnosis.primary_site or "").lower()
    assert any(bm.gene == "EGFR" for bm in b1.biomarkers)
    assert "breast" not in (b1.diagnosis.primary_site or "").lower()
    assert not any(m.name == "tamoxifen" for m in b1.medications)

    # patient-002 is the breast/HER2 case; no lung/EGFR/warfarin from patient-001.
    assert "breast" in (b2.diagnosis.primary_site or "").lower()
    assert not any(bm.gene == "EGFR" for bm in b2.biomarkers)
    assert not any(m.name == "warfarin" for m in b2.medications)


def test_case_id_is_the_folder_name_partition_key():
    b1 = load_patient_folder(PATIENTS / "patient-001")
    assert b1.case_id == "patient-001"  # folder name, NOT the file's internal id ("pt-001")


def test_multiple_files_are_assembled():
    """patient-001 has patient.json + clinical.json (Bundle) + metadata.json + transcript.txt."""
    b1 = load_patient_folder(PATIENTS / "patient-001")
    assert b1.patient.sex == "female"                 # from patient.json
    assert b1.board_date == "2026-07-18"              # from metadata.json
    assert len(b1.biomarkers) >= 1 and b1.medications  # from clinical.json Bundle


def test_mixed_patient_data_raises():
    """A folder whose files reference two patients must fail loudly, not merge."""
    with pytest.raises(MixedPatientDataError) as e:
        load_patient_folder(PATIENTS / "patient-mixed")
    assert "pt-100" in str(e.value) and "pt-999" in str(e.value)


def test_load_all_isolates_failures():
    bundles, errors = load_all(PATIENTS)
    # good patients load
    assert "patient-001" in bundles and "patient-002" in bundles
    # bad folders are isolated to errors, not raised, not merged
    assert "patient-mixed" in errors and "patient-broken" in errors
    assert "MixedPatientDataError" in errors["patient-mixed"]
    # a broken folder never contaminated a good one
    assert bundles["patient-001"].case_id == "patient-001"


def test_deterministic_load():
    a = load_patient_folder(PATIENTS / "patient-001")
    b = load_patient_folder(PATIENTS / "patient-001")
    assert a.source_digest == b.source_digest
    assert [x.element_id for x in a.biomarkers] == [x.element_id for x in b.biomarkers]
