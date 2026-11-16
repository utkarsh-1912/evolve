"""Black-box API isolation tests against contracts/api.md v1.0.0 (R-EVAL-2, P-01, P-06, P-07, P-10, P-14).

Runs the real app via FastAPI TestClient; nothing in the app is mocked (AGENTS.md §5). Skips only if
services/api/evolve_api is not built yet. Expected values come from contracts + an independent
re-derivation of visibility/forbidden terms (tests/_support/qa_support.py), not from app internals.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "_support"))
import qa_support as qs  # noqa: E402

qs.add_path("evolve_api")
try:
    from evolve_api.main import app  # noqa: E402
except ModuleNotFoundError as e:  # only "not built yet" is a skip; a broken import inside the app is a failure
    if e.name and e.name.split(".")[0] == "evolve_api":
        pytest.skip(f"services/api/evolve_api not built yet (agent-runtime TASK-P2-AR): {e}", allow_module_level=True)
    raise

from fastapi.testclient import TestClient  # noqa: E402

PIDS = [f"{v}{r}" for v in qs.VIGNETTES for r in "AB"]
CANARY_A, CANARY_B = "ZZZ9", "QQQ7"
DIGEST_INDEX = {r["digest"]: r for v in qs.VIGNETTES for r in qs.locked_records(v)}


@pytest.fixture()
def client():
    c = TestClient(app)
    r = c.post("/api/demo/reset")
    assert r.status_code in (200, 204), r.text
    return c


def login(client, pid: str) -> dict:
    r = client.post("/api/session", json={"partner_id": pid})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["partner_id"] == pid
    return {"Authorization": f"Bearer {body['token']}"}


def counselor(client) -> dict:
    r = client.post("/api/session", json={"role": "counselor"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def other(pid: str) -> str:
    return pid[:2] + ("B" if pid[2] == "A" else "A")


def consent(client, h, pid) -> dict:
    r = client.post("/api/consents", json={"counterpart": other(pid)}, headers=h)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["status"] == "active" and body["patient"] == pid and body["counterpart"] == other(pid)
    return body


def compat(client, h, vid):
    return client.post(f"/api/couples/{vid}/compatibility", headers=h)


def text_of(resp) -> str:
    try:
        return json.dumps(resp.json(), ensure_ascii=False)
    except ValueError:
        return resp.text


def assert_no_leak(pid: str, blob: str, where: str):
    hits = qs.term_hits(blob, qs.forbidden_terms_for(pid))
    assert not hits, f"P-06 LEAK to {pid} via {where}: {hits}"


def full_couple(client, vid):
    ha, hb = login(client, vid + "A"), login(client, vid + "B")
    consent(client, ha, vid + "A")
    consent(client, hb, vid + "B")
    return ha, hb


# ------------------------------------------------------------------ session / scopes (P-10)
def test_session_scopes_are_granular_and_short_lived(client):
    r = client.post("/api/session", json={"partner_id": "V1A"})
    body = r.json()
    assert body["expires_in"] <= 3600
    assert body["scopes"] and all("*" not in s for s in body["scopes"])
    rc = client.post("/api/session", json={"role": "counselor"}).json()
    assert all("*" not in s for s in rc["scopes"]) and all(s.startswith("user/") for s in rc["scopes"])


def test_requests_without_token_are_rejected(client):
    for method, path in [("get", "/api/me/vault"), ("get", "/api/me/messages"), ("post", "/api/couples/V1/compatibility"),
                         ("get", "/api/counselor/queue")]:
        r = getattr(client, method)(path)
        assert r.status_code in (401, 403), (path, r.status_code)


# ------------------------------------------------------------------ dual consent (P-07)
def test_compatibility_refused_without_dual_consent(client):
    ha, hb = login(client, "V4A"), login(client, "V4B")
    r = compat(client, ha, "V4")
    assert r.status_code == 409, r.text
    assert set(r.json()) == {"error"} and {"code", "message"} <= set(r.json()["error"])
    consent(client, ha, "V4A")
    for h in (ha, hb):
        r = compat(client, h, "V4")
        assert r.status_code == 409, r.text  # one consent is not enough
        assert_no_leak("V4B", text_of(r), "409 body")
        assert_no_leak("V4A", text_of(r), "409 body")
    consent(client, hb, "V4B")
    assert compat(client, ha, "V4").status_code == 200


# ------------------------------------------------------------------ cross-partner access (403)
def test_partner_b_cannot_read_partner_a_vault(client):
    ha, hb = full_couple(client, "V4")
    assert compat(client, ha, "V4").status_code == 200
    own = client.get("/api/me/vault", headers=hb)
    assert own.status_code == 200
    assert_no_leak("V4B", text_of(own), "/me/vault")
    # attempts to address A's vault from B's token: must be 403, or ignored (B's own data only)
    for kw in ({"params": {"partner_id": "V4A"}}, {"headers": {**hb, "X-Partner-Id": "V4A"}}):
        r = client.get("/api/me/vault", **({"headers": hb} | kw))
        assert r.status_code in (200, 403), r.status_code
        assert_no_leak("V4B", text_of(r), f"/me/vault {kw}")
    # token for A is not usable to impersonate: B's token + A's partner_id in body
    r = client.post("/api/consents", json={"counterpart": "V4B", "patient": "V4A"}, headers=hb)
    assert r.status_code in (400, 403, 409, 422) or r.json().get("patient") == "V4B"


def test_cross_scope_requests_are_403(client):
    ha, hb = login(client, "V4A"), login(client, "V4B")
    cid = consent(client, ha, "V4A")["id"]
    consent(client, hb, "V4B")
    assert client.delete(f"/api/consents/{cid}", headers=hb).status_code in (403, 404)  # B cannot revoke A's consent
    assert compat(client, hb, "V1").status_code == 403  # not B's couple
    assert client.get("/api/loop/V1", headers=hb).status_code == 403
    assert client.get("/api/counselor/queue", headers=hb).status_code == 403
    assert client.post("/api/loop/V4/advance", json={"to": "HumanClosure"}, headers=hb).status_code == 403


# ------------------------------------------------------------------ revocation (P-07, R-PRIV-2)
def test_revocation_purges_workspace_and_blocks_compatibility(client):
    ha, hb = login(client, "V1A"), login(client, "V1B")
    ca = consent(client, ha, "V1A")
    consent(client, hb, "V1B")
    assert compat(client, ha, "V1").status_code == 200
    t0 = time.monotonic()
    r = client.delete(f"/api/consents/{ca['id']}", headers=ha)
    assert r.status_code in (200, 204), r.text
    if r.status_code == 200 and r.content:
        assert r.json().get("status") != "active"
    for h in (ha, hb):
        assert compat(client, h, "V1").status_code == 409
    assert time.monotonic() - t0 <= 5.0  # P-07: purge <= 5 s


# ------------------------------------------------------------------ V4 APSI (R-PRIV-1)
def test_v4_compatibility_response_has_no_gene_identifiers(client):
    ha, hb = full_couple(client, "V4")
    for h in (ha, hb):
        r = compat(client, h, "V4")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["apsi"]["status"] == "ok" and body["apsi"]["compatible"] is True
        assert body["apsi"]["shared_hgnc_ids"] == []
        assert all(rec["audience"] == "couple" for rec in body["records"]) and body["records"] == []
        blob = text_of(r)
        terms = qs.partner_terms(qs.vignette("V4")["partners"][0]) + qs.partner_terms(qs.vignette("V4")["partners"][1])
        assert not qs.term_hits(blob, terms), qs.term_hits(blob, terms)
        assert not re.search(r"HGNC:\s*\d+", blob)
        assert not qs.HGVS_RX.search(blob), qs.HGVS_RX.search(blob)


# ------------------------------------------------------------------ canary / metamorphic (docs/04 §3.7)
def test_canary_isolation_interleaved_sessions(client):
    """Interleave both partners of every vignette; canaries typed by one partner and the other partner's
    private genes must never reach the other (P-06, P-08)."""
    seen: dict[str, list[str]] = {p: [] for p in PIDS}
    for vid in qs.VIGNETTES:
        a, b = vid + "A", vid + "B"
        ha, hb = login(client, a), login(client, b)
        hdr = {a: ha, b: hb}
        steps = [
            (a, "post", "/api/demo/gate-probe", {"recipient_partner_id": a, "draft": f"note {CANARY_A}", "lang": "en"}),
            (b, "get", "/api/me/vault", None),
            (a, "post", "/api/teachback", {"answers": [f"{CANARY_A} is my gene"]}),
            (b, "post", "/api/teachback", {"answers": [f"{CANARY_B} is my gene"]}),
            (a, "post", "/api/consents", {"counterpart": b}),
            (b, "get", "/api/me/messages", None),
            (b, "post", "/api/consents", {"counterpart": a}),
            (a, "post", f"/api/couples/{vid}/compatibility", None),
            (b, "get", "/api/me/messages", None),
            (a, "get", "/api/me/messages", None),
            (b, "post", f"/api/couples/{vid}/compatibility", None),
            (a, "get", "/api/me/vault", None),
            (b, "get", "/api/me/vault", None),
            (a, "get", f"/api/loop/{vid}", None),
            (b, "get", f"/api/loop/{vid}", None),
        ]
        for who, m, path, body in steps:
            r = getattr(client, m)(path, headers=hdr[who], **({"json": body} if body is not None else {}))
            assert r.status_code < 500, (who, path, r.status_code, r.text[:200])
            seen[who].append(f"{m.upper()} {path} -> {text_of(r)}")
    for pid, blobs in seen.items():
        for blob in blobs:
            assert_no_leak(pid, blob, blob[:60])
            foreign = CANARY_B if pid.endswith("A") else CANARY_A
            assert foreign not in blob, f"canary {foreign} reached {pid}: {blob[:120]}"


# ------------------------------------------------------------------ P-01 independent re-check
def _all_messages(client) -> list[tuple[str, dict]]:
    out = []
    for vid in qs.VIGNETTES:
        ha, hb = full_couple(client, vid)
        r = compat(client, ha, vid)
        assert r.status_code == 200, (vid, r.text)
        out += [("compat:" + vid + "A", m) for m in r.json()["messages"]]
        for pid, h in ((vid + "A", ha), (vid + "B", hb)):
            rm = client.get("/api/me/messages", headers=h)
            assert rm.status_code == 200
            msgs = rm.json()
            assert all(m["to"] == pid for m in msgs), f"/me/messages for {pid} returned someone else's message"
            out += [(pid, m) for m in msgs]
    return out


def test_every_number_in_every_message_is_in_its_locked_records(client):
    msgs = _all_messages(client)
    assert msgs, "no messages produced for V1-V5"
    problems = []
    for src, m in msgs:
        recs = []
        for d in m.get("locked_digests") or []:
            if d not in DIGEST_INDEX:
                problems.append((src, m["id"], f"unknown digest {d[:12]}"))
            else:
                recs.append(DIGEST_INDEX[d])
        allowed = qs.allowed_numbers(recs)
        bad = [n for n in qs.numbers_in(qs.strip_fixed_phrases(m["text"])) if n not in allowed]
        if bad:
            problems.append((src, m["id"], f"numbers not in locked records: {bad}"))
        if m.get("simulated") is not True:
            problems.append((src, m["id"], "simulated flag missing"))
        if not (m.get("gate") or {}).get("passed"):
            problems.append((src, m["id"], "delivered message without gate.passed"))
        if set((m.get("gate") or {}).get("rules") or []) != {"numeric", "leakage", "nondirective", "uae_law"}:
            problems.append((src, m["id"], f"gate rules {m.get('gate')}"))
        # every record a message cites must be visible to its addressee (P-06)
        vis = {r["digest"] for r in qs.visible_records(m["to"])} if m["to"] in PIDS else set()
        for d in m.get("locked_digests") or []:
            if d in DIGEST_INDEX and d not in vis:
                problems.append((src, m["id"], f"cites record not visible to {m['to']} ({DIGEST_INDEX[d]['audience']})"))
    assert not problems, problems


def test_messages_never_leak_to_their_addressee(client):
    for src, m in _all_messages(client):
        if m["to"] in PIDS:
            assert_no_leak(m["to"], m["text"], f"message {m['id']} ({src})")


def test_result_messages_carry_judicial_statement(client):
    """P-14: result screens state the health certificate is issued regardless of the genetic result."""
    missing = []
    for src, m in _all_messages(client):
        if m["kind"] != "result":
            continue
        t = m["text"].lower()
        ok = ("regardless" in t and "certificate" in t) if m["lang"] == "en" else ("بغض النظر" in m["text"])
        if not ok:
            missing.append((src, m["id"], m["lang"]))
    assert not missing, missing


def test_v3_carrier_gets_locked_numbers_noncarrier_gets_no_gene(client):
    ha, hb = full_couple(client, "V3")
    assert compat(client, ha, "V3").status_code == 200
    a_text = " ".join(m["text"] for m in client.get("/api/me/messages", headers=ha).json())
    b_text = " ".join(m["text"] for m in client.get("/api/me/messages", headers=hb).json())
    assert "1 in 321" in a_text and "1 in 3,800" in a_text
    assert_no_leak("V3B", b_text, "V3B messages")


# ------------------------------------------------------------------ guardrail feed + probe
def test_guardrail_events_carry_no_text_or_genes(client):
    full_couple(client, "V3")
    client.post("/api/demo/gate-probe", json={"recipient_partner_id": "V3B", "draft": "Your partner carries SMN1.", "lang": "en"})
    r = client.get("/api/guardrail/events")
    assert r.status_code == 200
    events = r.json()
    assert events, "blocked probe produced no guardrail event"
    for e in events:
        assert set(e) <= {"ts", "rule", "outcome", "message_id"}, set(e)
        assert e["outcome"] in ("blocked", "rewritten", "escalated", "passed")
    blob = text_of(r)
    assert "SMN1" not in blob and not qs.HGVS_RX.search(blob)


@pytest.mark.parametrize("pid,draft,rule", [
    ("V3B", "Your partner carries SMN1.", "leakage"),
    ("V3A", "Your chance of an affected child is about 1 in 50.", "numeric_drift"),
    ("V1A", "You should not marry him.", "directive"),
    ("V1A", "You could consider using donor eggs.", "uae_law"),
])
def test_gate_probe_blocks(client, pid, draft, rule):
    r = client.post("/api/demo/gate-probe", json={"recipient_partner_id": pid, "draft": draft, "lang": "en"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["passed"] is False and rule in {v["rule"] for v in body["violations"]}
