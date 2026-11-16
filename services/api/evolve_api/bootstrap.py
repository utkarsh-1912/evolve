"""Path setup for the modular monolith (contracts/api.md): make our service packages importable without
pip-installing them. Import this module before anything from risk_engine/privacy/fhirgen/synth/runtime/loopbus.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
for _sub in ("agents", "loop", "risk_engine", "privacy", "fhir", "synth"):
    _p = str(ROOT / "services" / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
