"""Stage 2 contract invariants (docs/stage-interface-contract.yaml §1, §2, §7).

All run without an API key — Stage 2 makes zero model calls.
"""
import json
import pathlib

import pytest
import yaml

from app.stage2 import to_bundle
from app.stage2.bundle import REQUIRED_SELECTORS, PatientCaseBundle
from app.stage2.enums import BiomarkerCategory, MedIntent, PerfScale, StageGroup, TreatmentKind, TriState
from app.stage2.ids import slug, stage_group, value_num

ROOT = pathlib.Path(__file__).parents[2]
CONTRACT = yaml.safe_load((ROOT / "docs" / "stage-interface-contract.yaml").read_text())
FX = ROOT / "fixtures" / "contract" / "v1"
SOURCE = json.loads((FX / "source_record.json").read_text())


# --- §6 enum drift: the Python enums must equal the contract's closed sets -----
def _contract_vals(key):
    v = CONTRACT["enumerations"][key]
    return set(v["values"] if isinstance(v, dict) else v)


@pytest.mark.parametrize("enum_cls,key", [
    (TriState, "TRISTATE"),
    (BiomarkerCategory, "BIOMARKER_CATEGORY"),
    (MedIntent, "MED_INTENT"),
    (PerfScale, "PERF_SCALE"),
    (TreatmentKind, "TREATMENT_KIND"),
    (StageGroup, "STAGE_GROUP"),
])
def test_enums_match_contract(enum_cls, key):
    assert {e.value for e in enum_cls} == _contract_vals(key)


# --- §1 stable identifiers ----------------------------------------------------
def test_element_ids_unique_and_never_positional():
    b = to_bundle(SOURCE)
    ids = _all_element_ids(b)
    assert len(ids) == len(set(ids)), "element_ids must be unique"
    # no id or provenance ref may carry an array index like "observations[3]"
    for eid in ids:
        assert "[" not in eid and "]" not in eid
    for raw_ref, res in b.raw_resources.items():
        assert "[" not in raw_ref
    for prov_ref in _all_prov_refs(b):
        assert prov_ref is None or "[" not in prov_ref


def test_ids_are_reproducible():
    a = to_bundle(SOURCE)
    b = to_bundle(SOURCE)
    assert _all_element_ids(a) == _all_element_ids(b)
    assert a.source_digest == b.source_digest


# --- §2 mechanical facts ------------------------------------------------------
def test_all_required_selectors_present_as_keys():
    b = to_bundle(SOURCE)
    for selector in REQUIRED_SELECTORS:
        assert selector in b.presence, f"missing presence selector: {selector}"


def test_absent_selector_is_explicit_false_not_missing():
    sparse = {"id": "s", "encounter_fhir": {"related_resources": {
        "Condition": [{"resourceType": "Condition", "code": "Breast carcinoma"}]}}}
    b = to_bundle(sparse)
    assert b.presence["biomarkers"].present is False
    assert b.presence["biomarkers"].element_ids == []
    assert b.presence["biomarkers"].count == 0


def test_staleness_is_raw_arithmetic_only():
    b = to_bundle(SOURCE)
    # board_date 2026-07-18, FEV1 dated 2026-07-10 -> 8 days
    fev1 = next(s for s in b.staleness if s.selector == "labs")
    assert fev1.age_days == 8


def test_prior_treatment_kind_is_a_real_enum_value():
    """Regression for the fhir_adapter kind='procedure' bug — must be a TreatmentKind."""
    b = to_bundle(SOURCE)
    for pt in b.prior_treatments:
        assert pt.kind in TreatmentKind
    biopsy = next(pt for pt in b.prior_treatments if "biopsy" in pt.name.lower())
    assert biopsy.kind == TreatmentKind.other  # not the literal string "procedure"


def test_raw_is_sidecar_not_inlined():
    b = to_bundle(SOURCE)
    # provenance carries a pointer, and the side-car resolves it
    for ref in _all_prov_refs_rawref(b):
        if ref is not None:
            assert ref in b.raw_resources


# --- §3 forbidden vocabulary: no clinical-judgment words in Stage 2 output -----
def test_no_gap_vocabulary_in_output():
    b = to_bundle(SOURCE)
    forbidden = ("gap", "missing", "deficiency", "required")
    for selector in b.presence:
        assert not any(w in selector.lower() for w in forbidden)
    for field in PatientCaseBundle.model_fields:
        assert not any(w in field.lower() for w in forbidden)


# --- §7 golden fixture regression ---------------------------------------------
def test_adapter_matches_golden_bundle():
    golden = json.loads((FX / "patient_case_bundle.json").read_text())
    assert to_bundle(SOURCE).model_dump(mode="json") == golden


# --- derivation helpers -------------------------------------------------------
def test_stage_group_derivation():
    assert stage_group("IIIA (T3 N1 M0)") == "III"
    assert stage_group("IVB") == "IV"
    assert stage_group("IA") == "I"
    assert stage_group(None) == "unknown"


def test_value_num_only_when_leading_number():
    assert value_num("70% (high)") == 70.0
    assert value_num("exon 19 deletion, POSITIVE") is None
    assert value_num("negative") is None
    assert value_num(38) == 38.0


def test_slug_rules():
    assert slug("EGFR exon 19 deletion") == "egfr-exon-19-deletion"
    assert slug("  Severe COPD!! ") == "severe-copd"


# --- helpers ------------------------------------------------------------------
def _all_element_ids(b):
    ids = []
    if b.diagnosis:
        ids.append(b.diagnosis.element_id)
    if b.performance_status:
        ids.append(b.performance_status.element_id)
    if b.goals_of_care:
        ids.append(b.goals_of_care.element_id)
    for coll in (b.biomarkers, b.comorbidities, b.medications, b.labs, b.imaging, b.prior_treatments):
        ids.extend(x.element_id for x in coll)
    return ids


def _all_prov(b):
    provs = []
    for attr in ("diagnosis", "performance_status", "goals_of_care"):
        obj = getattr(b, attr)
        if obj:
            provs.append(obj.provenance)
    for coll in (b.biomarkers, b.comorbidities, b.medications, b.labs, b.imaging, b.prior_treatments):
        provs.extend(x.provenance for x in coll)
    return provs


def _all_prov_refs(b):
    return [p.ref for p in _all_prov(b)]


def _all_prov_refs_rawref(b):
    return [p.raw_ref for p in _all_prov(b)]
