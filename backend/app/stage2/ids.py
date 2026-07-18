"""Deterministic identifier + derivation helpers (contract §1).

`element_id`s must be stable and reproducible from the source bytes and MUST NOT
contain array indices — reordering the source must never rewrite a citation.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Optional


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def source_digest(record) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(record).encode()).hexdigest()


def _resource_hash(resource) -> str:
    return hashlib.sha256(canonical_json(resource).encode()).hexdigest()[:8]


def slug(text: str) -> str:
    """lowercase; non-alphanumerics collapsed to '-'; leading/trailing '-' stripped."""
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "x"


def element_id(
    collection: str,
    label: str,
    seen: set[str],
    *,
    dated: Optional[str] = None,
    resource: Optional[dict] = None,
) -> str:
    """'{collection}/{slug}', optionally '@YYYY-MM-DD', with a sha256 suffix on
    collision. Registers the id in `seen`. Never uses positional indices."""
    base = f"{collection}/{slug(label)}"
    if dated:
        base = f"{base}@{dated[:10]}"
    eid = base
    if eid in seen and resource is not None:
        eid = f"{base}#{_resource_hash(resource)}"
    n = 2
    while eid in seen:  # pathological last resort — stable and index-free
        suffix = _resource_hash(resource) if resource is not None else "x"
        eid = f"{base}#{suffix}-{n}"
        n += 1
    seen.add(eid)
    return eid


def _parse(s: Optional[str]) -> Optional[date]:
    try:
        return date.fromisoformat(s[:10]) if s else None
    except (ValueError, TypeError):
        return None


def age_years(birth_date: Optional[str], board_date: Optional[str]) -> Optional[int]:
    b, d = _parse(birth_date), _parse(board_date)
    if not b or not d:
        return None
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def age_days(dated_at: Optional[str], board_date: Optional[str]) -> Optional[int]:
    a, d = _parse(dated_at), _parse(board_date)
    if not a or not d:
        return None
    return (d - a).days


_STAGE_PREFIXES = ("IV", "III", "II", "I", "0")


def stage_group(overall_stage: Optional[str]) -> str:
    """Coarse bucket for guidance matching: leading Roman numeral of overall_stage."""
    if not overall_stage:
        return "unknown"
    s = overall_stage.strip().upper()
    for p in _STAGE_PREFIXES:
        if s.startswith(p):
            return p
    return "unknown"


_NUM = re.compile(r"^\s*(-?\d+(?:\.\d+)?)")


def value_num(value) -> Optional[float]:
    """Parse a numeric ONLY when the value starts with a number (so 'exon 19
    deletion' → None, but '70% (high)' → 70.0). Ambiguous → None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = _NUM.match(str(value))
    return float(m.group(1)) if m else None
