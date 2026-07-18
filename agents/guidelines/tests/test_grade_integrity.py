"""recommendation_grade (and recommendation, evidence_ref) in the output are
byte-for-byte identical to the shelf card they came from — proving the model
never rewrote the evidence, even on the LLM synthesis path."""

from __future__ import annotations

import json

from agents.guidelines import synthesis
from agents.guidelines.api import check_guideline_coverage
from agents.guidelines.config import PLACEHOLDER_PATIENT_PATH
from agents.guidelines.loader import load_shelf


def _patient() -> dict:
    with open(PLACEHOLDER_PATIENT_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _card_triples() -> set[tuple[str, str, str]]:
    """(recommendation, recommendation_grade, evidence_ref) for every card."""
    triples = set()
    for cards in load_shelf().values():
        for card in cards:
            triples.add(
                (card["recommendation"], card["recommendation_grade"], card["evidence_ref"])
            )
    return triples


def test_grade_recommendation_evidence_are_verbatim_offline():
    triples = _card_triples()
    findings = check_guideline_coverage(_patient(), use_llm=False)
    assert findings
    for f in findings:
        assert (
            f["recommendation"],
            f["recommendation_grade"],
            f["evidence_ref"],
        ) in triples


def test_model_cannot_rewrite_the_grade_on_the_llm_path():
    """Simulate the LLM path with a stub that tries to smuggle a bogus grade.

    The merge only ever reads the model's three judgment fields, so a bogus
    'recommendation_grade' from the model must be ignored and the card's grade
    preserved. We also confirm the model's match_confidence DID come through, so
    the stub is genuinely exercising the LLM path.
    """
    triples = _card_triples()

    def fake_call(patient, partials, model):
        return {
            str(i): {
                "id": str(i),
                "match_confidence": "high",
                "confidence_rationale": "Chart shows cancer=breast, stage=II, age=34.",
                "patient_facing_note": "Plain-language note.",
                # Adversarial: try to overwrite the evidence. Must be ignored.
                "recommendation_grade": "IV / D (bogus)",
                "recommendation": "MODEL-HALLUCINATED RECOMMENDATION",
            }
            for i, _ in enumerate(partials)
        }

    original = synthesis._call_claude
    synthesis._call_claude = fake_call
    try:
        findings = check_guideline_coverage(_patient(), use_llm=True)
    finally:
        synthesis._call_claude = original

    assert findings
    for f in findings:
        # Judgment field came from the model...
        assert f["match_confidence"] == "high"
        # ...but the evidence triple is still the card's, untouched.
        assert (
            f["recommendation"],
            f["recommendation_grade"],
            f["evidence_ref"],
        ) in triples
        assert "bogus" not in f["recommendation_grade"]
        assert f["recommendation"] != "MODEL-HALLUCINATED RECOMMENDATION"
