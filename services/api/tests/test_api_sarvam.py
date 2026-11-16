"""API v1.3.0: counselor AI summary draft + /api/config + CORS from env (DECISIONS #62, P-21).
Fake HTTP transport only (no network)."""
import json

import pytest

from conftest import consent_both, login

# PAUSED (coordinator priority change 2026-11-16: deployment first, AI later). The summary-draft endpoint is unwired
# from the app; these tests are kept unchanged so the feature can be resumed by re-wiring it.
pytestmark = pytest.mark.skip(reason="counselor AI draft paused: deployment first; endpoint not wired")

CANARY = "Zephyr-marker summary for counselor review only."


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append(json.loads(body))
        r = self.responses.pop(0) if self.responses else (200, {"choices": [{"message": {"content": CANARY}}]})
        if isinstance(r, Exception):
            raise r
        return r[0], json.dumps(r[1]).encode()


def ok(text):
    return 200, {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}


@pytest.fixture
def make_client(authority):
    from fastapi.testclient import TestClient
    from evolve_api.main import create_app
    from runtime.llm_sarvam import SarvamClient
    from runtime.orchestrator import Runtime

    def build(*responses):
        transport = FakeTransport(*responses)
        app = create_app(Runtime(authority=authority), llm_client=SarvamClient("k", transport=transport,
                                                                                   sleep=lambda s: None))
        c = TestClient(app)
        c.rt, c.transport = app.state.runtime, transport
        return c
    return build


def _setup(c, cid="V3"):
    ha, hb, _, _ = consent_both(c, cid)
    c.post(f"/api/couples/{cid}/compatibility", headers=ha)
    hc = login(c, role="counselor")
    c.post("/api/counselor/shift", json={"on": True}, headers=hc)
    case_id = next(x["case_id"] for x in c.get("/api/counselor/cases", headers=hc).json() if x["couple_id"] == cid)
    return ha, hb, hc, case_id


def test_summary_draft_success_shape(make_client):
    c = make_client(ok(CANARY))
    _, _, hc, case_id = _setup(c)
    r = c.post(f"/api/counselor/cases/{case_id}/summary-draft", headers=hc)
    assert r.status_code == 200
    body = r.json()
    assert {"draft", "provider", "model", "generated_at", "ai_generated", "gate", "input_fields"} <= set(body)
    assert body["draft"] == CANARY and body["provider"] == "sarvam" and body["ai_generated"] is True
    assert body["gate"] == {"passed": True, "violations": []}
    sent = json.dumps(c.transport.calls[0])
    assert "V3A" not in sent and "V3B" not in sent


@pytest.mark.parametrize("failure", [
    (402, {"error": {"code": "insufficient_quota_error", "message": "quota"}}),
    "429x2",
    TimeoutError("slow"),
])
def test_provider_errors_map_to_503(make_client, failure):
    if failure == "429x2":
        responses = [(429, {"error": {"code": "rate_limit_exceeded_error"}})] * 2
    else:
        responses = [failure]
    c = make_client(*responses)
    _, _, hc, case_id = _setup(c)
    r = c.post(f"/api/counselor/cases/{case_id}/summary-draft", headers=hc)
    assert r.status_code == 503 and r.json()["error"]["code"] == "llm_unavailable"


def test_gate_blocks_drifted_number_and_returns_no_text(make_client):
    c = make_client(ok("The chance per pregnancy is 1 in 50."))
    _, _, hc, case_id = _setup(c)
    body = c.post(f"/api/counselor/cases/{case_id}/summary-draft", headers=hc).json()
    assert body["draft"] is None and body["gate"]["passed"] is False
    assert "numeric_drift" in {v["rule"] for v in body["gate"]["violations"]}


def test_prompt_excludes_notes_and_ids(make_client):
    c = make_client(ok(CANARY))
    _, _, hc, case_id = _setup(c)
    c.post(f"/api/counselor/cases/{case_id}/notes", json={"text": "NOTE-SHOULD-NOT-LEAVE the clinic"}, headers=hc)
    c.post(f"/api/counselor/cases/{case_id}/summary-draft", headers=hc)
    sent = json.dumps(c.transport.calls[0])
    assert "NOTE-SHOULD-NOT-LEAVE" not in sent and "Patient/" not in sent and "V3" not in sent


def test_shift_and_role_gating(make_client):
    c = make_client(ok(CANARY))
    ha, _, hc, case_id = _setup(c)
    c.post("/api/counselor/shift", json={"on": False}, headers=hc)
    r = c.post(f"/api/counselor/cases/{case_id}/summary-draft", headers=hc)
    assert r.status_code == 403 and r.json()["error"]["code"] == "off_shift"
    assert c.post(f"/api/counselor/cases/{case_id}/summary-draft", headers=ha).status_code == 403
    assert c.transport.calls == []  # nothing sent to the provider


def test_no_patient_endpoint_ever_returns_the_draft(make_client):
    c = make_client(ok(CANARY))
    ha, hb, hc, case_id = _setup(c)
    assert c.post(f"/api/counselor/cases/{case_id}/summary-draft", headers=hc).json()["draft"] == CANARY
    for h in (ha, hb):
        for path in ("/api/me/vault", "/api/me/messages", "/api/me/home", "/api/me/activity", "/api/me/notifications",
                     "/api/me/care-plan", "/api/consents", "/api/loop/V3"):
            assert "Zephyr-marker" not in c.get(path, headers=h).text, path
    case = c.get(f"/api/counselor/cases/{case_id}", headers=hc).text
    assert "Zephyr-marker" not in case  # never stored on the case
    assert "Zephyr-marker" not in json.dumps(c.rt.audit.events())
