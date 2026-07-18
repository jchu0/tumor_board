# `data/` — one folder per patient

Each immediate subfolder of `data/` is **exactly one patient's data set**. Put that
patient's files inside their folder; the Stage 2 loader assembles them into one
`PatientCaseBundle`, in isolation.

```
data/
  patient-001/        <- one patient
    patient.json          FHIR Patient resource
    clinical.json         FHIR Bundle (or a list / individual resource files)
    metadata.json         optional: { "date": "YYYY-MM-DD", ... }  (the board date)
    transcript.txt        optional: the board transcript
  patient-002/        <- a different patient
    ...
  abridge/            <- RESERVED reference dataset, not a single patient (skipped)
```

## The rule: patient data never gets mixed up

Enforced in code (`backend/app/stage2/loader.py`, tested in `test_stage2_loader.py`):

1. **One folder → one bundle.** `load_patient_folder()` reads ONLY the files inside
   the folder it is given. No code path reads across sibling folders, so a new folder
   cannot bleed into an existing patient.
2. **Identity guard.** If the files in a folder reference more than one patient
   (a stray file from someone else), the load **raises `MixedPatientDataError`**
   instead of silently merging. Use consistent `subject: {reference: "Patient/<id>"}`
   references so this guard can see conflicts.
3. **Folder = partition key.** The bundle's `case_id` is the folder name, so two
   patients are never confused downstream even if their internal ids coincide.
4. **Per-patient failure isolation.** `load_all()` captures a bad folder's error
   against that patient only; the rest of the demo set still loads.

## Adding demo data

Just create a new folder and drop the patient's files in — no code change. It is
discovered and loaded in isolation at runtime:

```python
from app.stage2 import discover_patients, load_patient_folder, load_all

discover_patients()                 # -> [data/patient-001, data/patient-002, ...]
load_patient_folder("data/patient-001")   # -> one PatientCaseBundle
bundles, errors = load_all()        # every patient, failures isolated per-folder
```

## Accepted file shapes (auto-detected)

- a FHIR **Bundle** (`{"resourceType": "Bundle", "entry": [...]}`),
- a **list** of FHIR resources, or individual resource files (each with `resourceType`),
- a **Patient** resource → patient demographics,
- a full/partial **FHIR-envelope** record (`patient_context` / `encounter_fhir`),
- `metadata.json` → merged into the record metadata (holds the board `date`),
- `*.txt` / `*.md`, or a JSON with a `transcript` field → the transcript.

Filenames are flexible; classification is by content. A malformed JSON file fails the
whole patient's load loudly (clinical data is never silently dropped).
