"""raises_check must run deterministically and gate the findings (feedback #1),
and its vocabulary must not drift from the tool registry (feedback #3)."""
from app.agents.schema import Enrichment, InferenceKind, InferredObservation, SourceRef, ToolName
from app.case_schema import Comorbidity, PerformanceStatus, TumorBoardCase
from app.orchestrator import gate_operability, run_triggered_checks
from app.schema import Finding, OperabilityStatus
from app.tools import _REGISTRY


def test_toolname_enum_matches_registry():
    """A typo'd tool name would silently never fire — this catches drift."""
    assert {t.value for t in ToolName} == set(_REGISTRY)


def _inferred_copd():
    return InferredObservation(
        kind=InferenceKind.comorbidity,
        summary="uncoded severe COPD mentioned — surgery may be unsafe",
        confidence=0.6,
        rationale="r",
        raises_check=ToolName.check_operability,
        source=SourceRef(location="transcript", quote="q", grounded=True),
    )


def test_raises_check_runs_the_tool_deterministically():
    case = TumorBoardCase(performance_status=PerformanceStatus(scale="ECOG", value="1"))
    enr = Enrichment(inferred=[_inferred_copd()])
    triggered = run_triggered_checks(case, enr)
    assert len(triggered) == 1
    t = triggered[0]
    assert t["tool"] == "check_operability"
    # The inferred COPD was folded into the operability inputs and blocks clearance.
    assert t["result"]["cleared"] is False
    assert any("copd" in f.lower() for f in t["result"]["limiting_factors"])


def test_triggered_block_gates_a_surgical_finding_end_to_end():
    """The inferred comorbidity's check result must force a surgical finding to not_confirmed."""
    case = TumorBoardCase(performance_status=PerformanceStatus(scale="ECOG", value="1"))
    enr = Enrichment(inferred=[_inferred_copd()])
    op_results = [t["result"] for t in run_triggered_checks(case, enr)]

    f = Finding(issue="Lobectomy", recommendation="Offer lobectomy", match_confidence=0.7,
                patient_facing_note="n", live_question="q", evidence_ref="e",
                source_agent="check_guideline_coverage", proposes_procedure=True,
                operability_status=OperabilityStatus.cleared)  # model wrongly says cleared
    (gated,) = gate_operability([f], op_results)
    assert gated.operability_status == OperabilityStatus.not_confirmed


def test_no_raises_check_triggers_nothing():
    obs = InferredObservation(kind=InferenceKind.symptom, summary="s", confidence=0.5, rationale="r",
                              source=SourceRef(location="transcript", quote="q"))
    assert run_triggered_checks(TumorBoardCase(), Enrichment(inferred=[obs])) == []
