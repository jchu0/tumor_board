"""check_operability — feasibility gate for surgical / invasive options.

HARD RULE (README §5): any finding proposing a surgical or invasive procedure MUST
route through this tool before entering the findings feed. Enforcement lives in the
synthesis step (see orchestrator.gate_operability), not in the prompt alone.
"""
from __future__ import annotations

SCHEMA = {
    "name": "check_operability",
    "description": (
        "Assess whether the patient can undergo a proposed surgical/invasive procedure, "
        "given performance status and comorbidities. MUST be called before any surgical "
        "option is surfaced. Returns cleared=true/false with the limiting factors."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "procedure": {"type": "string"},
            "ecog_status": {"type": "integer", "description": "ECOG performance status 0–4."},
            "comorbidities": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["procedure"],
    },
}

# Coarse demo heuristic over canned inputs — good enough to show the gate working.
# Matched as substrings so an *inferred* comorbidity ("uncoded severe COPD noted")
# trips the same rule as a coded one, not just exact strings.
_HIGH_RISK = ("severe copd", "recent mi", "ejection fraction <40", "cirrhosis", "ckd stage 4")


def run(procedure: str, ecog_status: int | None = None, comorbidities: list[str] | None = None) -> dict:
    comorbidities = comorbidities or []
    limiting = [c for c in comorbidities if any(k in c.lower() for k in _HIGH_RISK)]
    poor_ps = ecog_status is not None and ecog_status >= 3
    cleared = not limiting and not poor_ps
    factors = list(limiting)
    if poor_ps:
        factors.append(f"ECOG {ecog_status} (poor performance status)")
    return {
        "procedure": procedure,
        "cleared": cleared,
        "limiting_factors": factors,
        "note": "cleared" if cleared else "operability not confirmed — label option accordingly",
    }
