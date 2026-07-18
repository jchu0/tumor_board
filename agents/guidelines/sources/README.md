# Breast cancer guideline sources

Real, downloaded reference documents for authoring the breast-cancer shelf
cards. **These are source material, not agent code** — the physician reads them
and transcribes recommendations into `shelf/*.json` (see `../shelf/AUTHORING.md`).

Downloaded 2026-07-18.

| File | What it is | Best for | Grades? |
|---|---|---|---|
| `ESMO_Breast_Pocket_Guideline_2025.pdf` | ESMO Breast Cancer Pocket Guideline 2025 (professional, compact) | **Card authoring** — recommendations with ESMO evidence levels | ✅ `[I, A]`-style |
| `ESMO_Breast_Pocket_Guideline_2024.pdf` | ESMO Breast Cancer Pocket Guideline 2024 | Prior-year cross-check | ✅ |
| `NCCN_Patients_Invasive_Breast.pdf` | NCCN Guidelines for Patients: Invasive Breast Cancer | Full early/invasive treatment pathway (plain-language, real) | ✗ (patient version) |
| `NCCN_Patients_Metastatic_Breast.pdf` | NCCN Guidelines for Patients: Metastatic Breast Cancer | Full metastatic treatment pathway | ✗ (patient version) |

## How these map to `recommendation_grade`

The ESMO pocket guidelines use ESMO's Level of Evidence (I–V) / Grade of
Recommendation (A–E), printed as e.g. `[I, A]` after a statement. That maps
directly to the plan's two-axis convention — put it verbatim:

```
"recommendation_grade": "I / A (ESMO Breast 2025)"
"evidence_ref": "ESMO Breast Cancer Pocket Guideline 2025, <section>"
```

The NCCN *patient* PDFs are not graded (they're the plain-language versions) —
use them for the treatment-pathway overview and the biomarker/therapy vocabulary,
not for grades.

## Biomarker `requires` lists (standard-of-care testing panels, factual)

- Breast: `["ER", "PR", "HER2"]` (optionally `"Ki-67"`)
- NSCLC (Variant 4 control): `["EGFR", "ALK", "ROS1", "BRAF", "PD-L1"]`

## Still needed (gated — grab via your own access, cannot be scripted)

- **NCCN Clinical Practice Guidelines: Breast Cancer** (clinician version, the
  most comprehensive, with NCCN Categories 1/2A/2B/3) — free with registration at
  <https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1419>
- **ESMO Early Breast Cancer CPG full text** (Annals of Oncology, open access;
  bot-blocked to scripts, opens fine in a browser) —
  <https://www.annalsofoncology.org/article/S0923-7534(23)05104-9/fulltext>
- **ESMO Metastatic Breast Cancer CPG** — <https://www.esmo.org/guidelines>
