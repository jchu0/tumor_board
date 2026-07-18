"""Public entry point for the trials agent.

One callable, parallel to the guidelines agent:

    search_trials(patient: dict) -> list[dict]

Pipeline: extract patient facts -> for each canned trial, evaluate binary
criteria deterministically and collect free-text criteria -> ONE Claude call
judges all free-text criteria against the chart -> combine per trial into a
verdict (could_enter / cannot_enter / possible_with_more_info) naming the
decisive criterion.
"""

from __future__ import annotations

from .config import MODEL
from .eligibility import UNKNOWN, evaluate_check
from .extract import extract_patient_facts
from .llm_criteria import evaluate_freetext_criteria
from .loader import load_trials
from .verdict import _criterion_view, build_finding, sort_key


def _iter_criteria(trial: dict):
    for kind in ("inclusion", "exclusion"):
        for crit in trial.get(kind, []):
            yield kind, crit


def search_trials(
    patient: dict,
    *,
    use_llm: bool | None = None,
    model: str = MODEL,
) -> list[dict]:
    """Screen a patient against the canned trials and return per-trial findings."""
    facts = extract_patient_facts(patient)
    trials = load_trials()

    # 1. Deterministic pass + gather free-text criteria (batched into one call).
    deterministic: dict[str, str] = {}          # criterion id -> result
    freetext_inputs: list[dict] = []            # for the LLM call
    for trial in trials:
        for kind, crit in _iter_criteria(trial):
            cid = crit.get("id") or f"{trial.get('id','?')}:{kind}:{crit.get('description','')[:24]}"
            crit["id"] = cid  # ensure a stable id for matching results back
            if crit.get("check"):
                deterministic[cid] = evaluate_check(crit["check"], facts)
            else:
                freetext_inputs.append(
                    {"id": cid, "description": crit.get("description", ""), "kind": kind}
                )

    # 2. One agent call for every non-obvious criterion across all trials.
    llm_results = evaluate_freetext_criteria(
        patient, freetext_inputs, use_llm=use_llm, model=model
    )

    # 3. Combine into a verdict per trial.
    findings: list[dict] = []
    for trial in trials:
        evaluated: list[dict] = []
        for kind, crit in _iter_criteria(trial):
            cid = crit["id"]
            if crit.get("check"):
                evaluated.append(
                    _criterion_view(crit, kind, deterministic.get(cid, UNKNOWN), "", "")
                )
            else:
                r = llm_results.get(cid, {"result": UNKNOWN, "evidence": "", "missing": ""})
                evaluated.append(
                    _criterion_view(crit, kind, r["result"], r["evidence"], r["missing"])
                )
        findings.append(build_finding(trial, evaluated))

    findings.sort(key=sort_key)
    return findings
