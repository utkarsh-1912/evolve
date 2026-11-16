"""API contract v1.2.x (P3) through TestClient: SMART hardening, portal endpoints, counselor workbench."""
import base64
import hashlib
import json
import secrets
from datetime import timedelta

import pytest

from conftest import consent_both, login

GENES = ["CYP21A2", "HBB", "MEFV", "ABCA4", "HBA2", "SMN1", "DONSON", "ALDH3A2", "TPO", "CYP1B1", "GJB2"]


@pytest.fixture
def sim_client():
    """Client on a SIMULATED clock (own Authority so signed sets match the clock)."""
    from fastapi.testclient import TestClient
    from evolve_api.main import create_app
    from loopbus import SimulatedClock
    from runtime.orchestrator import Runtime
    clock = SimulatedClock()
    app = create_app(Runtime(clock=clock))
    with TestClient(app) as c:
        c.rt, c.clock = app.state.runtime, clock
        yield c


def counselor_on_shift(client):
    h = login(client, role="counselor")
    assert client.post("/api/counselor/shift", json={"on": True}, headers=h).json()["on_shift"] is True
    return h


# --------------------------------------------------------------------- SMART hardening (R-PRIV-3)
def test_token_ttl_enforced_on_clock(sim_client):
    h = login(sim_client, "V1A")
    assert sim_client.get("/api/me/home", headers=h).status_code == 200
    sim_client.clock.advance(timedelta(minutes=59))
    assert sim_client.get("/api/me/home", headers=h).status_code == 200
    sim_client.clock.advance(timedelta(minutes=2))
    r = sim_client.get("/api/me/home", headers=h)
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"


def test_scopes_enforced_per_endpoint(client):
    r = client.post("/api/session", json={"partner_id": "V1A", "scopes": ["patient/Consent.cru"]}).json()
    h = {"Authorization": "Bearer " + r["token"]}
    assert r["scopes"] == ["patient/Consent.cru"]
    assert client.get("/api/consents", headers=h).status_code == 200
    for path in ("/api/me/vault", "/api/me/home", "/api/me/care-plan", "/api/me/notifications"):
        res = client.get(path, headers=h)
        assert res.status_code == 403 and res.json()["error"]["code"] == "insufficient_scope", path
    assert client.post("/api/session", json={"partner_id": "V1A", "scopes": ["patient/Task.cru"]}).status_code == 400
    c = client.post("/api/session", json={"role": "counselor", "scopes": ["user/DiagnosticReport.rs"]}).json()
    hc = {"Authorization": "Bearer " + c["token"]}
    assert client.post("/api/counselor/shift", json={"on": True}, headers=hc).json()["error"]["code"] == "insufficient_scope"


def _pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def test_pkce_flow_single_use_and_verifier_check(client):
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(24)
    a = client.post("/api/auth/authorize", json={"partner_id": "V2A", "code_challenge": challenge,
                                                 "code_challenge_method": "S256", "state": state}).json()
    assert a["state"] == state and a["simulated"] is True
    bad = client.post("/api/auth/token", json={"code": a["code"], "code_verifier": secrets.token_urlsafe(48)})
    assert bad.status_code == 400  # wrong verifier burns the code
    a2 = client.post("/api/auth/authorize", json={"partner_id": "V2A", "code_challenge": challenge,
                                                  "code_challenge_method": "S256", "state": state}).json()
    t = client.post("/api/auth/token", json={"code": a2["code"], "code_verifier": verifier}).json()
    assert t["partner_id"] == "V2A" and t["expires_in"] <= 3600
    assert client.get("/api/me/vault", headers={"Authorization": "Bearer " + t["token"]}).status_code == 200
    assert client.post("/api/auth/token", json={"code": a2["code"], "code_verifier": verifier}).status_code == 400
    plain = client.post("/api/auth/authorize", json={"partner_id": "V2A", "code_challenge": challenge,
                                                     "code_challenge_method": "plain", "state": state})
    assert plain.status_code == 400
    short_state = client.post("/api/auth/authorize", json={"partner_id": "V2A", "code_challenge": challenge,
                                                           "code_challenge_method": "S256", "state": "abc"})
    assert short_state.status_code == 400


