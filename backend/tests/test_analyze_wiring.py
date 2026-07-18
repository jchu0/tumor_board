"""/analyze + /enrich wired to data/cases via case_id. No API key needed:
the orchestrator LLM call is not exercised, but everything up to it is."""
import pytest
from fastapi.testclient import TestClient

from app.cases import list_cases
from app.config import get_client
from app.ingest import ingest
from app.ingest.transcript import parse
from app.main import app
from app.stage2.extract import analysis_inputs_from_case

_CASES = {c.case_id for c in list_cases()}
pytestmark = pytest.mark.skipif(not _CASES, reason="data/cases/ not present")
client = TestClient(app)


def test_ingest_transcript_parses_numbered_turns():
    lines = parse("1. ONCOLOGIST: hello there.\n2. SURGEON: my turn.")
    assert [l["speaker"] for l in lines] == ["ONCOLOGIST", "SURGEON"]


def test_case_inputs_feed_the_pipeline():
    record, free_text = analysis_inputs_from_case("hero_breast_escalation")
    assert record["patient_context"]["patient"]["id"] == "SYN-BR-00147"
    assert record["transcript"].strip()
    # prose notes are handed to enrichment (Stage 2 didn't interpret them)
    assert any(k.startswith("oncology/") for k in free_text)
    case = ingest(record)
    assert any(m.name == "Tamoxifen" for m in case.medications)


def test_analyze_unknown_case_is_404():
    assert client.post("/analyze", json={"case_id": "does_not_exist"}).status_code == 404


def test_enrich_on_a_real_case_runs_end_to_end(monkeypatch):
    """Full case_id -> record -> ingest -> transcript -> enrich path via the API.
    No key, so enrich degrades to a skipped result — but the wiring is exercised."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_client.cache_clear()
    r = client.post("/enrich", json={"case_id": "hero_breast_escalation"})
    assert r.status_code == 200
    assert r.json()["skipped_reason"]
