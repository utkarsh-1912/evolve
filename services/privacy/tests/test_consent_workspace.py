"""docs/04 §3 items 4, 5 (R-PRIV-2, P-07, P-08)."""
from __future__ import annotations

import time
from datetime import timedelta

import jsonschema
import pytest

from privacy import apsi
from privacy._common import utcnow
from privacy.consent import CONSENT_SCHEMA, WorkspaceError


@pytest.fixture
def spy(monkeypatch):
    calls = []
    real = apsi.execute_psi

    def wrapper(*a):
        calls.append(a)
        return real(*a)

    monkeypatch.setattr(apsi, "execute_psi", wrapper)
    return calls


@pytest.fixture
def sets(authority):
    return lambda: (authority.sign_carrier_set("V4A", [6998, 4284]), authority.sign_carrier_set("V4B", [34]))


def test_consent_matches_schema_and_verifies(consents):
    c = consents.create("V4A", "V4B")
    jsonschema.validate(c, CONSENT_SCHEMA)
    assert consents.check(c) is None
    assert consents.check({**c, "counterpart": "V4C"}) == "bad_signature"


def _cases(consents):
    now = utcnow()
    a, b = consents.create("V4A", "V4B"), consents.create("V4B", "V4A")
    expired = consents.create("V4A", "V4B", start=now - timedelta(days=10), end=now - timedelta(days=1))
    future = consents.create("V4A", "V4B", start=now + timedelta(days=1))
    proposed = consents.create("V4A", "V4B", status="proposed")
    revoked = consents.create("V4A", "V4B")
    consents.revoke(revoked)
    stranger = consents.create("V4A", "V4Z")
    yield "missing A", None, b
    yield "missing B", a, None
    yield "missing both", None, None
    yield "expired", expired, b
    yield "not yet started", future, b
    yield "not active", proposed, b
    yield "revoked (stale active copy replayed)", revoked, b
    yield "not mutual", stranger, b
    yield "same consent twice", a, a
    yield "forged consent", {**a, "signature": "x"}, b


def test_missing_expired_revoked_consent_never_invokes_psi(service, consents, sets, spy):
    for label, ca, cb in _cases(consents):
        sa, sb = sets()
        res = service.run(ca, cb, sa, sb)
        assert res["status"] == "refused_no_consent", label
        assert res["compatible"] is None and res["shared_hgnc_ids"] == [], label
    assert spy == []
    sa, sb = sets()  # control: a valid pair does invoke it (spy is wired correctly)
    assert service.run(consents.create("V4A", "V4B"), consents.create("V4B", "V4A"), sa, sb)["status"] == "ok"
    assert len(spy) == 1


def test_revocation_kills_token_and_purges_within_5s(service, consents, couple, sets, audit):
    ca, cb = couple
    sa, sb = sets()
    res = service.run(ca, cb, sa, sb)
    token = consents.workspaces.open(res)
    assert consents.workspaces.read(token)["compatible"] is True

    t0 = time.perf_counter()
    revoked = consents.revoke(cb)
    with pytest.raises(WorkspaceError):
        consents.workspaces.read(token)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0
    assert len(consents.workspaces) == 0
    assert revoked["status"] == "inactive" and consents.check(revoked) == "revoked"
    sa, sb = sets()
    assert service.run(ca, cb, sa, sb)["status"] == "refused_no_consent"
    actions = [e["action"] for e in audit.events()]
    assert "consent.revoke" in actions and actions.count("workspace.read") == 2


def test_workspace_holds_only_ok_apsi_result(service, consents, sets):
    sa, sb = sets()
    refused = service.run(None, None, sa, sb)
    with pytest.raises(WorkspaceError):
        consents.workspaces.open(refused)
    with pytest.raises(jsonschema.ValidationError):
        consents.workspaces.open({**refused, "status": "ok", "partner_a_genes": [6998]})