def test_pkce_code_expires(sim_client):
    verifier, challenge = _pkce()
    a = sim_client.post("/api/auth/authorize", json={"partner_id": "V1A", "code_challenge": challenge,
                                                     "state": secrets.token_urlsafe(24)}).json()
    sim_client.clock.advance(timedelta(seconds=61))
    assert sim_client.post("/api/auth/token", json={"code": a["code"], "code_verifier": verifier}).status_code == 400


# --------------------------------------------------------------------- citizen portal
def test_home_activity_notifications_shapes(client):
    ha, hb, _, _ = consent_both(client, "V3")
    client.post("/api/couples/V3/compatibility", headers=ha)
    home = client.get("/api/me/home", headers=hb).json()
    assert set(home) == {"next_step", "couple_status", "consent", "counts"}
    assert set(home["next_step"]) == {"kind", "title_key", "href"} and home["couple_status"] == "result_ready"
    act = client.get("/api/me/activity?limit=5", headers=hb).json()
    assert 0 < len(act) <= 5 and all(set(e) == {"ts", "actor_role", "action", "object_kind"} for e in act)
    dump = json.dumps(act)
    assert "V3A" not in dump and not any(g in dump for g in GENES)
    notes = client.get("/api/me/notifications", headers=hb).json()
    assert all(set(n) == {"id", "ts", "kind", "title_key", "href", "read"} for n in notes)
    r = client.post(f"/api/me/notifications/{notes[0]['id']}/read", headers=hb).json()
    assert r["read"] is True
    assert client.post(f"/api/me/notifications/{notes[0]['id']}/read", headers=ha).status_code == 404  # not A's


def test_care_plan_shape_and_no_leak(client):
    ha, hb, _, _ = consent_both(client, "V3")
    client.post("/api/couples/V3/compatibility", headers=ha)
    a = client.get("/api/me/care-plan", headers=ha).json()
    assert {"loop", "tasks", "appointments", "options", "eligibility"} <= set(a)
    assert set(a["tasks"][0]) == {"id", "kind", "status", "due"}
    assert all(set(o) == {"id", "title_key", "body_key"} for o in a["options"])
    assert {"immediate", "checks"} == set(a["eligibility"])
    b = client.get("/api/me/care-plan", headers=hb).json()
    assert b["tasks"] == [] and not any(g in json.dumps(b) for g in GENES)
    assert client.get("/api/loop/V3", headers=hb).json()["state"] == "PatientNotified"


def test_teachback_start_and_family_tokens(client):
    ha, hb, _, _ = consent_both(client, "V3")
    q = client.post("/api/me/teachback/start", headers=ha).json()["questions"]
    assert len(q) == 4 and all("key" in x for x in q)
    t = client.post("/api/family/tokens", json={"hgnc_id": 11117}, headers=ha).json()
    assert {"token", "qr_payload", "expires_at"} <= set(t) and "V3A" not in json.dumps(t)
    assert client.post("/api/family/tokens", json={"hgnc_id": 11117}, headers=hb).status_code == 403


def test_disclosure_consent_via_api(client):
    ha, hb, _, _ = consent_both(client, "V3")
    client.post("/api/couples/V3/compatibility", headers=ha)
    bad = client.post("/api/consents", json={"purpose": "disclose-gene-to-partner", "hgnc_id": 11117}, headers=hb)
    assert bad.status_code == 422
    c = client.post("/api/consents", json={"purpose": "disclose-gene-to-partner", "hgnc_id": 11117}, headers=ha).json()
    assert c["purpose"] == "disclose-gene-to-partner"
    assert [t["kind"] for t in client.get("/api/me/care-plan", headers=hb).json()["tasks"]] == ["confirmatory_test"]
    assert client.delete(f"/api/consents/{c['id']}", headers=hb).status_code == 403
    assert client.delete(f"/api/consents/{c['id']}", headers=ha).json()["status"] == "inactive"


