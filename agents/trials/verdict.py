"""Combine per-criterion results into a trial verdict.

This is where the three outcomes are decided — deterministically, in code, so
the decisive criterion is always explicit and reproducible:

  - any FAIL (inclusion not met) or any TRIGGERED exclusion  -> "cannot_enter"
  - else any UNKNOWN                                          -> "possible_with_more_info"
  - else                                                      -> "could_enter"
"""

from __future__ import annotations

from typing import Any

from .eligibility import FAIL, PASS, UNKNOWN

COULD_ENTER = "could_enter"
CANNOT_ENTER = "cannot_enter"
POSSIBLE = "possible_with_more_info"

_VERDICT_ORDER = {COULD_ENTER: 0, POSSIBLE: 1, CANNOT_ENTER: 2}


def _criterion_view(crit: dict, kind: str, result: str, evidence: str, missing: str) -> dict:
    return {
        "id": crit.get("id", ""),
        "kind": kind,
        "description": crit.get("description", ""),
        "result": result,
        "source": "binary" if crit.get("check") else "agent",
        "evidence": evidence,
        "missing": missing,
    }


def build_finding(trial: dict, evaluated: list[dict]) -> dict:
    """Turn a trial + its evaluated criteria into one output finding.

    `evaluated` items are the dicts produced by _criterion_view.
    """
    title = trial.get("title", trial.get("id", "trial"))

    blocking: list[dict] = []   # decisive disqualifiers
    missing: list[dict] = []    # near-match reasons
    met: list[dict] = []

    for c in evaluated:
        if c["kind"] == "inclusion":
            if c["result"] == FAIL:
                blocking.append(c)
            elif c["result"] == UNKNOWN:
                missing.append(c)
            else:
                met.append(c)
        else:  # exclusion
            if c["result"] == PASS:  # meets excluding condition -> disqualified
                blocking.append(c)
            elif c["result"] == UNKNOWN:
                missing.append(c)
            else:
                met.append(c)

    if blocking:
        verdict = CANNOT_ENTER
        decisive = blocking
    elif missing:
        verdict = POSSIBLE
        decisive = missing
    else:
        verdict = COULD_ENTER
        decisive = met

    # Confidence: high when the decisive criteria were all binary chart pulls;
    # moderate when an agent-read (free-text) criterion was decisive.
    used_agent = any(c["source"] == "agent" for c in decisive) if decisive else False
    match_confidence = "moderate" if used_agent else "high"

    note, live_question = _narrate(verdict, title, blocking, missing, met)
    rationale = _rationale(verdict, blocking, missing, met, used_agent)

    return {
        "domain": "trial_eligibility",
        "source_agent": "trials_agent",
        "trial_id": trial.get("id", ""),
        "title": title,
        "recruitment_status": trial.get("recruitment_status", "unknown"),
        "verdict": verdict,
        "decisive_criteria": [
            {"description": c["description"], "result": c["result"],
             "source": c["source"], "evidence": c["evidence"], "missing": c["missing"]}
            for c in decisive
        ],
        "criteria_met": [c["description"] for c in met],
        "criteria_blocking": [c["description"] for c in blocking],
        "criteria_missing_info": [c["description"] for c in missing],
        "match_confidence": match_confidence,
        "confidence_rationale": rationale,
        "patient_facing_note": note,
        "live_question": live_question,
    }


def _narrate(verdict, title, blocking, missing, met) -> tuple[str, str]:
    if verdict == COULD_ENTER:
        met_str = "; ".join(c["description"] for c in met) or "all criteria"
        return (
            f"You appear eligible for {title} (meets: {met_str}).",
            f"Has enrollment in {title} been considered?",
        )
    if verdict == CANNOT_ENTER:
        first = blocking[0]
        reason = (
            f"does not meet: {first['description']}"
            if first["kind"] == "inclusion"
            else f"excluded by: {first['description']}"
        )
        return (
            f"You are not eligible for {title} — {reason}.",
            "",
        )
    # possible_with_more_info
    need = "; ".join(c["description"] for c in missing)
    return (
        f"You may be eligible for {title}; we still need to confirm: {need}.",
        f"To assess eligibility for {title}, can we obtain: {need}?",
    )


def _rationale(verdict, blocking, missing, met, used_agent) -> str:
    how = "with chart-reading by the agent" if used_agent else "deterministically from the chart"
    if verdict == CANNOT_ENTER:
        c = blocking[0]
        return (
            f"Blocked by a {c['kind']} criterion — {c['description']} "
            f"(evidence: {c['evidence'] or 'from patient fields'}). Determined {how}."
        )
    if verdict == POSSIBLE:
        need = "; ".join(c["description"] for c in missing)
        return (
            f"All checkable criteria pass; the patient file lacks: {need}. Determined {how}."
        )
    met_str = "; ".join(c["description"] for c in met) or "the trial criteria"
    return f"All criteria satisfied ({met_str}). Determined {how}."


def sort_key(finding: dict) -> tuple[int, str]:
    return (_VERDICT_ORDER.get(finding["verdict"], 9), finding.get("trial_id", ""))
