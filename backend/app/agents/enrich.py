"""Enrichment agent: read the unstructured inputs, emit source-cited inferences.

Reference implementation of the agent template (see agents/__init__.py). The
model authors candidate observations via a forced structured-output tool; a
deterministic verifier then confirms every citation against the source text
before anything is trusted.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from ..case_schema import TumorBoardCase
from ..config import MODEL, get_client
from .schema import Enrichment, InferenceKind, InferredObservation, SourceRef, ToolName

SYSTEM = """You surface clinical nuance that structured data misses in a tumor board.

You are given a NORMALIZED CASE (already extracted from coded fields) plus the raw
TRANSCRIPT and free-text SUMMARY/NOTE. Find things the coded data does NOT already
capture but that a careful clinician would notice in the prose, such as:
- performance status implied by casual speech ("she's still doing the school run"),
- a comorbidity or symptom mentioned but not coded,
- a goals-of-care concern, mismatch, or staleness raised in conversation,
- a concern raised then dropped without resolution.

Hard rules:
- Report ONLY inferences supported by a VERBATIM quote from the provided text.
  Put that exact quote in source.quote. No quote → do not report it.
- Do NOT restate facts already present in the normalized case.
- These are INFERENCES, not confirmed facts. Set an honest confidence.
- If an inference implies a needed check (e.g. an uncoded comorbidity that affects
  whether surgery is safe), set raises_check to the relevant tool name
  (e.g. 'check_operability').
- Call report_inferences exactly once. If you find nothing, return an empty list."""

# The forced structured-output tool == the output template. Hand-authored so the
# contract is explicit and stable across runs.
ENRICHMENT_TOOL = {
    "name": "report_inferences",
    "description": "Report source-cited clinical inferences drawn from the unstructured text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "observations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": [k.value for k in InferenceKind]},
                        "summary": {"type": "string"},
                        "value": {"type": ["string", "null"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "rationale": {"type": "string"},
                        "raises_check": {
                            "type": ["string", "null"],
                            "enum": [t.value for t in ToolName] + [None],
                            "description": "A sub-check tool this must trigger (runs deterministically), or null.",
                        },
                        "source": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string"},
                                "line": {"type": ["integer", "null"]},
                                "speaker": {"type": ["string", "null"]},
                                "quote": {"type": "string", "description": "Verbatim span from the source."},
                            },
                            "required": ["location", "quote"],
                        },
                    },
                    "required": ["kind", "summary", "confidence", "rationale", "source"],
                },
            }
        },
        "required": ["observations"],
    },
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


# Negation tokens that, if adjacent to a matched quote but NOT inside it, mean the
# quote likely inverts the source's meaning (e.g. source "not a candidate for
# resection", quote "a candidate for resection"). Grounding proves quotation, not
# entailment — so we flag and reject these rather than trust them.
_NEG = {
    "not", "no", "never", "without", "denies", "denied", "declines", "declined",
    "cannot", "can't", "won't", "isn't", "aren't", "wasn't", "doesn't", "didn't",
    "non", "unable", "ruled", "ineligible", "unfit", "contraindicated",
}


def _negation_inversion(text_norm: str, quote_norm: str) -> bool:
    """True if a negation sits just outside the matched span but not within the
    quote — the classic meaning-inversion the substring match would miss."""
    idx = text_norm.find(quote_norm)
    if idx < 0:
        return False
    pre = text_norm[:idx].split()[-4:]
    post = text_norm[idx + len(quote_norm):].split()[:2]
    quote_words = set(quote_norm.split())
    if quote_words & _NEG:  # the quote itself carries the negation — fine
        return False
    return any(w.strip(".,;:") in _NEG for w in (*pre, *post))


def verify_grounding(
    observations: list[InferredObservation],
    transcript_lines: list[dict],
    free_text: dict[str, str],
) -> tuple[list[InferredObservation], list[InferredObservation]]:
    """Deterministic guardrail: keep only observations whose quote actually
    appears in the source. Repairs the transcript line/speaker when the quote is
    found there. Returns (grounded, rejected)."""
    line_norms = [(i, ln.get("speaker"), _norm(ln.get("text", ""))) for i, ln in enumerate(transcript_lines)]
    field_norms = {k: _norm(v) for k, v in free_text.items()}

    grounded: list[InferredObservation] = []
    rejected: list[InferredObservation] = []
    for obs in observations:
        q = _norm(obs.source.quote)
        if not q:
            obs.source.grounding_note = "empty quote"
            rejected.append(obs)
            continue
        hit_line = next((i for i, _spk, t in line_norms if q in t), None)
        if hit_line is not None:
            if _negation_inversion(line_norms[hit_line][2], q):
                obs.source.grounding_note = "negation adjacent to quote — possible meaning inversion; not trusted"
                rejected.append(obs)
                continue
            obs.source.grounded = True
            obs.source.line = hit_line                     # repair to the real line
            obs.source.speaker = transcript_lines[hit_line].get("speaker")
            obs.source.location = "transcript"
            grounded.append(obs)
            continue
        hit_field = next((name for name, t in field_norms.items() if q in t), None)
        if hit_field is not None:
            if _negation_inversion(field_norms[hit_field], q):
                obs.source.grounding_note = "negation adjacent to quote — possible meaning inversion; not trusted"
                rejected.append(obs)
                continue
            obs.source.grounded = True
            obs.source.location = hit_field
            grounded.append(obs)
            continue
        obs.source.grounding_note = "quote not found in source"
        rejected.append(obs)
    return grounded, rejected


def enrich(case: TumorBoardCase, transcript_lines: list[dict], free_text: Optional[dict] = None) -> Enrichment:
    """Run the agent. Degrades gracefully: any failure (incl. no API key) yields
    an empty Enrichment with a skipped_reason, so the pipeline still runs."""
    free_text = free_text or {}
    try:
        client = get_client()
    except RuntimeError as e:
        return Enrichment(skipped_reason=str(e).splitlines()[0])

    user = (
        "NORMALIZED CASE (already extracted — do not restate):\n"
        + json.dumps(case.model_dump(), indent=2, default=str)
        + "\n\nTRANSCRIPT (line: speaker: text):\n"
        + "\n".join(f"{ln.get('line', i)}: {ln.get('speaker')}: {ln.get('text','')}" for i, ln in enumerate(transcript_lines))
        + "".join(f"\n\n{k.upper()}:\n{v}" for k, v in free_text.items() if v)
    )
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM,
            tools=[ENRICHMENT_TOOL],
            tool_choice={"type": "tool", "name": "report_inferences"},
            messages=[{"role": "user", "content": user}],
        )
        block = next(b for b in resp.content if b.type == "tool_use")
        drafts = [InferredObservation(**o) for o in block.input.get("observations", [])]
    except Exception as e:  # graceful degradation — never break the pipeline
        return Enrichment(model=MODEL, skipped_reason=f"enrichment error: {type(e).__name__}: {e}")

    grounded, rejected = verify_grounding(drafts, transcript_lines, free_text)
    return Enrichment(inferred=grounded, rejected=rejected, model=MODEL)
