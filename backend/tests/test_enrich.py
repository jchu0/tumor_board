"""Enrichment: the deterministic guardrails must hold without an API key."""
from app.agents.enrich import enrich, verify_grounding
from app.agents.schema import InferenceKind, InferredObservation, SourceRef
from app.case_schema import TumorBoardCase


def _obs(quote: str, kind=InferenceKind.performance_status, line=None) -> InferredObservation:
    return InferredObservation(
        kind=kind, summary="s", confidence=0.6, rationale="r",
        source=SourceRef(location="transcript", line=line, quote=quote),
    )


TRANSCRIPT = [
    {"line": 0, "speaker": "ONCOLOGIST", "text": "Stage IIIA NSCLC, T3 N1 M0."},
    {"line": 1, "speaker": "FAMILY", "text": "She's still doing the school run every morning."},
]


def test_grounded_quote_is_kept_and_line_repaired():
    # Quote is from line 1, but the model claimed line 0 — verifier must fix it.
    obs = _obs("she's still doing the school run", line=0)
    grounded, rejected = verify_grounding([obs], TRANSCRIPT, {})
    assert len(grounded) == 1 and not rejected
    g = grounded[0]
    assert g.source.grounded is True
    assert g.source.line == 1                 # repaired to the true line
    assert g.source.speaker == "FAMILY"       # repaired from the transcript


def test_hallucinated_quote_is_rejected_not_trusted():
    obs = _obs("patient completed a marathon last week")  # not in the source
    grounded, rejected = verify_grounding([obs], TRANSCRIPT, {})
    assert not grounded and len(rejected) == 1
    assert rejected[0].source.grounded is False
    assert "not found" in (rejected[0].source.grounding_note or "")


def test_dropped_negation_is_rejected_as_inversion():
    """Grounding proves quotation, not entailment: quoting 'a candidate for
    resection' out of 'she's not a candidate for resection' must NOT be trusted."""
    transcript = [{"line": 0, "speaker": "SURGEON", "text": "She's not a candidate for resection."}]
    obs = _obs("a candidate for resection", kind=InferenceKind.comorbidity)
    grounded, rejected = verify_grounding([obs], transcript, {})
    assert not grounded and len(rejected) == 1
    assert "negation" in (rejected[0].source.grounding_note or "")


def test_quote_that_keeps_the_negation_is_grounded():
    transcript = [{"line": 0, "speaker": "SURGEON", "text": "She's not a candidate for resection."}]
    obs = _obs("not a candidate for resection", kind=InferenceKind.comorbidity)
    grounded, _ = verify_grounding([obs], transcript, {})
    assert len(grounded) == 1 and grounded[0].source.grounded


def test_free_text_source_is_grounded_too():
    obs = _obs("declined aggressive measures", kind=InferenceKind.goals_of_care)
    grounded, _ = verify_grounding([obs], TRANSCRIPT, {"longitudinal_summary": "Patient declined aggressive measures at a prior visit."})
    assert grounded and grounded[0].source.location == "longitudinal_summary"


def test_enrich_degrades_gracefully_without_api_key(monkeypatch):
    from app.config import get_client

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_client.cache_clear()  # ignore any client cached by another test
    result = enrich(TumorBoardCase(), TRANSCRIPT, {})
    assert result.inferred == [] and result.skipped_reason
