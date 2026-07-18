"""The single synthesis Claude call.

Takes the partial findings the specialists produced and adds the three
judgment-only fields to each:

  - match_confidence      : "high" | "moderate" | "low"
  - confidence_rationale  : WHY, citing specific chart facts (required)
  - patient_facing_note   : plain language, numbers included

CRITICAL: the model NEVER produces or edits recommendation / recommendation_grade
/ evidence_ref. Those are copied verbatim from the card via
`PartialFinding.public_base()`. The model's only job is judgment about whether
the (already-selected) guideline actually fits THIS patient.

Runs fully offline too: with no API key, or on any API error, a deterministic
fallback fills the three fields from the matched chart facts so the pipeline
stays runnable and the tests never need the network.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .config import MODEL
from .contract import MATCH_CONFIDENCE_VALUES
from .specialists.base import PartialFinding

_SYSTEM = (
    "You are the confidence layer of a clinical tumor-board 'guidelines agent'. "
    "Deterministic code has already selected which guideline cards apply to a "
    "patient and copied their recommendation, grade, and evidence reference "
    "verbatim. Your ONLY job is to judge, for each finding, how confident you "
    "are that this guideline was matched to THIS specific patient correctly — "
    "right cancer, stage, biomarker, age, and complete-enough data. You must "
    "NOT invent, restate, or modify any recommendation, grade, or evidence. "
    "You output only match_confidence, confidence_rationale, and "
    "patient_facing_note."
)

_INSTRUCTIONS = """\
For each finding below, decide:

- match_confidence: "high" | "moderate" | "low"
    high     = the chart clearly and completely satisfies what the card needs.
    moderate = it applies, but some relevant detail is assumed or incomplete.
    low      = the match is plausible but key data is missing or ambiguous.

- confidence_rationale: ONE sentence explaining that confidence. It MUST cite
    specific facts from this patient's chart (e.g. the cancer type, stage, age,
    which biomarkers are present/missing). This field is required.

- patient_facing_note: a plain-language sentence a clinician could say to the
    patient. Include any concrete numbers present in the finding (ages,
    counts, day-counts, missing-biomarker lists). Do NOT introduce statistics
    that are not in the data.

Return strict JSON matching the schema: an object with a "findings" array,
one entry per input finding, each carrying the same "id" you were given.
Do not add, drop, or reorder findings.
"""

_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "match_confidence": {
                        "type": "string",
                        "enum": ["high", "moderate", "low"],
                    },
                    "confidence_rationale": {"type": "string"},
                    "patient_facing_note": {"type": "string"},
                },
                "required": [
                    "id",
                    "match_confidence",
                    "confidence_rationale",
                    "patient_facing_note",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}


def _finding_for_prompt(index: int, p: PartialFinding) -> dict[str, Any]:
    return {
        "id": str(index),
        "domain": p.domain,
        "issue": p.issue,
        "recommendation": p.recommendation,
        "recommendation_grade": p.recommendation_grade,
        "status": p.status,
        "applies_when": p.applies_when,
        "matched_chart_facts": p.matched_on,
        "detail": p.detail,
    }


def _build_prompt(patient: dict, partials: list[PartialFinding]) -> str:
    return (
        _INSTRUCTIONS
        + "\n\nPATIENT CHART (JSON):\n"
        + json.dumps(patient, indent=2, default=str)
        + "\n\nFINDINGS (JSON):\n"
        + json.dumps(
            [_finding_for_prompt(i, p) for i, p in enumerate(partials)],
            indent=2,
            default=str,
        )
    )


def _call_claude(
    patient: dict, partials: list[PartialFinding], model: str
) -> dict[str, dict]:
    """Call Claude once and return {id: {match_confidence, ...}}."""
    import anthropic  # imported lazily so the offline path needs no dependency

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the env
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        thinking={"type": "disabled"},
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": _SCHEMA},
        },
        system=_SYSTEM,
        messages=[{"role": "user", "content": _build_prompt(patient, partials)}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)
    return {item["id"]: item for item in data.get("findings", [])}


def _fallback_enrichment(p: PartialFinding) -> tuple[str, str, str]:
    """Deterministic three-field enrichment when the LLM is unavailable."""
    facts: list[str] = []
    for key, value in p.matched_on.items():
        facts.append(f"{key}={value}")
    if p.detail.get("missing"):
        facts.append(f"missing biomarkers={p.detail['missing']}")
    if p.detail.get("age_days") is not None:
        facts.append(f"last documented {p.detail['age_days']} days ago")
    facts_str = "; ".join(facts) if facts else "the matched card's applies-when conditions"

    match_confidence = "moderate"
    rationale = (
        f"Card {p.matched_card_id or '(unknown)'} matched on chart facts: "
        f"{facts_str}. [Automated fallback rationale — LLM synthesis unavailable.]"
    )
    note = (
        f"{p.recommendation} "
        f"[Plain-language note auto-generated — LLM synthesis unavailable.]"
    )
    return match_confidence, rationale, note


def synthesize(
    patient: dict,
    partials: list[PartialFinding],
    *,
    use_llm: bool | None = None,
    model: str = MODEL,
) -> list[dict[str, str]]:
    """Turn partial findings into full contract (A) findings.

    use_llm=None auto-detects: use the model iff ANTHROPIC_API_KEY is set.
    """
    if not partials:
        return []

    if use_llm is None:
        use_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))

    enrichment: dict[str, dict] | None = None
    if use_llm:
        try:
            enrichment = _call_claude(patient, partials, model)
        except Exception as exc:  # noqa: BLE001 — never let synthesis break the pipeline
            logging.getLogger(__name__).warning(
                "guidelines synthesis LLM call failed (%s: %s); using deterministic "
                "offline fallback for confidence/notes.",
                type(exc).__name__,
                exc,
            )
            enrichment = None

    findings: list[dict[str, str]] = []
    for index, partial in enumerate(partials):
        item = (enrichment or {}).get(str(index))
        mc = cr = note = None
        if item:
            mc = item.get("match_confidence")
            cr = (item.get("confidence_rationale") or "").strip()
            note = (item.get("patient_facing_note") or "").strip()

        # Guard every field the model touched; fall back per-field on anything
        # missing or malformed.
        if mc not in MATCH_CONFIDENCE_VALUES or not cr or not note:
            mc, cr, note = _fallback_enrichment(partial)

        finding = partial.public_base()  # grade/rec/ref copied verbatim
        finding["match_confidence"] = mc
        finding["confidence_rationale"] = cr
        finding["patient_facing_note"] = note
        findings.append(finding)

    return findings
