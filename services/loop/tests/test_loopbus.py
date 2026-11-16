"""Loop bus: 7 states, forward only, HumanClosure human-only, 48 h booking timer on a simulated clock."""
from datetime import timedelta

import pytest

from loopbus import STATES, ForbiddenTransition, LoopBus, LoopError, SimulatedClock, default_adapters


def test_seven_states_in_order():
    assert STATES == ("ResultIssued", "PatientNotified", "ComprehensionConfirmed", "ConfirmatoryDone",
                      "CounselingDone", "ReproReferralDone", "HumanClosure")


def test_forward_only_with_recorded_skips():
    bus = LoopBus(SimulatedClock())
    bus.start("V1", booking_required=True)
    bus.advance("V1", "PatientNotified", actor_role="system")
    out = bus.advance("V1", "CounselingDone", actor_role="counselor")
    assert out["state"] == "CounselingDone"
    assert out["history"][-1]["skipped"] == ["ComprehensionConfirmed", "ConfirmatoryDone"]
    with pytest.raises(LoopError):
        bus.advance("V1", "PatientNotified", actor_role="counselor")
    with pytest.raises(LoopError):
        bus.advance("V1", "Nope", actor_role="counselor")


@pytest.mark.parametrize("role", ["system", "partner"])
def test_human_closure_only_by_counselor(role):
    bus = LoopBus(SimulatedClock())
    bus.start("V1", booking_required=False)
    with pytest.raises(ForbiddenTransition):
        bus.advance("V1", "HumanClosure", actor_role=role)
    assert bus.advance("V1", "HumanClosure", actor_role="counselor")["state"] == "HumanClosure"


def test_48h_booking_timer():
    clock = SimulatedClock()
    bus = LoopBus(clock)
    bus.start("V1", booking_required=True)
    clock.advance(timedelta(hours=47))
    assert bus.timer("V1")["overdue"] is False
    clock.advance(timedelta(hours=2))
    assert bus.timer("V1")["overdue"] is True and bus.overdue() == ["V1"]
    bus.start("V2", booking_required=True)
    clock.advance(timedelta(hours=10))
    bus.book_counseling("V2", actor_role="counselor")
    clock.advance(timedelta(hours=100))
    t = bus.timer("V2")
    assert t["booked_at"] and t["overdue"] is False and t["simulated"] is True


def test_no_timer_when_not_required_and_purge():
    bus = LoopBus(SimulatedClock())
    bus.start("V4", booking_required=False)
    assert bus.timer("V4")["required"] is False
    bus.purge("V4")
    with pytest.raises(LoopError):
        bus.get("V4")


def test_adapters_are_labelled_simulated():
    ads = default_adapters()
    assert set(ads) == {"Malaffi", "SEHA", "ART", "Judicial"}
    rec = ads["Judicial"].send("certificate_issued_regardless_of_result", couple_id="V1")
    assert rec["label"] == "SIMULATED"


def test_history_shape_and_listeners():
    bus = LoopBus(SimulatedClock())
    seen = []
    bus.listeners.append(lambda cid, state, role: seen.append((cid, state, role)))
    bus.start("V1", booking_required=True)
    bus.advance("V1", "PatientNotified", actor_role="system")
    assert seen == [("V1", "ResultIssued", "system"), ("V1", "PatientNotified", "system")]
    assert all({"state", "ts", "actor_role"} <= set(h) for h in bus.get("V1")["history"])
