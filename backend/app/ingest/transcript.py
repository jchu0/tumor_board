"""Parse the transcript STRING (real contract) into structured lines for the UI.

Real Abridge transcripts are a single string with 'SPEAKER:' labels. We parse
into {line, speaker, text} so findings can link to a transcript line. A line
without a leading label is appended to the previous speaker's turn.
"""
from __future__ import annotations

import re

_LABEL = re.compile(r"^\s*([A-Z][A-Z0-9_ ]{1,30}):\s*(.*)$")


def parse(transcript: str | list) -> list[dict]:
    # Already structured? pass through (keeps simplified synthetic working).
    if isinstance(transcript, list):
        return [
            {"line": i, "speaker": t.get("speaker"), "text": t.get("text", ""),
             "timestamp": t.get("timestamp")}
            for i, t in enumerate(transcript)
        ]

    lines: list[dict] = []
    for raw in (transcript or "").splitlines():
        if not raw.strip():
            continue
        m = _LABEL.match(raw)
        if m:
            lines.append({"line": len(lines), "speaker": m.group(1).strip(), "text": m.group(2).strip(), "timestamp": None})
        elif lines:
            lines[-1]["text"] += " " + raw.strip()
    return lines
