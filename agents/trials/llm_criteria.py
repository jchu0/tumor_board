"""The agent step: judge NON-obvious criteria against the patient file.

Binary criteria are handled deterministically (eligibility.py). Everything else
— free-text criteria with no `check` — is sent here. One Claude call reads the
whole patient file, locates the relevant information, and returns PASS / FAIL /
UNKNOWN per criterion with the chart evidence it used (or what is missing). It
does NOT decide trial verdicts; the verdict combiner does that in code.

For an EXCLUSION criterion, "pass" means the patient MEETS the excluding
condition (i.e. would be disqualified). This is stated explicitly in the prompt.

Fully offline-safe: with no API key or on any error, every free-text criterion
comes back UNKNOWN (we never fabricate a pass/fail), which surfaces as a
"need more information" reason rather than a wrong eligibility call.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .config import MODEL
from .eligibility import FAIL, PASS, UNKNOWN

_RESULTS = {PASS, FAIL, UNKNOWN}

_SYSTEM = (
    "You screen a patient against clinical-trial eligibility criteria. For each "
    "criterion you are given, search the patient chart and decide whether the "
    "chart shows it is satisfied. You must not guess: if the chart does not "
    "contain the information, answer 'unknown'. Cite the specific chart facts "
    "you used, or say exactly what is missing."
)

_INSTRUCTIONS = """\
For each criterion below decide a `result`:

- For an INCLUSION criterion:
    "pass"    = the chart shows the patient satisfies it.
    "fail"    = the chart shows the patient does NOT satisfy it.
    "unknown" = the chart does not contain the information needed to decide.

- For an EXCLUSION criterion (kind = "exclusion"):
    "pass"    = the chart shows the patient MEETS the excluding condition
                (this would disqualify them).
    "fail"    = the chart shows the excluding condition is ABSENT.
    "unknown" = the chart does not say either way.

Also return:
- `evidence`: the specific chart fact(s) you based the decision on (empty if none).
- `missing` : if unknown, what information is needed and where it would normally
              be found (empty otherwise).

Return strict JSON with a "criteria" array, one entry per input criterion,
carrying the same "id". Do not add, drop, or reorder entries. Never guess.
"""

_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "result": {"type": "string", "enum": ["pass", "fail", "unknown"]},
                    "evidence": {"type": "string"},
                    "missing": {"type": "string"},
                },
                "required": ["id", "result", "evidence", "missing"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["criteria"],
    "additionalProperties": False,
}


def evaluate_freetext_criteria(
    patient: dict,
    criteria: list[dict],
    *,
    use_llm: bool | None = None,
    model: str = MODEL,
) -> dict[str, dict]:
    """Return {criterion_id: {result, evidence, missing}} for free-text criteria.

    `criteria` items: {"id", "description", "kind": "inclusion"|"exclusion"}.
    """
    if not criteria:
        return {}

    if use_llm is None:
        use_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))

    if use_llm:
        try:
            return _call_claude(patient, criteria, model)
        except Exception as exc:  # noqa: BLE001 — never let this break eligibility
            logging.getLogger(__name__).warning(
                "trials free-text criteria LLM call failed (%s: %s); all free-text "
                "criteria fall back to UNKNOWN (offline).",
                type(exc).__name__,
                exc,
            )

    # Offline / failure fallback: cannot read the chart, so everything is unknown.
    return {
        c["id"]: {
            "result": UNKNOWN,
            "evidence": "",
            "missing": f"{c['description']} — chart not read (offline).",
        }
        for c in criteria
    }


def _call_claude(patient: dict, criteria: list[dict], model: str) -> dict[str, dict]:
    import anthropic  # lazy import so the offline path needs no dependency

    prompt = (
        _INSTRUCTIONS
        + "\n\nPATIENT CHART (JSON):\n"
        + json.dumps(patient, indent=2, default=str)
        + "\n\nCRITERIA (JSON):\n"
        + json.dumps(criteria, indent=2, default=str)
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        thinking={"type": "disabled"},
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": _SCHEMA},
        },
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)

    out: dict[str, dict] = {}
    for item in data.get("criteria", []):
        result = item.get("result")
        if result not in _RESULTS:
            result = UNKNOWN
        out[item["id"]] = {
            "result": result,
            "evidence": item.get("evidence", "") or "",
            "missing": item.get("missing", "") or "",
        }
    return out
