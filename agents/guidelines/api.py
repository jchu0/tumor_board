"""Public entry point for the guidelines agent.

The whole component is exposed to the outside world as ONE function:

    check_guideline_coverage(patient: dict) -> list[dict]

Internally it is an agent: deterministic triage -> specialist lookups over the
on-disk EBM shelf -> one Claude synthesis call. Externally it is one callable
returning findings in contract (A).
"""

from __future__ import annotations

from .config import MODEL
from .contract import validate_finding
from .specialists import SPECIALISTS
from .synthesis import synthesize
from .triage import select_specialists


def check_guideline_coverage(
    patient: dict,
    *,
    use_llm: bool | None = None,
    model: str = MODEL,
) -> list[dict]:
    """Return guideline-coverage findings for a patient (contract (A)).

    Args:
        patient: a patient file (FHIR-ish; see README for the schema).
        use_llm: run the synthesis Claude call? None auto-detects from
            ANTHROPIC_API_KEY. Pass False for a fully offline, deterministic run.
        model:   the synthesis model (defaults to the MODEL constant).

    The recommendation, recommendation_grade, and evidence_ref in every finding
    come verbatim from the shelf; the model only supplies match_confidence,
    confidence_rationale, and patient_facing_note.
    """
    # 1. Triage: which specialists apply to this patient.
    selected = select_specialists(patient)

    # 2. Each specialist looks up the shelf and returns partial findings.
    partials = []
    for name in selected:
        partials.extend(SPECIALISTS[name].run(patient))

    # 3. One synthesis call adds the two-axis confidence fields + note.
    findings = synthesize(patient, partials, use_llm=use_llm, model=model)

    # 4. Guarantee the boundary contract before handing off.
    for finding in findings:
        validate_finding(finding)
    return findings
