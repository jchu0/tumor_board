"""Shelf loader.

Reads every card file from `shelf/` into memory, keyed by the card's
`specialist` field. Cards are contract (B) — physician-authored EBM lookup
cards. The loader is deliberately forgiving about file shape (a file may hold a
single card object or a list of cards) so the shelf stays dead simple to
hand-edit.
"""

from __future__ import annotations

import json
import os
from typing import Any

from . import config

# Card = a plain dict following contract (B). We alias for readability.
Card = dict[str, Any]

_CACHE: dict[str, list[Card]] | None = None


def _read_card_file(path: str) -> list[Card]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError(
        f"shelf file {path} must contain a card object or a list of cards, "
        f"got {type(data).__name__}"
    )


def load_shelf(shelf_dir: str | None = None, *, refresh: bool = False) -> dict[str, list[Card]]:
    """Load all cards from the shelf, grouped by `specialist`.

    Results are cached; pass refresh=True (or a custom shelf_dir) to reload.
    """
    global _CACHE

    if shelf_dir is None:
        if _CACHE is not None and not refresh:
            return _CACHE
        shelf_dir = config.SHELF_DIR

    by_specialist: dict[str, list[Card]] = {}
    if os.path.isdir(shelf_dir):
        for name in sorted(os.listdir(shelf_dir)):
            if not name.endswith(".json"):
                continue
            for card in _read_card_file(os.path.join(shelf_dir, name)):
                specialist = card.get("specialist")
                if not specialist:
                    raise ValueError(
                        f"card {card.get('id', '<no id>')} in {name} is missing "
                        f"a 'specialist' field"
                    )
                by_specialist.setdefault(specialist, []).append(card)

    if shelf_dir == config.SHELF_DIR:
        _CACHE = by_specialist
    return by_specialist


def get_cards(specialist: str, shelf_dir: str | None = None) -> list[Card]:
    """Return the cards authored for one specialist (empty list if none)."""
    return load_shelf(shelf_dir).get(specialist, [])
