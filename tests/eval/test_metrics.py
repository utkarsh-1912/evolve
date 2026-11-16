"""Tests for the services/eval scaffold (R-EVAL-1). Synthetic event logs only; outputs must be stamped SIMULATED."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "eval"))

from qa_eval import STRATA, evaluate, guardrail_feed, persona_grid, wilson  # noqa: E402
from qa_eval.metrics import paired_signflip_p  # noqa: E402


def _personas(n=5):
    return list(persona_grid(n, seed=1))


def good_log():
    ev = []
    for i, p in enumerate(_personas()):
        persona = {k: p[k] for k in STRATA}
        ev.append({"type": "comprehension", "persona": persona,
                   "items": {"carrier_not_diagnosis": True, "each_pregnancy": True, "negative_not_zero": i % 20 != 0,
                             "you_decide": True}})
        ev.append({"type": "gcos", "persona": persona, "pre": 80.0, "post": 90.0 + (i % 3)})
        ev.append({"type": "sure", "persona": persona, "score": 4 if i % 20 else 3, "phase": "post"})
    ev += [{"type": "booking", "couple_id": f"SYN-C{i:04d}", "incompatible": True,
            "result_ts": "2026-11-01T08:00:00", "booked_ts": "2026-11-02T20:00:00"} for i in range(10)]
    ev += [{"type": "task", "kind": "confirmatory", "completed": True} for _ in range(20)]
    ev += [{"type": "arithmetic_sweep", "records": 618, "mismatches": 0}, {"type": "fhir_validation", "errors": 0}]
    ev += [{"type": "redteam", "category": "leakage", "n": 45, "intercepted": 45, "leaks": 0},
           {"type": "redteam", "category": "directive", "n": 42, "intercepted": 42, "leaks": 0}]
    return ev


def test_every_output_is_stamped_simulated():
    rep = evaluate(good_log())
    assert rep["label"] == "SIMULATED" and rep["simulated"] is True
    for d in rep["dimensions"].values():
        assert d["label"] == "SIMULATED"
    for row in rep["dimensions"]["privacy"]["table"]:
        assert row["label"] == "SIMULATED"
    assert "SIMULATED" in json.dumps(guardrail_feed([]))


def test_five_dimensions_present_and_good_log_meets_targets():
    rep = evaluate(good_log())
    assert set(rep["dimensions"]) == {"comprehension", "informed_choice", "loop_velocity", "calibration", "privacy"}
    assert all(d["meets"] for d in rep["dimensions"].values()), {k: d["meets"] for k, d in rep["dimensions"].items()}


def test_strata_are_language_literacy_gender():
    ps = _personas(2)
    assert len(ps) == 48 and all(p["simulated"] for p in ps)
    assert set(STRATA) == {"lang", "literacy", "sex", "relationship"} and len(STRATA["literacy"]) == 3
    rep = evaluate(good_log())
    assert len(rep["dimensions"]["comprehension"]["by_stratum"]) == 24


def test_comprehension_without_gcos_is_unknown_not_met():
    ev = [e for e in good_log() if e["type"] != "gcos"]
    c = evaluate(ev)["dimensions"]["comprehension"]
    assert c["gcos"]["instrumented"] is False and c["meets"] is None


@pytest.mark.parametrize("mutate,dim", [
    (lambda ev: ev.append({"type": "coercion_flag", "source": "test"}), "informed_choice"),
    (lambda ev: ev.append({"type": "booking", "couple_id": "SYN-C9999", "incompatible": True,
                           "result_ts": "2026-11-01T08:00:00", "booked_ts": "2026-11-03T09:00:00"}), "loop_velocity"),
    (lambda ev: ev.append({"type": "booking", "couple_id": "SYN-C9998", "incompatible": True,
                           "result_ts": "2026-11-01T08:00:00", "booked_ts": None}), "loop_velocity"),
    (lambda ev: ev.append({"type": "arithmetic_sweep", "records": 1, "mismatches": 1}), "calibration"),
    (lambda ev: ev.append({"type": "fhir_validation", "errors": 2}), "calibration"),
    (lambda ev: ev.append({"type": "redteam", "category": "x", "n": 10, "intercepted": 10, "leaks": 1}), "privacy"),
    (lambda ev: ev.append({"type": "redteam", "category": "y", "n": 10, "intercepted": 9, "leaks": 0}), "privacy"),
])
def test_single_violation_fails_its_dimension(mutate, dim):
    ev = good_log()
    mutate(ev)
    assert evaluate(ev)["dimensions"][dim]["meets"] is False


def test_empty_log_never_meets():
    rep = evaluate([])
    assert not any(d["meets"] for d in rep["dimensions"].values())


def test_wilson_interval():
    assert wilson(0, 0) is None
    lo, hi = wilson(45, 45)
    assert hi == 1.0 and 0.9 < lo < 1.0
    lo, hi = wilson(0, 100)
    assert lo == 0.0 and hi < 0.05


def test_signflip_detects_shift_and_not_noise():
    assert paired_signflip_p([1.0] * 30) < 0.01
    assert paired_signflip_p([1.0, -1.0] * 15) > 0.5


def test_guardrail_feed_rejects_text_or_genes():
    ok = guardrail_feed([{"ts": "t", "rule": "leakage", "outcome": "blocked", "message_id": "m1"}])
    assert ok["by_rule"]["leakage"]["blocked"] == 1
    with pytest.raises(ValueError):
        guardrail_feed([{"ts": "t", "rule": "leakage", "outcome": "blocked", "message_id": "m", "text": "SMN1"}])
