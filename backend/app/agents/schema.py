"""The enrichment output contract — the *template* every inference conforms to.

Consistency comes from this schema being enforced via structured output: the
model must fill exactly these fields. The one non-negotiable field is
`source.quote` — a verbatim span from the input — because an inference we can't
point back at the source is not one we surface.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class InferenceKind(str, Enum):
    performance_status = "performance_status"   # ECOG/Karnofsky implied by speech
    comorbidity = "comorbidity"                 # condition mentioned but not coded
    goals_of_care = "goals_of_care"             # GOC concern / mismatch raised in conversation
    symptom = "symptom"                         # functionally relevant symptom
    disagreement = "disagreement"               # raised-then-dropped concern
    medication = "medication"                   # med mentioned but not in the chart
    other = "other"


class ToolName(str, Enum):
    """The sub-check tools raises_check may trigger. MUST stay in sync with the
    tool registry (app.tools._REGISTRY) — a drift test enforces this, so a typo'd
    tool name fails loudly at test time instead of silently never firing."""
    check_drug_interactions = "check_drug_interactions"
    search_trials = "search_trials"
    check_guideline_coverage = "check_guideline_coverage"
    flag_stale_data = "flag_stale_data"
    check_operability = "check_operability"
    check_practice_pattern = "check_practice_pattern"


class SourceRef(BaseModel):
    """The pointer to the data. `quote` is verbatim and REQUIRED; `grounded` is
    set by the deterministic verifier, never by the model."""
    location: str = Field(..., description="Where it came from, e.g. 'transcript', 'longitudinal_summary', 'note'.")
    line: Optional[int] = Field(None, description="Transcript line index if applicable (verifier repairs it).")
    speaker: Optional[str] = None
    quote: str = Field(..., description="Verbatim span from the source that supports the inference.")
    grounded: bool = Field(False, description="Set by verify_grounding: does `quote` actually appear in the source?")
    grounding_note: Optional[str] = None


class InferredObservation(BaseModel):
    kind: InferenceKind
    summary: str = Field(..., description="What was inferred, in one line.")
    value: Optional[str] = Field(None, description="Structured value if any, e.g. 'ECOG 2 (implied)'.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="The agent's confidence in the inference.")
    rationale: str = Field(..., description="Why the quote implies this — the reasoning link.")
    raises_check: Optional[ToolName] = Field(None, description="A sub-check tool this observation must trigger deterministically.")
    source: SourceRef
    inferred: Literal[True] = True  # marks the channel; always true here


class Enrichment(BaseModel):
    """Distinct section of the response — never merged into the grounded case.
    Everything in `inferred` is verified (its quote was found in the source);
    `rejected` holds items whose citation didn't check out, kept for transparency."""
    inferred: list[InferredObservation] = Field(default_factory=list)
    rejected: list[InferredObservation] = Field(default_factory=list)
    model: Optional[str] = None
    skipped_reason: Optional[str] = Field(None, description="Set when the agent didn't run, e.g. 'no ANTHROPIC_API_KEY'.")
