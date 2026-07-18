"""Configuration for the trials agent.

The Anthropic API key is read from ANTHROPIC_API_KEY at call time (see
llm_criteria.py); never hard-coded.
"""

from __future__ import annotations

import os

# Model for the non-obvious criteria call (reads the chart to judge free-text
# criteria). It NEVER decides the verdict — code does that deterministically.
MODEL = "claude-sonnet-5"

_HERE = os.path.dirname(os.path.abspath(__file__))

# On-disk canned trials ("shells"): one JSON file per trial (or a list).
TRIALS_DIR = os.path.join(_HERE, "trials")
