"""Make the sibling service packages importable (no pip installs of our own packages; contracts/api.md)."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE_DIRS = ("risk_engine", "privacy", "fhir", "synth", "loop", "agents")


def ensure() -> pathlib.Path:
    for sub in SERVICE_DIRS:
        p = str(ROOT / "services" / sub)
        if p not in sys.path:
            sys.path.append(p)
    return ROOT
