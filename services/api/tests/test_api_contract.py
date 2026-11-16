"""API contract tests (contracts/api.md) through TestClient. Real runtime, risk_engine, privacy and gate."""
import json
import re

from conftest import consent_both, login

GENES = ["CYP21A2", "HBB", "MEFV", "ABCA4", "HBA2", "SMN1", "DONSON", "ALDH3A2", "TPO", "CYP1B1", "GJB2"]
NUM = re.compile(r"(?<![A-Za-z0-9.,:])\d[\d,]*(?:\.\d+)?")


def test_session_scopes_and_simulated(client):
    r = client.post("/api/session", json={"partner_id": "V1A"}).json()
    assert r["scopes"] == ["patient/Observation.rs", "patient/DiagnosticReport.r", "patient/Consent.cru"]
    assert r["expires_in"] <= 3600 and r["simulated"] is True
    c = client.post("/api/session", json={"role": "counselor"}).json()
    assert c["scopes"] == ["user/DiagnosticReport.rs", "user/Task.cru"]
    assert client.post("/api/session", json={"partner_id": "NOPE"}).status_code == 404


def test_vignettes_have_no_genotype(client):
    v = client.get("/api/demo/vignettes").json()
    assert [x["couple_id"] for x in v] == ["V1", "V2", "V3", "V4", "V5"]
    assert not any(g in json.dumps(v) for g in GENES)


def test_v4_end_to_end(client):
    ha, hb, _, _ = consent_both(client, "V4")
    r = client.post("/api/couples/V4/compatibility", headers=ha)
    assert r.status_code == 200
    body = r.json()
    assert body["apsi"]["compatible"] is True and body["records"] == []
    dump = json.dumps(body)
    assert not any(g in dump for g in GENES) and "HGNC:" not in dump and not re.search(r"\b[cp]\.\(?[A-Z0-9]", dump)
    assert body["messages"] and all(m["to"] == "V4A" for m in body["messages"])
    va, vb = client.get("/api/me/vault", headers=ha).json(), client.get("/api/me/vault", headers=hb).json()
    assert {c["gene"] for c in va["calls"]} == {"MEFV", "GJB2"} and "ABCA4" not in json.dumps(va)
    assert {c["gene"] for c in vb["calls"]} == {"ABCA4"} and "MEFV" not in json.dumps(vb)


def test_v1_and_v3_messages(client):
    ha, hb, _, _ = consent_both(client, "V1")
    body = client.post("/api/couples/V1/compatibility", headers=hb).json()
    assert body["apsi"]["shared_hgnc_ids"] == [4827]
    t = " ".join(m["text"] for m in body["messages"])
    assert "HBB" in t and "1 in 4" in t and "regardless" in t
    ha3, hb3, _, _ = consent_both(client, "V3")
    client.post("/api/couples/V3/compatibility", headers=ha3)
    a = " ".join(m["text"] for m in client.get("/api/me/messages", headers=ha3).json())
    b = " ".join(m["text"] for m in client.get("/api/me/messages", headers=hb3).json())
    assert "1 in 321" in a and "1 in 3,800" in a
    assert not any(g in b for g in GENES)
    hc = login(client, role="counselor")
    client.post("/api/counselor/shift", json={"on": True}, headers=hc)  # DECISIONS #40: queue is shift-gated
    q = client.get("/api/counselor/queue", headers=hc).json()
    assert {(c["couple_id"], c["trigger"]) for c in q} == {("V1", "a"), ("V3", "b")}
    assert set(q[0]) == {"case_id", "couple_id", "trigger", "created_at"}
    brief = client.get(f"/api/counselor/briefs/{q[0]['case_id']}", headers=hc).json()
    assert {"pedigree", "variant_summary", "pending_tasks", "couple_questions"} <= set(brief)


def test_every_message_number_is_in_its_locked_records(client):
    for cid in ("V1", "V2", "V3", "V4", "V5"):
        ha, hb, _, _ = consent_both(client, cid)
        client.post(f"/api/couples/{cid}/compatibility", headers=ha)
        by_digest = {r["digest"]: r for r in client.rt.counselor_records[cid]}
        for h in (ha, hb):
            for m in client.get("/api/me/messages", headers=h).json():
                assert m["gate"]["passed"] is True and m["simulated"] is True
                allowed = " ".join(json.dumps(by_digest[d]) for d in m["locked_digests"])
                for n in NUM.findall(m["text"].replace("48 hours", "")):
                    assert n in allowed or n == "1", (cid, n)


