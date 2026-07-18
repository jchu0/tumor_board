"""The hard rule is enforced in code, so it must be testable without the API."""
from app.orchestrator import gate_operability
from app.schema import Finding, OperabilityStatus


def _finding(**over) -> Finding:
    base = dict(
        issue="x",
        evidence_ref="guidelines.json",
        recommendation="do the thing",
        match_confidence=0.5,
        patient_facing_note="note",
        live_question="q?",
        source_agent="check_guideline_coverage",
    )
    base.update(over)
    return Finding(**base)


def test_surgical_finding_without_operability_is_relabeled():
    f = _finding(issue="Lobectomy not offered", recommendation="Offer lobectomy")
    (gated,) = gate_operability([f])
    assert gated.operability_status == OperabilityStatus.not_confirmed
    assert "operability not yet confirmed" in gated.recommendation


def test_cleared_finding_stands_only_with_a_cleared_result():
    f = _finding(
        issue="Consider resection",
        recommendation="Proceed to surgery",
        operability_status=OperabilityStatus.cleared,
    )
    (gated,) = gate_operability([f], operability_results=[{"cleared": True}])
    assert gated.operability_status == OperabilityStatus.cleared
    assert "not yet confirmed" not in gated.recommendation


def test_declared_cleared_without_any_result_is_downgraded():
    """A model claiming 'cleared' with no backing operability result is not trusted."""
    f = _finding(issue="Consider resection", recommendation="Proceed to surgery",
                 operability_status=OperabilityStatus.cleared)
    (gated,) = gate_operability([f], operability_results=[])
    assert gated.operability_status == OperabilityStatus.not_confirmed


def test_blocking_result_overrides_declared_cleared():
    f = _finding(issue="Consider resection", recommendation="Proceed to surgery",
                 operability_status=OperabilityStatus.cleared)
    (gated,) = gate_operability([f], operability_results=[{"cleared": False}])
    assert gated.operability_status == OperabilityStatus.not_confirmed
    assert "operability not yet confirmed" in gated.recommendation


def test_non_surgical_finding_is_untouched():
    f = _finding(issue="EGFR trial not discussed", recommendation="Consider trial NCT04030000")
    (gated,) = gate_operability([f])
    assert gated.operability_status == OperabilityStatus.not_applicable


def test_finding_that_only_mentions_surgery_is_not_gated():
    """Regression: a documentation finding that mentions surgery/resection but
    does NOT propose a procedure must not be relabeled (the earlier false positive)."""
    f = _finding(
        issue="Radiotherapy chosen over surgery with no rationale stated",
        recommendation="Document explicit rationale for radiotherapy over resection",
    )
    (gated,) = gate_operability([f])
    assert gated.operability_status == OperabilityStatus.not_applicable
    assert "operability not yet confirmed" not in gated.recommendation


def test_declared_proposes_procedure_is_gated_even_without_keywords():
    """Primary path: the model's declared intent gates it regardless of wording."""
    f = _finding(issue="Definitive local therapy", recommendation="Take patient to the OR", proposes_procedure=True)
    (gated,) = gate_operability([f])
    assert gated.operability_status == OperabilityStatus.not_confirmed
