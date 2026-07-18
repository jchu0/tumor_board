"""Configuration for the guidelines agent.

Nothing secret lives here. The Anthropic API key is read from the
ANTHROPIC_API_KEY environment variable at call time (see synthesis.py); it is
never hard-coded or stored.
"""

from __future__ import annotations

import os

# The reasoning model used ONLY for the synthesis call (match_confidence,
# confidence_rationale, patient_facing_note). It never produces clinical
# recommendations or grades — those come straight from the shelf.
MODEL = "claude-sonnet-5"

_HERE = os.path.dirname(os.path.abspath(__file__))

# On-disk EBM "shelf": one JSON file per specialist, physician-authored.
SHELF_DIR = os.path.join(_HERE, "shelf")

# Placeholder fixtures (physician replaces these with real content).
FIXTURES_DIR = os.path.join(_HERE, "fixtures")
PLACEHOLDER_PATIENT_PATH = os.path.join(FIXTURES_DIR, "placeholder_patient.json")