def test_cross_partner_access_forbidden(client):
    ha, hb = login(client, "V1A"), login(client, "V4B")
    assert client.get("/api/me/vault?partner_id=V1A", headers=hb).status_code == 403
    assert client.get("/api/me/vault", headers={**hb, "X-Partner-Id": "V1A"}).status_code == 403
    assert client.post("/api/couples/V1/compatibility", headers=hb).status_code == 403
    assert client.get("/api/loop/V1", headers=hb).status_code == 403
    assert client.post("/api/consents", json={"counterpart": "V1A"}, headers=hb).status_code == 403
    assert client.get("/api/counselor/queue", headers=ha).status_code == 403
    assert client.get("/api/me/vault").status_code == 401
    r = client.get("/api/me/vault", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401 and set(r.json()["error"]) == {"code", "message"}


def test_every_request_audited(client):
    h = login(client, "V2A")
    before = len(client.rt.audit)
    client.get("/api/me/vault", headers=h)
    client.get("/api/me/messages", headers=h)
    client.get("/api/me/vault?partner_id=V2B", headers=h)
    ev = client.rt.audit.events()[before:]
    assert [e["action"] for e in ev] == ["api.read"] * 3
    assert [e["outcome"] for e in ev] == ["success", "success", "denied"]
    assert client.rt.audit.verify()


def test_consent_409_and_revocation(client):
    ha, hb = login(client, "V1A"), login(client, "V1B")
    assert client.post("/api/couples/V1/compatibility", headers=ha).status_code == 409
    ca = client.post("/api/consents", json={"counterpart": "V1B"}, headers=ha).json()
    assert ca["status"] == "active" and ca["resourceType"] == "Consent"
    assert client.post("/api/couples/V1/compatibility", headers=ha).status_code == 409
    client.post("/api/consents", json={"counterpart": "V1A"}, headers=hb)
    assert client.post("/api/couples/V1/compatibility", headers=ha).status_code == 200
    assert client.delete(f"/api/consents/{ca['id']}", headers=hb).status_code == 403
    assert client.delete(f"/api/consents/{ca['id']}", headers=ha).json()["status"] == "inactive"
    assert client.get("/api/me/messages", headers=hb).json() == []
    assert client.get("/api/me/vault", headers=hb).json()["records"] == []
    assert client.post("/api/couples/V1/compatibility", headers=hb).status_code == 409


def test_canary_isolation_via_api(client):
    call = {"hgvs_c": None, "hgvs_p": None, "refseq": None, "zygosity": "het", "classification": "P",
            "variant_type": "snv", "absent_gnomad": True, "absent_clinvar": True, "in_roh_gt_10mb": False}
    client.rt.add_couple({"couple_id": "VC", "relationship": {"type": "unrelated", "paths": []}, "partners": [
        {"partner_id": "VCA", "role": "A", "sex": "female", "age": 25, "bmi": 22.0,
         "calls": [{**call, "hgnc_id": 990009, "gene": "ZZZ9"}], "assays": {}},
        {"partner_id": "VCB", "role": "B", "sex": "male", "age": 27, "bmi": 24.0, "calls": [], "assays": {}}]})
    ha, hb = login(client, "VCA"), login(client, "VCB")
    seen = {"a": [], "b": []}
    seen["b"].append(client.get("/api/me/vault", headers=hb).text)
    client.post("/api/consents", json={"counterpart": "VCB"}, headers=ha)
    seen["b"].append(client.post("/api/consents", json={"counterpart": "VCA"}, headers=hb).text)
    seen["b"].append(client.post("/api/couples/VC/compatibility", headers=hb).text)
    for _ in range(2):
        seen["a"].append(client.get("/api/me/messages", headers=ha).text)
        seen["b"].append(client.get("/api/me/messages", headers=hb).text)
        seen["b"].append(client.get("/api/me/vault", headers=hb).text)
        seen["a"].append(client.get("/api/me/vault", headers=ha).text)
        seen["b"].append(client.get("/api/loop/VC", headers=hb).text)
    assert "ZZZ9" in " ".join(seen["a"])
    assert "ZZZ9" not in " ".join(seen["b"])
    assert "ZZZ9" not in client.get("/api/guardrail/events").text


def test_teachback_sure_loop_and_human_closure(client):
    ha, hb, _, _ = consent_both(client, "V1")
    client.post("/api/couples/V1/compatibility", headers=ha)
    assert client.post("/api/teachback", json={"answers": [False, True, True, True]}, headers=ha).json()["passed"] is True
    client.post("/api/teachback", json={"answers": [False, True, True, True]}, headers=hb)
    assert client.get("/api/loop/V1", headers=ha).json()["state"] == "ComprehensionConfirmed"
    assert client.post("/api/sure", json={"answers": [True, False, True, True]}, headers=hb).json() == {
        "score": 3, "escalated": True}
    assert client.post("/api/sure", json={"answers": [True]}, headers=hb).status_code == 422
    assert client.post("/api/loop/V1/advance", json={"to": "HumanClosure"}, headers=ha).status_code == 403
    hc = login(client, role="counselor")
    # DECISIONS #50: loop writes are shift-gated like the other counselor writes
    r = client.post("/api/loop/V1/advance", json={"to": "CounselingDone"}, headers=hc)
    assert r.status_code == 403 and r.json()["error"]["code"] == "off_shift"
    client.post("/api/counselor/shift", json={"on": True}, headers=hc)
    assert client.post("/api/loop/V1/advance", json={"to": "CounselingDone"}, headers=hc).json()["state"] == "CounselingDone"
    assert client.post("/api/loop/V1/advance", json={"to": "HumanClosure"}, headers=hc).json()["state"] == "HumanClosure"
    assert client.post("/api/loop/V1/advance", json={"to": "PatientNotified"}, headers=hc).status_code == 409


def test_gate_probe_and_events_carry_no_text(client):
    consent_both(client, "V3")
    r = client.post("/api/demo/gate-probe", json={"recipient_partner_id": "V3B", "lang": "en",
                                                  "draft": "Your partner carries SMN1, about 1 in 50."}).json()
    assert r["passed"] is False and {"leakage", "numeric_drift"} <= {v["rule"] for v in r["violations"]}
    assert "SMN1" not in json.dumps(r)
    ev = client.get("/api/guardrail/events").json()
    assert ev and all(set(e) == {"ts", "rule", "outcome", "message_id"} for e in ev)
    assert "SMN1" not in json.dumps(ev)


def test_gate_failure_delivers_nothing(client, monkeypatch):
    from runtime import bioethics

    def boom(*_a, **_k):
        raise RuntimeError("down")
    monkeypatch.setattr(bioethics, "check", boom)
    ha, hb, _, _ = consent_both(client, "V3")
    body = client.post("/api/couples/V3/compatibility", headers=ha).json()
    assert body["messages"] == []
    assert client.get("/api/me/messages", headers=ha).json() == []
    assert client.get("/api/me/messages", headers=hb).json() == []


def test_demo_reset(client):
    consent_both(client, "V1")
    r = client.post("/api/demo/reset").json()
    assert r["vignettes"] == 5 and r["cohort_couples"] >= 0
    assert client.rt.consents == {} and client.get("/api/guardrail/events").json() == []


def test_v1_1_bodies_consents_and_simulated_partner_consent(client):
    ha = login(client, "V3A")
    r = client.post("/api/demo/simulate-partner-consent", json={"couple_id": "V3"}).json()
    assert r["simulated"] is True and r["created"] == 2
    cons = client.get("/api/consents", headers=ha).json()
    assert len(cons) == 2 and {c["patient"] for c in cons} == {"V3A", "V3B"}
    assert client.get("/api/consents", headers=login(client, "V1A")).json() == []
    assert client.post("/api/couples/V3/compatibility", headers=ha).status_code == 200
    calls = client.get("/api/me/vault", headers=ha).json()["calls"]
    assert {"gene", "hgnc_id", "classification", "zygosity", "plain_en", "plain_ar", "confirmatory_recommended"} <= set(calls[0])
    assert client.post("/api/demo/simulate-partner-consent", json={"couple_id": "NOPE"}).status_code == 404
