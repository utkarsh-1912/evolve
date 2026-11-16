"""Drives SIMULATED persona journeys through the real backend (FastAPI TestClient, nothing mocked) on an injectable
SIMULATED clock, and turns backend responses into harness events (TASK-P4-QA-EVAL item 2).

Per persona run: demo reset -> sign-in both partners -> both consents -> compatibility -> messages -> teach-back
(seeded answers; one counselor re-explanation + retry on failure) -> SURE -> counselor on shift -> book counseling for
trigger-(a) cases after a simulated delay -> complete confirmatory Tasks per the model -> read loop timer.
Every response addressed to either partner is scanned for the OTHER partner's identifying terms (live leakage check).
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
for d in (ROOT / "services" / "api", ROOT / "tests" / "_support"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

import qa_support as qs  # noqa: E402  (independent forbidden-term derivation)

from .personas import STRATA, ResponseModel  # noqa: E402

# Truth of each teach-back statement, judged by qa-redteam from the statement text (not read from the runtime).
TEACHBACK_TRUTH = {
    "teachback.q.carrier_not_diagnosis": False,  # "Being a carrier means I have the disease."
    "teachback.q.each_pregnancy": True,
    "teachback.q.negative_not_zero": True,
    "teachback.q.you_decide": True,
}


def make_backend():
    """Real app + SIMULATED clock. Returns (client, clock)."""
    from evolve_api.main import create_app  # noqa: WPS433
    from fastapi.testclient import TestClient
    from loopbus.machine import SimulatedClock
    from runtime.orchestrator import Runtime

    clock = SimulatedClock()
    return TestClient(create_app(Runtime(clock=clock))), clock


def _hdr(client, **body) -> dict:
    r = client.post("/api/session", json=body)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _blob(resp) -> str:
    try:
        return json.dumps(resp.json(), ensure_ascii=False)
    except ValueError:
        return resp.text


def run_persona(client, clock, persona: dict) -> tuple[list[dict], list[str]]:
    """Returns (events, problems). Problems are harness-level failures (non-2xx on the happy path, unknown keys)."""
    m = ResponseModel(persona)
    stratum = {k: persona[k] for k in STRATA}
    vid = m.vignette()
    couple = qs.vignette(vid)
    me = next((p for p in couple["partners"] if p["sex"] == persona["sex"]), couple["partners"][0])
    pid = me["partner_id"]
    other = next(p["partner_id"] for p in couple["partners"] if p["partner_id"] != pid)
    run_id = persona["persona_id"]
    problems: list[str] = []
    seen: dict[str, list[str]] = {pid: [], other: []}

    def call(who, method, path, h, **kw):
        r = getattr(client, method)(path, headers=h, **kw)
        if who in seen:
            seen[who].append(_blob(r))
        if r.status_code >= 400:
            problems.append(f"{run_id}: {method.upper()} {path} -> {r.status_code}")
        return r

    client.post("/api/demo/reset").raise_for_status()
    h = {pid: _hdr(client, partner_id=pid, lang=persona["lang"]), other: _hdr(client, partner_id=other)}
    call(pid, "post", "/api/consents", h[pid], json={"counterpart": other})
    call(other, "post", "/api/consents", h[other], json={"counterpart": pid})
    call(pid, "post", f"/api/couples/{vid}/compatibility", h[pid])
    for who in (pid, other):
        call(who, "get", "/api/me/messages", h[who])
        call(who, "get", "/api/me/vault", h[who])

    events: list[dict] = []
    qs_ = call(pid, "post", "/api/me/teachback/start", h[pid]).json().get("questions", [])
    keys = [q["key"] for q in qs_]
    if any(k not in TEACHBACK_TRUTH for k in keys):
        problems.append(f"{run_id}: unknown teach-back key(s) {sorted(set(keys) - set(TEACHBACK_TRUTH))}")
        return events, problems
    truths = [TEACHBACK_TRUTH[k] for k in keys]
    for attempt in (1, 2):
        answers = m.teachback(truths, attempt)
        res = call(pid, "post", "/api/teachback", h[pid], json={"answers": answers}).json()
        items = {k.split(".")[-1]: a == t for k, a, t in zip(keys, answers, truths)}
        events.append({"type": "comprehension", "persona": stratum, "run_id": run_id, "attempt": attempt,
                       "items": items, "passed": bool(res.get("passed")), "escalated": bool(res.get("escalated"))})
        if res.get("passed"):
            break
    sres = call(pid, "post", "/api/sure", h[pid], json={"answers": m.sure()}).json()
    events.append({"type": "sure", "persona": stratum, "run_id": run_id, "score": int(sres.get("score", 0)),
                   "phase": "post", "escalated": bool(sres.get("escalated"))})

    co = _hdr(client, role="counselor")
    call("counselor", "post", "/api/counselor/shift", co, json={"on": True})
    queue = [c for c in call("counselor", "get", "/api/counselor/queue", co).json() if c["couple_id"] == vid]
    for case in queue:
        if case["trigger"] == "a":
            clock.advance(timedelta(hours=m.booking_delay_hours()))
            co = _hdr(client, role="counselor")  # tokens live <= 1 h on the simulated clock (P-10)
            call("counselor", "post", "/api/counselor/shift", co, json={"on": True})
            call("counselor", "post", f"/api/counselor/cases/{case['case_id']}/tasks", co,
                 json={"kind": "appointment", "partner_id": pid})
            break
    done_tasks: set[str] = set()
    for case in queue:
        detail = call("counselor", "get", f"/api/counselor/cases/{case['case_id']}", co).json()
        for t in detail.get("tasks", []):
            kind = t.get("kind") or (t.get("code") or {}).get("text")
            if kind != "confirmatory_test" or t["id"] in done_tasks:
                continue
            done_tasks.add(t["id"])
            completed = m.confirmatory_completed()
            if completed:
                call("counselor", "patch", f"/api/counselor/cases/{case['case_id']}/tasks/{t['id']}", co,
                     json={"status": "completed"})
            events.append({"type": "task", "kind": "confirmatory", "completed": completed, "run_id": run_id})
    loop = call("counselor", "get", f"/api/loop/{vid}", co).json()
    timer = loop.get("timer") or {}
    if timer.get("required"):
        issued = next(x["ts"] for x in loop["history"] if x["state"] == "ResultIssued")
        events.append({"type": "booking", "couple_id": f"{vid}/{run_id}", "incompatible": True,
                       "result_ts": issued.replace("Z", "+00:00"),
                       "booked_ts": timer["booked_at"].replace("Z", "+00:00") if timer.get("booked_at") else None})

    leaks = 0
    for who, blobs in seen.items():
        terms = qs.forbidden_terms_for(who)
        leaks += sum(bool(qs.term_hits(b, terms)) for b in blobs)
    events.append({"type": "leak_scan", "responses": sum(len(b) for b in seen.values()), "leaks": leaks, "run_id": run_id})
    for g in client.get("/api/guardrail/events").json():
        events.append({"type": "guardrail", **g})
    return events, problems