# --------------------------------------------------------------------- counselor workbench
def test_cases_require_shift_and_scope(client):
    ha, _, _, _ = consent_both(client, "V1")
    client.post("/api/couples/V1/compatibility", headers=ha)
    hc = login(client, role="counselor")
    r = client.get("/api/counselor/cases", headers=hc)
    assert r.status_code == 403 and r.json()["error"]["code"] == "off_shift"
    # DECISIONS #40: the legacy queue and briefs are shift-gated too
    assert client.get("/api/counselor/queue", headers=hc).json()["error"]["code"] == "off_shift"
    case_id = next(iter(client.rt.cases))
    assert client.get(f"/api/counselor/briefs/{case_id}", headers=hc).status_code == 403
    client.post("/api/counselor/shift", json={"on": True}, headers=hc)
    assert client.get("/api/counselor/queue", headers=hc).status_code == 200
    assert client.get(f"/api/counselor/briefs/{case_id}", headers=hc).status_code == 200
    client.post("/api/counselor/shift", json={"on": False}, headers=hc)
    assert client.get("/api/counselor/queue", headers=hc).status_code == 403
    client.post("/api/counselor/shift", json={"on": True}, headers=hc)
    rows = client.get("/api/counselor/cases?status=open&trigger=a", headers=hc).json()
    assert len(rows) == 1
    assert {"case_id", "couple_id", "trigger", "priority", "opened_at", "sla_due_at", "couple_status", "assigned_to"} <= set(rows[0])
    assert client.get("/api/counselor/cases", headers=ha).status_code == 403  # partner


def test_case_view_tasks_notes_closure_via_api(client):
    ha, hb, _, _ = consent_both(client, "V1")
    client.post("/api/couples/V1/compatibility", headers=ha)
    hc = counselor_on_shift(client)
    cid = client.get("/api/counselor/cases", headers=hc).json()[0]["case_id"]
    v = client.get(f"/api/counselor/cases/{cid}", headers=hc).json()
    assert {"brief", "pedigree", "variants", "tasks", "notes", "timeline", "access_basis"} <= set(v)
    assert v["access_basis"] == {"couple_consent": True, "on_shift": True}
    assert set(v["pedigree"]) >= {"nodes", "edges", "F", "relationship"}
    t = client.post(f"/api/counselor/cases/{cid}/tasks", json={"kind": "appointment"}, headers=hc).json()
    assert len(t["tasks"]) == 2 and t["tasks"][0]["resourceType"] == "Task"
    assert client.get("/api/me/care-plan", headers=ha).json()["appointments"][0]["simulated"] is True
    assert client.get(f"/api/loop/V1", headers=hc).json()["timer"]["booked_at"]
    p = client.patch(f"/api/counselor/cases/{cid}/tasks/{t['tasks'][0]['id']}", json={"status": "done"}, headers=hc)
    assert p.status_code == 422
    n = client.post(f"/api/counselor/cases/{cid}/notes", json={"text": "Couple asked about options."}, headers=hc).json()
    assert n["visible_to_patient"] is False
    assert "asked about" not in json.dumps(client.get("/api/me/messages", headers=ha).json())  # notes never reach patients
    assert client.post(f"/api/counselor/cases/{cid}/closure", json={"summary": "x"}, headers=ha).status_code == 403
    out = client.post(f"/api/counselor/cases/{cid}/closure", json={"summary": "Counseling complete."}, headers=hc).json()
    assert out["loop"]["state"] == "HumanClosure"
    keys = [x["title_key"] for x in client.get("/api/me/notifications", headers=hb).json()]
    assert "notif.loop.HumanClosure" in keys


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"])
def test_cors_allows_citizen_counselor_and_eval_apps(client, origin):
    r = client.options("/api/demo/vignettes", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == origin


def test_loop_advance_shift_gated_and_closure_counselor_only(client):
    ha, _, _, _ = consent_both(client, "V1")
    client.post("/api/couples/V1/compatibility", headers=ha)
    hc = login(client, role="counselor")
    off = client.post("/api/loop/V1/advance", json={"to": "CounselingDone"}, headers=hc)
    assert off.status_code == 403 and off.json()["error"]["code"] == "off_shift"
    assert client.post("/api/loop/V1/advance", json={"to": "HumanClosure"}, headers=ha).status_code == 403  # partner
    client.post("/api/counselor/shift", json={"on": True}, headers=hc)
    on = client.post("/api/loop/V1/advance", json={"to": "CounselingDone"}, headers=hc)
    assert on.status_code == 200 and on.json()["state"] == "CounselingDone"
    assert client.post("/api/loop/V1/advance", json={"to": "HumanClosure"}, headers=hc).json()["state"] == "HumanClosure"
