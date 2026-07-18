"""Stage 2 extraction from the on-disk case format (data/cases/<case>/).

Reads the real cases via the repository (app.cases). Skips if the data isn't
present on disk, so the suite stays green without the (uncommitted) dataset.
"""
import pytest

from app.cases import get_case, list_cases
from app.stage2 import bundle_from_case, load_case_bundle
from app.stage2.enums import SpeakerRole

_CASES = {c.case_id for c in list_cases()}
pytestmark = pytest.mark.skipif(not _CASES, reason="data/cases/ not present")


def _bundle(case_id):
    return load_case_bundle(case_id)


def test_every_case_structures_without_error():
    for cid in _CASES:
        b, tb = load_case_bundle(cid)
        assert b.case_id == cid and tb.transcript_id == cid
        assert b.source_digest.startswith("sha256:")


def test_hero_case_deterministic_extraction():
    b, tb = _bundle("hero_breast_escalation")
    assert b.patient.id == "SYN-BR-00147" and b.patient.sex == "female"
    assert b.performance_status and b.performance_status.value == "1"   # latest ECOG row
    names = {bm.name.upper() for bm in b.biomarkers}
    assert {"ER", "PR", "HER2"} <= names
    assert any(m.name == "Tamoxifen" for m in b.medications)
    assert b.goals_of_care and b.goals_of_care.summary
    assert any(t.speaker_role == SpeakerRole.surgeon for t in tb.turns)


def test_negative_control_egfr_is_negative_not_a_false_positive():
    """variant_4 is the negative control: EGFR is NEGATIVE. Regression against the
    'no mutation detected' -> positive inversion."""
    b, _ = _bundle("variant_4_lung_control")
    egfr = next((bm for bm in b.biomarkers if bm.gene == "EGFR"), None)
    assert egfr is not None and egfr.status.value == "negative"
    # the kidney lab eGFR must NOT have been misfiled as the EGFR gene
    assert not any(bm.name.lower() == "egfr" and bm is not egfr for bm in b.biomarkers)
    assert b.diagnosis and b.diagnosis.staging and b.diagnosis.staging.overall_stage


def test_egfr_kidney_lab_is_a_lab_not_a_biomarker():
    b, _ = _bundle("variant_2_stale_interaction")
    assert any(l.name.lower() == "egfr" for l in b.labs)
    assert not any(bm.name.lower() == "egfr" for bm in b.biomarkers)


def test_numbered_transcript_parses_with_roles():
    _, tb = _bundle("variant_4_lung_control")
    assert len(tb.turns) >= 8
    assert tb.turns[0].line_id == "L001" and tb.turns[0].ordinal == 1
    speakers = {t.speaker for t in tb.turns}
    assert "ONCOLOGIST" in speakers
    # PNEUMOLOGIST is a real speaker but not in the closed SpeakerRole enum -> other
    assert any(t.speaker == "PNEUMOLOGIST" and t.speaker_role == SpeakerRole.other for t in tb.turns)


def test_extraction_is_deterministic():
    a, _ = _bundle("hero_breast_escalation")
    b, _ = _bundle("hero_breast_escalation")
    assert a.source_digest == b.source_digest
    assert [x.element_id for x in a.medications] == [x.element_id for x in b.medications]


def test_isolation_two_cases_do_not_bleed():
    hero, _ = _bundle("hero_breast_escalation")
    lung, _ = _bundle("variant_4_lung_control")
    assert hero.patient.id != lung.patient.id
    assert not any(m.name == "Tiotropium inhaler" for m in hero.medications)  # lung-only med
