"""Closed-loop care state machine (R-UX-3 backend; docs/02 §6; source §Tier 6).

ResultIssued -> PatientNotified -> ComprehensionConfirmed -> ConfirmatoryDone -> CounselingDone
-> ReproReferralDone -> HumanClosure

Rules
- Forward only. A state may be skipped when it does not apply (e.g. no confirmatory test); the skip is
  recorded in the history so the counselor can see it.
- Only a human counselor (actor_role == "counselor") may write HumanClosure (P-18).
- Booking timer: couples that need counseling (trigger (a) incompatible) must be booked within 48 h of
  ResultIssued (source §5 metric 3). The clock is injectable; in the demo it is a simulated clock.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

STATES = (
    "ResultIssued",
    "PatientNotified",
    "ComprehensionConfirmed",
    "ConfirmatoryDone",
    "CounselingDone",
    "ReproReferralDone",
    "HumanClosure",
)
HUMAN_ONLY = "HumanClosure"
ACTOR_ROLES = ("system", "partner", "counselor")
BOOKING_WINDOW = timedelta(hours=48)

Clock = Callable[[], datetime]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LoopError(Exception):
    """Unknown loop or invalid transition."""


class ForbiddenTransition(LoopError):
    """The actor may not perform this transition (e.g. non-human HumanClosure)."""


class SimulatedClock:
    """SIMULATED clock for demos and tests: starts at a fixed instant and only moves when advanced."""

    def __init__(self, start: Optional[datetime] = None):
        self._now = start or datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> datetime:
        self._now = self._now + delta
        return self._now


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class LoopBus:
    def __init__(self, clock: Clock = utcnow, booking_window: timedelta = BOOKING_WINDOW):
        self.clock = clock
        self.booking_window = booking_window
        self._loops: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.listeners: list[Callable[[str, str, str], None]] = []  # (couple_id, state, actor_role)

    def _emit(self, couple_id: str, state: str, actor_role: str) -> None:
        for fn in list(self.listeners):
            fn(couple_id, state, actor_role)

    # ------------------------------------------------------------------ lifecycle
    def start(self, couple_id: str, *, booking_required: bool, actor_role: str = "system") -> dict:
        """(Re)open a loop at ResultIssued. Restarting replaces the previous loop for this couple."""
        now = self.clock()
        with self._lock:
            self._loops[couple_id] = {
                "state": STATES[0],
                "history": [{"ts": _iso(now), "state": STATES[0], "to": STATES[0], "actor_role": actor_role,
                             "skipped": []}],
                "issued_at": now,
                "booking_required": bool(booking_required),
                "booked_at": None,
            }
        self._emit(couple_id, STATES[0], actor_role)
        return self.get(couple_id)

    def advance(self, couple_id: str, to: str, *, actor_role: str) -> dict:
        if to not in STATES:
            raise LoopError("unknown state")
        if actor_role not in ACTOR_ROLES:
            raise ForbiddenTransition("unknown actor role")
        if to == HUMAN_ONLY and actor_role != "counselor":
            raise ForbiddenTransition("only a human counselor may record HumanClosure")
        now = self.clock()
        with self._lock:
            loop = self._loops.get(couple_id)
            if loop is None:
                raise LoopError("no loop for this couple")
            cur, nxt = STATES.index(loop["state"]), STATES.index(to)
            if nxt <= cur:
                raise LoopError("transitions are forward only")
            skipped = list(STATES[cur + 1:nxt])
            loop["state"] = to
            loop["history"].append({"ts": _iso(now), "state": to, "to": to, "actor_role": actor_role,
                                    "skipped": skipped})
        self._emit(couple_id, to, actor_role)
        return self.get(couple_id)

    def book_counseling(self, couple_id: str, *, actor_role: str) -> dict:
        if actor_role not in ("counselor", "system"):
            raise ForbiddenTransition("booking is recorded by the counselor service")
        with self._lock:
            loop = self._loops.get(couple_id)
            if loop is None:
                raise LoopError("no loop for this couple")
            if loop["booked_at"] is None:
                loop["booked_at"] = self.clock()
        return self.get(couple_id)

    def purge(self, couple_id: str) -> None:
        with self._lock:
            self._loops.pop(couple_id, None)

    def reset(self) -> None:
        with self._lock:
            self._loops.clear()

    # ------------------------------------------------------------------ views
    def timer(self, couple_id: str) -> dict:
        with self._lock:
            loop = self._loops.get(couple_id)
            if loop is None:
                raise LoopError("no loop for this couple")
            if not loop["booking_required"]:
                return {"required": False, "deadline": None, "booked_at": None, "overdue": False, "simulated": True}
            deadline = loop["issued_at"] + self.booking_window
            booked = loop["booked_at"]
            overdue = (booked is None and self.clock() > deadline) or (booked is not None and booked > deadline)
            return {"required": True, "deadline": _iso(deadline), "booked_at": _iso(booked) if booked else None,
                    "overdue": overdue, "simulated": True}

    def overdue(self) -> list[str]:
        return [cid for cid in list(self._loops) if self.timer(cid)["overdue"]]

    def get(self, couple_id: str) -> dict:
        with self._lock:
            loop = self._loops.get(couple_id)
            if loop is None:
                raise LoopError("no loop for this couple")
            out = {"state": loop["state"], "history": [dict(h) for h in loop["history"]], "states": list(STATES)}
        out["timer"] = self.timer(couple_id)
        return out

    def has(self, couple_id: str) -> bool:
        with self._lock:
            return couple_id in self._loops
