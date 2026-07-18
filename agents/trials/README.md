# Trials Agent

The **trial-eligibility sub-check** of the tumor-board assistant — a sibling to
the guidelines agent, exposed as **one function**:

```python
from agents.trials import search_trials

findings = search_trials(patient)   # -> list[dict]
```

It screens a patient file against a set of canned ("factice") trials and, per
trial, returns one of three verdicts, always naming the **decisive** criterion:

| Verdict | Meaning |
|---|---|
| ✅ `could_enter` | the patient meets every criterion |
| ❌ `cannot_enter` | a criterion rules them out (which one is reported) |
| 🟡 `possible_with_more_info` | a near-match: everything checkable passes, but some information isn't in the chart yet (what's missing is reported) |

> **Placeholder content.** The trials in `trials/` are minimal, clearly-labeled
> **factice** shells so the pipeline runs and tests pass. The physician replaces
> them with real trial content authored to the same shape (see `AUTHORING.md`).

---

## How it works (hybrid: binary + agent)

Each trial criterion resolves to **PASS / FAIL / UNKNOWN**:

- **Binary criteria** (a `check` block) are pulled straight from the patient
  file and evaluated deterministically — cancer, stage, age, sex, biomarker
  status, therapy class. Fast, reproducible, offline.
- **Non-obvious criteria** (free text, no `check`) are handed to **one Claude
  call** that reads the whole patient file, locates the relevant information,
  and returns PASS/FAIL/UNKNOWN with the evidence it used or a note on what's
  missing. It never guesses — missing info → UNKNOWN.

The **verdict is decided in code, not by the model**, so the decisive criterion
is always explicit:

```
extract patient facts
   │
   ├─ binary criteria  → deterministic PASS/FAIL/UNKNOWN        (eligibility.py)
   └─ free-text criteria → ONE Claude call, reads the chart      (llm_criteria.py)
                    │
                    ▼
   combine per trial → verdict + decisive criterion             (verdict.py)
   any FAIL / met-exclusion → cannot_enter
   else any UNKNOWN         → possible_with_more_info
   else                     → could_enter
```

The two tools are **parallel**: the orchestrator calls `check_guideline_coverage`
and `search_trials` independently. They share the same patient file and reuse
the guidelines feature extractor; nothing else is coupled.

---

## Output shape (per trial)

```jsonc
{
  "domain": "trial_eligibility",
  "source_agent": "trials_agent",
  "trial_id": "NCT-FACTICE-003",
  "title": "…",
  "recruitment_status": "recruiting",
  "verdict": "possible_with_more_info",      // could_enter | cannot_enter | possible_with_more_info
  "decisive_criteria": [                      // what drove the verdict
    { "description": "HER2-positive tumor", "result": "unknown",
      "source": "binary",                     // "binary" | "agent"
      "evidence": "", "missing": "HER2 status not recorded" }
  ],
  "criteria_met": [ "Breast cancer" ],
  "criteria_blocking": [],                     // for cannot_enter
  "criteria_missing_info": [ "HER2-positive tumor" ],  // for possible_with_more_info
  "match_confidence": "high",                  // high = decided by binary checks; moderate = agent-judged
  "confidence_rationale": "…",
  "patient_facing_note": "…",                  // plain language
  "live_question": "To assess eligibility for …, can we obtain: HER2 status?"
}
```

> This is trials-shaped, not identical to the guidelines findings contract. It
> shares `domain` / `source_agent` / `match_confidence` / `confidence_rationale`
> / `patient_facing_note` so the orchestrator can render both uniformly, and
> adds the trial-specific fields (`verdict`, `decisive_criteria`, `trial_id`,
> `live_question`, …). Easy to align further with the orchestrator when needed.

---

## Authoring trials

See **`AUTHORING.md`** — the exact criterion schema (binary `check` fields/ops,
and free-text agent-judged criteria) with copy-paste examples.

---

## Running it

Python 3.11+ (developed on 3.12). API key from `ANTHROPIC_API_KEY`; never
hard-coded.

```bash
pip install -r agents/trials/requirements.txt   # only for the agent path

python -m agents.trials.demo            # uses the agent (LLM) if a key is set
python -m agents.trials.demo --offline  # binary criteria only, no network

python -m pytest agents/trials/tests -q          # with pytest
python agents/trials/tests/run_all.py            # zero-dependency runner
```

Model is set in `config.py` (`MODEL = "claude-sonnet-5"`).

### Offline behaviour

With no `ANTHROPIC_API_KEY` (or on any API error) the free-text criteria return
UNKNOWN — so trials with agent-judged criteria degrade to
`possible_with_more_info` rather than a wrong eligibility call. Binary criteria
work either way. The four factice trials still demonstrate all three verdicts
offline.

---

## Tests (what they prove)

- `could_enter` when all binary criteria pass (`NCT-FACTICE-001`).
- `cannot_enter` names the decisive criterion (`NCT-FACTICE-002`, ER-negative
  required but patient is ER-positive).
- `possible_with_more_info` when a binary fact is missing (`NCT-FACTICE-003`,
  HER2 not recorded).
- Free-text criteria are UNKNOWN offline — never a fabricated pass/fail
  (`NCT-FACTICE-004`).
- Documenting a biomarker flips the verdict (HER2-positive → `could_enter`).
