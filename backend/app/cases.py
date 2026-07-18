"""Case repository — reads the on-disk patient folders in `data/cases/`.

Layout (authored, not FHIR):

    data/cases/<case_id>/
        case_meta.json            case identity + BENCHMARK GROUND TRUTH
        tumor_board_transcript.md the board discussion
        <specialty>/              biometrics, laboratory, oncology, pathology,
                                  radiology, medications, gynecology, pneumology...
            [<YYYY-MM-DD>_]<slug>.md

Two rules this module enforces:

1. THE ANSWER KEY NEVER LEAVES. `case_meta.json` carries `planted_gaps`,
   `expected_findings_count` and `noise_documents_not_expected_to_fire` — the
   benchmark ground truth. Serving those to a clinical view would both spoil the
   demo and show a clinician "findings" the system did not actually derive. Only
   the identity fields are exposed; see `CaseSummary`.

2. FOLDERS ARE DISCOVERED, NOT ASSUMED. Cases carry different specialties
   (variant_4 has pneumology; variant_3 has no laboratory). The API reports what
   is there, so the UI can render a tab per real folder rather than a fixed set
   with empty placeholders.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

CASES_DIR = Path(__file__).resolve().parents[2] / "data" / "cases"
TRANSCRIPT_NAME = "tumor_board_transcript.md"
META_NAME = "case_meta.json"

# Ground-truth keys that must never reach a clinical view.
_ANSWER_KEY_FIELDS = {"planted_gaps", "expected_findings_count",
                      "noise_documents_not_expected_to_fire", "notes",
                      # names the hero gap ids a variant closes — answer key too
                      "resolved_from_hero"}

# Preferred tab order. Anything not listed is appended alphabetically, so a new
# specialty folder shows up rather than being silently dropped.
_FOLDER_ORDER = ("biometrics", "oncology", "pathology", "radiology",
                 "laboratory", "medications", "pneumology", "gynecology")

_DATE_PREFIX = re.compile(r"(\d{4}-\d{2}-\d{2})")
_H1 = re.compile(r"^\s*#\s+(.+?)\s*$", re.M)


class Document(BaseModel):
    """One clinical document inside a specialty folder."""
    doc_id: str = Field(..., description="Stable id: '<folder>/<filename>'.")
    folder: str
    filename: str
    title: str = Field(..., description="First H1 in the file, else a title-cased filename.")
    date: Optional[str] = Field(None, description="From the filename, when it carries one.")
    body: str = Field(..., description="Raw markdown.")


class Folder(BaseModel):
    name: str
    label: str
    documents: list[Document] = Field(default_factory=list)


class CaseSummary(BaseModel):
    """Identity only — never the benchmark ground truth."""
    case_id: str
    cancer_type: Optional[str] = None
    patient_ref: Optional[str] = None
    line_of_therapy: Optional[str] = None
    board_date: Optional[str] = None
    folder_names: list[str] = Field(default_factory=list)
    document_count: int = 0


class CaseDetail(CaseSummary):
    folders: list[Folder] = Field(default_factory=list)
    transcript: Optional[str] = Field(None, description="Raw markdown of the board discussion.")


def _title_of(body: str, filename: str) -> str:
    m = _H1.search(body)
    if m:
        return m.group(1).replace("--", "—").strip()
    stem = Path(filename).stem
    stem = _DATE_PREFIX.sub("", stem).strip("_-")
    return stem.replace("_", " ").strip().capitalize() or filename


def _read_document(path: Path, folder: str) -> Document:
    body = path.read_text(encoding="utf-8")
    m = _DATE_PREFIX.search(path.name)
    return Document(
        doc_id=f"{folder}/{path.name}",
        folder=folder,
        filename=path.name,
        title=_title_of(body, path.name),
        date=m.group(1) if m else None,
        body=body,
    )


def _sort_documents(docs: list[Document]) -> list[Document]:
    """Undated documents first — they are standing records (demographics, the
    current medication list), not point-in-time events. Dated ones follow, newest
    first, which is the order a clinician reads a chart in."""
    undated = sorted((d for d in docs if not d.date), key=lambda d: d.filename)
    dated = sorted((d for d in docs if d.date), key=lambda d: d.date, reverse=True)
    return undated + dated


def _folder_sort_key(name: str) -> tuple[int, str]:
    return (_FOLDER_ORDER.index(name), "") if name in _FOLDER_ORDER else (len(_FOLDER_ORDER), name)


def _read_meta(case_dir: Path) -> dict:
    path = case_dir / META_NAME
    if not path.exists():
        return {}
    meta = json.loads(path.read_text(encoding="utf-8"))
    # Strip the answer key at the boundary, so it cannot leak by omission later.
    return {k: v for k, v in meta.items() if k not in _ANSWER_KEY_FIELDS}


def _case_dirs() -> list[Path]:
    if not CASES_DIR.is_dir():
        return []
    return sorted(p for p in CASES_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


@lru_cache(maxsize=1)
def list_cases() -> list[CaseSummary]:
    out: list[CaseSummary] = []
    for case_dir in _case_dirs():
        meta = _read_meta(case_dir)
        folders = sorted(
            (d.name for d in case_dir.iterdir() if d.is_dir() and not d.name.startswith(".")),
            key=_folder_sort_key,
        )
        count = sum(1 for _ in case_dir.rglob("*.md")) - (1 if (case_dir / TRANSCRIPT_NAME).exists() else 0)
        out.append(CaseSummary(
            case_id=meta.get("case_id", case_dir.name),
            cancer_type=meta.get("cancer_type"),
            patient_ref=meta.get("patient_ref"),
            line_of_therapy=meta.get("line_of_therapy"),
            board_date=meta.get("board_date"),
            folder_names=folders,
            document_count=max(count, 0),
        ))
    return out


@lru_cache(maxsize=32)
def get_case(case_id: str) -> Optional[CaseDetail]:
    case_dir = next((d for d in _case_dirs() if d.name == case_id), None)
    if case_dir is None:
        return None
    meta = _read_meta(case_dir)

    folders: list[Folder] = []
    for sub in sorted((d for d in case_dir.iterdir() if d.is_dir() and not d.name.startswith(".")),
                      key=lambda d: _folder_sort_key(d.name)):
        docs = _sort_documents([_read_document(p, sub.name) for p in sub.glob("*.md")])
        folders.append(Folder(name=sub.name, label=sub.name.replace("_", " ").title(), documents=docs))

    transcript_path = case_dir / TRANSCRIPT_NAME
    return CaseDetail(
        case_id=meta.get("case_id", case_dir.name),
        cancer_type=meta.get("cancer_type"),
        patient_ref=meta.get("patient_ref"),
        line_of_therapy=meta.get("line_of_therapy"),
        board_date=meta.get("board_date"),
        folder_names=[f.name for f in folders],
        document_count=sum(len(f.documents) for f in folders),
        folders=folders,
        transcript=transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else None,
    )
