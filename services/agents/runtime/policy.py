"""Runtime safety policy switches (DECISIONS #37).

LLM paraphrase is HARD-OFF. Patient text comes only from the closed template set. A Runtime refuses to start with an
LLM unless BOTH:
  1. env EVOLVE_ALLOW_LLM_PARAPHRASE == "1", and
  2. a recorded held-out pass file shows >= 2 fresh held-out sets with catch >= 0.95 and FP <= 0.05.
The pass file lives in the gate owner's directory (templates_verify/, TASK-P4-GATE); this module only reads it.
"""
from __future__ import annotations

import json
import os

from . import _paths

ENV_FLAG = "EVOLVE_ALLOW_LLM_PARAPHRASE"
HOLDOUT_PASS_FILE = _paths.ROOT / "services" / "agents" / "runtime" / "templates_verify" / "holdout_pass.json"
MIN_SETS, MIN_CATCH, MAX_FP = 2, 0.95, 0.05


class LLMPolicyError(RuntimeError):
    """An LLM was requested while paraphrase is not authorized (fail closed)."""


def _passing_sets() -> int:
    """Expected file shape: {"sets": [{"name", "catch", "fp"}, ...]}. Anything unreadable counts as zero."""
    try:
        data = json.loads(HOLDOUT_PASS_FILE.read_text(encoding="utf-8"))
        return sum(1 for s in data.get("sets", [])
                   if float(s["catch"]) >= MIN_CATCH and float(s["fp"]) <= MAX_FP)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return 0


def llm_paraphrase_allowed() -> bool:
    return os.environ.get(ENV_FLAG) == "1" and _passing_sets() >= MIN_SETS
