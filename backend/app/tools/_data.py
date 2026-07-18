"""Loader for the canned lookup tables in app/data/."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def load(name: str) -> dict | list:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)
