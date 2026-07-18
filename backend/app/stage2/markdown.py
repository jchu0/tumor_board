"""Small, deterministic markdown helpers for Stage 2 extraction.

Just the mechanical bits — tables and labeled `**Field:** value` lines. Prose is
left untouched (that's the enrichment layer's job), so these never interpret.
"""
from __future__ import annotations

import re

_SEPARATOR = re.compile(r"^\|?[\s:|-]*-[\s:|-]*\|?$")
_INLINE = re.compile(r"\*\*(.+?):\*\*[ \t]*([^|\n]*)")


def parse_tables(md: str) -> list[list[dict[str, str]]]:
    """Every GitHub-flavored markdown table as a list of row dicts keyed by header."""
    tables: list[list[dict[str, str]]] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        row = lines[i].strip()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if row.startswith("|") and _SEPARATOR.match(nxt):
            headers = [c.strip() for c in row.strip("|").split("|")]
            rows: list[dict[str, str]] = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                if len(cells) == len(headers):
                    rows.append(dict(zip(headers, cells)))
                j += 1
            tables.append(rows)
            i = j
        else:
            i += 1
    return tables


def find_table(md: str, *required_headers: str) -> list[dict[str, str]]:
    """The first table whose headers include all of `required_headers` (case-insensitive)."""
    want = {h.lower() for h in required_headers}
    for table in parse_tables(md):
        if table and want <= {h.lower() for h in table[0]}:
            return table
    return []


def get_cell(row: dict[str, str], *names: str) -> str | None:
    """Case-insensitive cell lookup by any of the given header names."""
    low = {k.lower(): v for k, v in row.items()}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def inline_fields(md: str) -> dict[str, str]:
    """All `**Key:** value` pairs (value = rest of its line, stops at a `|`).
    Keys lowercased; last occurrence wins."""
    return {m.group(1).strip().lower(): m.group(2).strip() for m in _INLINE.finditer(md)}
