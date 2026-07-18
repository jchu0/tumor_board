"""Trial loader.

Reads the canned trial "shells" from `trials/` into memory. Like the guidelines
shelf, a file may hold a single trial object or a list of trials, so the folder
stays dead simple to hand-edit.
"""

from __future__ import annotations

import json
import os
from typing import Any

from . import config

Trial = dict[str, Any]

_CACHE: list[Trial] | None = None


def _read_file(path: str) -> list[Trial]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError(
        f"trial file {path} must contain a trial object or a list, "
        f"got {type(data).__name__}"
    )


def load_trials(trials_dir: str | None = None, *, refresh: bool = False) -> list[Trial]:
    """Load every trial from the trials directory."""
    global _CACHE
    if trials_dir is None:
        if _CACHE is not None and not refresh:
            return _CACHE
        trials_dir = config.TRIALS_DIR

    trials: list[Trial] = []
    if os.path.isdir(trials_dir):
        for name in sorted(os.listdir(trials_dir)):
            if name.endswith(".json"):
                trials.extend(_read_file(os.path.join(trials_dir, name)))

    if trials_dir == config.TRIALS_DIR:
        _CACHE = trials
    return trials
