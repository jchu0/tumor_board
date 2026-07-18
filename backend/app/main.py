"""FastAPI entrypoint.

Run: uvicorn app.main:app --reload  (from the backend/ directory)
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import HTTPException

from .agents.enrich import enrich
from .agents.schema import Enrichment
from .cases import CaseDetail, CaseSummary, get_case, list_cases
from .config import FRONTEND_ORIGIN
from .ingest import ingest
from .ingest.transcript import parse as parse_transcript
from .orchestrator import analyze
from .schema import AnalysisResult, AnalyzeRequest
from .stage2.extract import analysis_inputs_from_case
from .tools._data import load


def _free_text(record: dict) -> dict:
    """Unstructured fields the enrichment agent reads (besides the transcript)."""
    pctx = record.get("patient_context", {})
    return {
        "longitudinal_summary": pctx.get("longitudinal_summary") or "",
        "note": record.get("note") or "",
    }

app = FastAPI(title="Tumor Board Gap-Detection Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_CASE = "case_nsclc_egfr.json"


def _record(req: AnalyzeRequest | None = None) -> dict:
    if req and req.record:
        return req.record
    return load(DEFAULT_CASE)


def _inputs(req: AnalyzeRequest | None = None) -> tuple[dict, dict]:
    """(fhir_record, free_text) for the pipeline. A case_id structures a
    data/cases folder; otherwise fall back to a record or the bundled case."""
    if req and req.case_id:
        try:
            return analysis_inputs_from_case(req.case_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown case: {req.case_id}")
    record = _record(req)
    return record, _free_text(record)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/case")
def sample_case() -> dict:
    """Raw record + normalized case + parsed transcript, so the UI can render
    the structured view (and its completeness gaps) without an LLM run."""
    record = load(DEFAULT_CASE)
    case = ingest(record)
    return {
        "record": record,
        "case": case.model_dump(),
        "completeness": [m.model_dump() for m in case.completeness()],
        "transcript": parse_transcript(record.get("transcript", [])),
    }


@app.post("/enrich", response_model=Enrichment)
def run_enrichment(req: AnalyzeRequest) -> Enrichment:
    """Run only the enrichment agent — for isolated testing of inferred output."""
    record, free_text = _inputs(req)
    case = ingest(record)
    transcript = parse_transcript(record.get("transcript", []))
    return enrich(case, transcript, free_text)


@app.post("/analyze", response_model=AnalysisResult)
def run_analysis(req: AnalyzeRequest) -> AnalysisResult:
    record, free_text = _inputs(req)
    case = ingest(record)
    transcript = parse_transcript(record.get("transcript", []))
    # Enrichment runs first so its source-cited leads feed the orchestrator;
    # it degrades to empty if there's no API key, so analysis still runs.
    enrichment = enrich(case, transcript, free_text)
    return analyze(case, transcript, enrichment)


@app.get("/cases", response_model=list[CaseSummary])
def all_cases() -> list[CaseSummary]:
    """Patient list. Identity only — the benchmark ground truth in case_meta.json
    (planted_gaps and friends) is stripped in the repository, never served."""
    return list_cases()


@app.get("/cases/{case_id}", response_model=CaseDetail)
def one_case(case_id: str) -> CaseDetail:
    """One patient's folders and documents, plus the board transcript. Folders are
    whatever exists on disk — cases carry different specialties."""
    case = get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"unknown case: {case_id}")
    return case
