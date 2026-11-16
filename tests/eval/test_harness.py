"""Eval harness end to end (TASK-P4-QA-EVAL): personas through the REAL backend (nothing mocked; SIMULATED clock) and the
evidence pack CLI. Small sizes keep CI fast; the full pack uses 10 personas per stratum (240 runs)."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "eval"))

from qa_eval import evaluate, persona_grid  # noqa: E402
from qa_eval.runner import make_backend, run_persona  # noqa: E402


@pytest.fixture(scope="module")
def live():
    client, clock = make_backend()
    events, problems = [], []
    for p in persona_grid(1, seed=7):
        ev, pr = run_persona(client, clock, p)
        events += ev
        problems += pr
    return events, problems


def test_persona_runs_have_no_harness_problems(live):
    assert live[1] == []


def test_live_runs_leak_nothing(live):
    scans = [e for e in live[0] if e["type"] == "leak_scan"]
    assert len(scans) == 24 and sum(e["responses"] for e in scans) > 0
    assert sum(e["leaks"] for e in scans) == 0


def test_dimensions_from_live_events(live):
    rep = evaluate([e for e in live[0] if e["type"] != "guardrail"])
    d = rep["dimensions"]
    assert rep["label"] == "SIMULATED" and all(v["label"] == "SIMULATED" for v in d.values())
    c = d["comprehension"]
    assert c["first_attempt_pass"]["n"] == 24 and c["first_attempt_pass"]["ci95"] is not None
    assert len(c["by_stratum"]) == 24
    assert d["informed_choice"]["sure_full"]["n"] == 24
    bookings = [e for e in live[0] if e["type"] == "booking"]
    assert bookings, "no trigger-(a) booking measured (V1 runs)"
    assert all(e["booked_ts"] for e in bookings)  # the counselor booking reached the loop timer


def test_guardrail_feed_events_are_contract_shaped(live):
    g = [e for e in live[0] if e["type"] == "guardrail"]
    assert g and all(set(e) <= {"type", "ts", "rule", "outcome", "message_id"} for e in g)


def test_cli_builds_evidence_pack(tmp_path):
    r = subprocess.run([sys.executable, "-m", "services.eval", "--per-stratum", "1", "--skip-tests", "--out", str(tmp_path)],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]
    e = json.loads((tmp_path / "evidence.json").read_text(encoding="utf-8"))
    assert e["label"] == "SIMULATED" and e["persona_runs"]["n"] == 24
    assert set(e["dimensions"]) == {"comprehension", "informed_choice", "loop_velocity", "calibration", "privacy"}
    assert e["dimensions"]["calibration"]["arithmetic_mismatches"] == 0
    assert e["build"]["contracts_sha256"] and e["contract_versions"]["api.md"]
    assert any(row["simulated"] is True for row in e["simulated_vs_real"])
    assert e["g2"]["decision"].startswith("DECISIONS #37")
    assert e["g2"]["llm_paraphrase_may_be_enabled"] is False or e["g2"]["two_sets_meet_target"] is True
    md = (tmp_path / "evidence.md").read_text(encoding="utf-8")
    assert md.startswith("# Evidence pack - SIMULATED") and "What is simulated vs real" in md
