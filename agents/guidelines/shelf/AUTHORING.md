# Authoring the guidelines shelf

How to hand-write the EBM "shelf" cards this agent reads. You (the physician)
own the medical content; this file is the exact structure the code expects so
your factice cards actually fire.

> This is contract (B). The full README has the matching finding-output shape
> (contract A). Nothing here is secret; edit the JSON files by hand.

---

## 1. File rules

- One JSON file per specialist under `shelf/`.
- A file contains **either a single card object or a list of cards** (use a list
  — you'll usually want several cards per specialist).
- Cards are grouped by their `specialist` field, **not** the filename. The field
  must be exact. Keep filename = specialist value for sanity.

| File | `specialist` value | Kind |
|---|---|---|
| `guideline_coverage.json` | `guideline_coverage` | pure lookup |
| `fertility_preservation.json` | `fertility_preservation` | pure lookup |
| `germline_testing.json` | `germline_testing` | pure lookup |
| `biomarker_completeness.json` | `biomarker_completeness` | completeness |
| `goals_of_care.json` | `goals_of_care` | staleness |

---

## 2. The matching vocabulary (this is "what fits")

The code flattens each patient into exactly these six features. **A card's
`applies_when` keys must be drawn from this set** — any other key silently never
matches.

| Feature key | Type | Supplied by the patient file | Match rule |
|---|---|---|---|
| `cancer` | list of strings | each `Condition[].cancer` | card list ∩ patient list, case-insensitive |
| `stage` | list of strings | each `Condition[].stage` | intersection, case-insensitive |
| `sex` | string | `Patient.gender` | intersection, case-insensitive |
| `age` | integer | `Patient.age` (or computed from `birthDate`) | via `age_min` / `age_max` |
| `biomarkers_present` | list of strings | each `Observation[].biomarker` | intersection, case-insensitive |
| `planned_therapy_class` | list of strings | each `MedicationRequest[].therapy_class` | intersection, case-insensitive |

Rules that matter:

- **Absent `applies_when` key = no constraint.**
- A stated list constraint requires the patient to actually *have* a matching
  value. If the patient has no `stage` and your card constrains `stage`, the card
  **does not fire** (conservative by design — we never flag on data the chart
  can't back up).
- `age_min` / `age_max` are **inclusive** integer bounds; a card using either
  requires the patient's age to be known.
- All string comparisons are lowercased/trimmed — `"Breast"` and `"breast"` are
  equivalent.
- The words used for `cancer`, `stage`, `planned_therapy_class`,
  `biomarkers_present` are **your vocabulary** — just keep the card and the
  patient consistent (decide `"gonadotoxic"`, use it in both).

---

## 3. Card fields

### Common to every card

```jsonc
{
  "id": "unique-string",                    // REQUIRED, any unique string
  "specialist": "fertility_preservation",   // REQUIRED, exact value from the table
  "applies_when": { ... },                  // optional; absent/empty = always applies
  "recommendation": "…",                    // REQUIRED — copied verbatim into the finding
  "recommendation_grade": "I / A",          // REQUIRED — copied verbatim; opaque free string
  "evidence_ref": "[factice] …",            // REQUIRED — copied verbatim
  "domain": "…",                            // OPTIONAL — overrides the finding's domain
  "issue": "…"                              // OPTIONAL — overrides the finding's issue text
}
```

- `recommendation_grade` is a **free string echoed byte-for-byte**; the agent
  never parses it. Use your two-axis convention: `"I / A"`, `"IIa / B"`,
  `"III / C"`, etc.
- The language model **never** rewrites `recommendation` /
  `recommendation_grade` / `evidence_ref`. Whatever you write is exactly what the
  orchestrator receives.

### Per-specialist extra fields

**`guideline_coverage`, `fertility_preservation`, `germline_testing`** (pure
lookup) — common fields plus optional:

```jsonc
"addressed_when": { "any_resource_text": ["keyword1", "keyword2"] }
```

If **any** keyword appears anywhere in the patient file, the finding is
`status: "addressed"`; otherwise `"gap"`. Omit it and each specialist uses
built-in defaults:

- fertility: `fertility`, `oncofertility`, `reproductive endocrinology`, `sperm banking`, `egg preservation`
- germline: `germline`, `genetic counseling`, `genetic testing`, `genetics referral`, `brca`
- guideline_coverage: `guideline addressed`, `plan documented`

**`biomarker_completeness`** — common fields plus **required**:

```jsonc
"requires": ["ER", "PR", "HER2"]
```

Logic: `missing = requires − biomarkers_present` (case-insensitive). Any missing
→ `gap` (the issue lists which are missing); none missing → `addressed`.
`addressed_when` is not used for this specialist.

**`goals_of_care`** — common fields plus optional:

```jsonc
"staleness_days": 180,
"addressed_when": { "any_resource_text": ["goals of care", "advance care planning"] }
```

The `any_resource_text` keywords **locate** the goals-of-care note in the chart;
`staleness_days` (default 180) is the freshness threshold. Logic:

- no matching note found → `gap` ("no goals-of-care conversation documented")
- note found, older than `staleness_days` → `gap` ("stale, N days old")
- note found, within threshold → `addressed`

The note's date is read from any of these fields on the resource: `date`,
`recordedDate`, `effectiveDateTime`, `authored`, `authoredOn`, `created`, or
`period.start` — ISO format (`YYYY-MM-DD…`).

---

## 4. Copy-paste templates

```jsonc
// shelf/guideline_coverage.json
[
  {
    "id": "guideline-breast-early-001",
    "specialist": "guideline_coverage",
    "applies_when": { "cancer": ["breast"], "stage": ["I", "II", "III"] },
    "recommendation": "…",
    "recommendation_grade": "IIa / B",
    "evidence_ref": "[factice] …",
    "addressed_when": { "any_resource_text": ["adjuvant therapy plan"] }
  }
]
```
```jsonc
// shelf/fertility_preservation.json
[
  {
    "id": "fertility-breast-premeno-001",
    "specialist": "fertility_preservation",
    "applies_when": {
      "cancer": ["breast"], "age_min": 18, "age_max": 45,
      "planned_therapy_class": ["gonadotoxic"]
    },
    "recommendation": "…",
    "recommendation_grade": "I / A",
    "evidence_ref": "[factice] …",
    "addressed_when": { "any_resource_text": ["fertility", "oncofertility"] }
  }
]
```
```jsonc
// shelf/germline_testing.json
[
  {
    "id": "germline-breast-001",
    "specialist": "germline_testing",
    "applies_when": { "cancer": ["breast"], "age_max": 50 },
    "recommendation": "…",
    "recommendation_grade": "I / B",
    "evidence_ref": "[factice] …",
    "addressed_when": { "any_resource_text": ["germline", "genetic counseling"] }
  }
]
```
```jsonc
// shelf/biomarker_completeness.json
[
  {
    "id": "biomarker-breast-001",
    "specialist": "biomarker_completeness",
    "applies_when": { "cancer": ["breast"] },
    "requires": ["ER", "PR", "HER2"],
    "recommendation": "…",
    "recommendation_grade": "I / A",
    "evidence_ref": "[factice] …"
  }
]
```
```jsonc
// shelf/goals_of_care.json
[
  {
    "id": "goc-breast-001",
    "specialist": "goals_of_care",
    "applies_when": { "cancer": ["breast"] },
    "staleness_days": 180,
    "recommendation": "…",
    "recommendation_grade": "III / C",
    "evidence_ref": "[factice] …",
    "addressed_when": { "any_resource_text": ["goals of care", "advance care planning"] }
  }
]
```

---

## 5. Patient-side cheat sheet (so your cards actually fire)

For a card to match, the synthetic patient must supply the matching fields:

```jsonc
{
  "patient_context": { "patient": { "gender": "female", "age": 34 } },
  "encounter_fhir": { "resources_by_type": {
    "Condition":         [ { "cancer": "breast", "stage": "II" } ],        // → cancer, stage
    "Observation":       [ { "biomarker": "ER" }, { "biomarker": "PR" } ], // → biomarkers_present
    "MedicationRequest": [ { "therapy_class": "gonadotoxic" } ],           // → planned_therapy_class
    "CarePlan":          [ { "title": "goals of care discussion", "date": "2024-01-10" } ] // GoC note + date
  }}
}
```

- To make an item show **addressed** instead of a gap, add a resource whose text
  contains one of that card's `addressed_when` keywords.
- To leave a **HER2 gap**, list ER/PR observations but not HER2.
- To trigger a **stale** goals-of-care gap, give the goals-of-care resource an
  old `date`; for a fresh one, use a recent date.

You can also shortcut everything with a top-level
`"features": {"cancer":["breast"],"stage":["II"],"age":34, ...}` block on the
patient — it overrides extraction — but the resource-based form above mirrors the
real Abridge schema and is what the demo uses.
```
