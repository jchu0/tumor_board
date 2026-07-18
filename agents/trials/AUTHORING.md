# Authoring the trials

How to hand-write the canned trial "shells" this agent screens patients against.
You own the medical content; this is the exact structure the code expects.

Each trial is a JSON file in `trials/` (one trial per file, or a list per file).

---

## The shape

```jsonc
{
  "id": "NCT-XXXX",                       // REQUIRED, unique
  "title": "…",                           // shown in output
  "recruitment_status": "recruiting",     // optional info (not currently a gate)
  "inclusion": [ <criterion>, … ],        // criteria the patient must MEET
  "exclusion": [ <criterion>, … ]         // criteria that DISQUALIFY the patient
}
```

Every criterion is one of two kinds:

### 1. Binary criterion (checked directly from the patient file)

Add a `check` block. The tool pulls the fact from the patient file and decides
PASS / FAIL / UNKNOWN deterministically — no model involved.

```jsonc
{ "id": "unique", "description": "human-readable text",
  "check": { "field": "...", "op": "...", "value": ... } }
```

`field` (what to pull from the patient file):

| `field` | Reads | Example |
|---|---|---|
| `cancer` | cancer type(s) | `{ "field": "cancer", "op": "in", "value": ["breast"] }` |
| `stage` | stage(s) | `{ "field": "stage", "op": "in", "value": ["II", "III"] }` |
| `age` | age (integer) | `{ "field": "age", "op": "lte", "value": 70 }` |
| `sex` | gender | `{ "field": "sex", "op": "equals", "value": "female" }` |
| `biomarker` | one biomarker's status (add `"biomarker": "HER2"`) | `{ "field": "biomarker", "biomarker": "HER2", "op": "equals", "value": "positive" }` |
| `biomarkers_present` | which biomarkers were tested | `{ "field": "biomarkers_present", "op": "in", "value": ["EGFR"] }` |
| `planned_therapy_class` | planned therapy class(es) | `{ "field": "planned_therapy_class", "op": "in", "value": ["gonadotoxic"] }` |

`op`:

| `op` | Meaning |
|---|---|
| `in` | patient value intersects `value` (a list) → PASS, else FAIL |
| `not_in` | patient value does NOT intersect `value` → PASS, else FAIL |
| `equals` | case-insensitive string/number equality |
| `gte` / `lte` / `gt` / `lt` | numeric comparison (for `age`) |

**If the patient file doesn't contain the fact, the result is UNKNOWN** — which
becomes a "could enter if we get X" reason, never a wrong pass/fail.

### 2. Agent-judged criterion (non-obvious — free text)

Omit `check`. Just give a `description`. One Claude call reads the whole patient
file, finds where the relevant information lives, and returns PASS / FAIL /
UNKNOWN with the evidence it used or a note on what's missing.

```jsonc
{ "id": "unique", "description": "Adequate bone marrow and organ function documented on recent labs" }
```

Use this for anything not a clean field lookup: organ function, prior lines of
therapy, performance status described in prose, "no uncontrolled comorbidity",
etc. Offline (no API key), these come back UNKNOWN — the tool degrades to a
"need more info" verdict rather than guessing.

---

## How the verdict is decided (code, not the model)

Each criterion resolves to PASS / FAIL / UNKNOWN. For an **exclusion**
criterion, "the patient meets the excluding condition" counts as a
disqualifier. Then:

| Condition | Verdict |
|---|---|
| any inclusion FAILs, or any exclusion is MET | ❌ `cannot_enter` (names the decisive criterion) |
| otherwise, any criterion is UNKNOWN | 🟡 `possible_with_more_info` (lists what's missing) |
| everything PASSes / exclusions confirmed absent | ✅ `could_enter` |

`match_confidence` is `high` when the decisive criteria were all binary chart
pulls, `moderate` when an agent-judged (free-text) criterion was decisive.

---

## Example (mixes both kinds)

```jsonc
{
  "id": "NCT-FACTICE-010",
  "title": "Example study",
  "recruitment_status": "recruiting",
  "inclusion": [
    { "id": "cancer",  "description": "Breast cancer",
      "check": { "field": "cancer", "op": "in", "value": ["breast"] } },
    { "id": "her2",    "description": "HER2 positive",
      "check": { "field": "biomarker", "biomarker": "HER2", "op": "equals", "value": "positive" } },
    { "id": "organ",   "description": "Adequate organ function on recent labs" }   // agent-judged
  ],
  "exclusion": [
    { "id": "brain",   "description": "Untreated brain metastases" }               // agent-judged
  ]
}
```

Against a patient with breast cancer + HER2 positive + labs on file + no brain
mets → **could enter**. With HER2 not recorded → **could enter if we get HER2
status**. HER2 recorded negative → **cannot enter (HER2 must be positive)**.

---

## What the patient file must contain (so binary checks resolve)

Same file both tools read (see the guidelines `shelf/AUTHORING.md` §5). Relevant
resources:

```jsonc
{
  "patient_context": { "patient": { "gender": "female", "age": 34 } },
  "encounter_fhir": { "resources_by_type": {
    "Condition":         [ { "cancer": "breast", "stage": "II" } ],
    "Observation":       [ { "biomarker": "HER2", "valueString": "positive" } ],  // status → biomarker checks
    "MedicationRequest": [ { "therapy_class": "gonadotoxic" } ]
  }}
}
```

- A `biomarker` check reads `Observation[].biomarker` + its `valueString`
  (or `value` / `interpretation`). No value recorded → UNKNOWN.
- Agent-judged criteria can use *anything* in the file — put the relevant prose
  (labs, comorbidities, prior treatments, notes) anywhere sensible and the agent
  will find it.
