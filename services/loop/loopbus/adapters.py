"""SIMULATED government/clinical adapters (P-19). No real Malaffi, SEHA, ART registry or Judicial
Department integration exists in this prototype (charter out-of-scope list). Each adapter records events
in memory and labels every record SIMULATED so the UI can show it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

SIMULATED = "SIMULATED"


class SimulatedAdapter:
    """In-memory stand-in for an external system. Payloads must carry opaque ids only (P-12)."""

    def __init__(self, system: str, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.system = system
        self.label = SIMULATED
        self._clock = clock
        self.sent: list[dict] = []

    def send(self, event: str, *, couple_id: str) -> dict:
        rec = {"system": self.system, "event": event, "couple_id": couple_id,
               "ts": self._clock().isoformat(), "label": SIMULATED}
        self.sent.append(rec)
        return rec


def default_adapters(clock=None) -> dict[str, SimulatedAdapter]:
    kw = {"clock": clock} if clock else {}
    return {name: SimulatedAdapter(name, **kw) for name in ("Malaffi", "SEHA", "ART", "Judicial")}
