"""Consent purposes (QUESTION-AR-3; DECISIONS #16, #40; R-PRIV-2, P-06, P-07)."""
from __future__ import annotations

import jsonschema
import pytest

from privacy import apsi
from privacy.consent import CONSENT_SCHEMA, DISCLOSE_PURPOSE, PURPOSE


@pytest.fixture
def spy(monkeypatch):
    calls = []
    monkeypatch.setattr(apsi, "execute_psi", lambda *a: calls.append(a))
    return calls


def test_default_is_apsi_purpose_without_scope_key(consents):
    c = consents.create("V2A", "V2B")
    assert c["purpose"] == PURPOSE and "scope" not in c  # original P1 record shape
    assert consents.check(c) is None and consents.check(c, purpose=PURPOSE) is None


def test_disclosure_consent_signed_with_scope(consents):
    c = consents.create("V2A", "V2B", purpose=DISCLOSE_PURPOSE, scope={"hgnc_id": 2600})
    jsonschema.validate(c, CONSENT_SCHEMA)
    assert c["purpose"] == DISCLOSE_PURPOSE and c["scope"] == {"hgnc_id": 2600}
    assert consents.check(c) is None
    assert consents.check(c, purpose=DISCLOSE_PURPOSE) is None
    assert consents.check(c, purpose=PURPOSE) == "wrong_purpose"


def test_scope_is_inside_the_signature(consents):
    c = consents.create("V2A", "V2B", purpose=DISCLOSE_PURPOSE, scope={"hgnc_id": 2600})
    assert consents.check({**c, "scope": {"hgnc_id": 11117}}) == "bad_signature"
    assert consents.check({k: v for k, v in c.items() if k != "scope"}) == "bad_signature"
    assert consents.check({**c, "purpose": PURPOSE}) == "bad_signature"
    a = consents.create("V2A", "V2B")
    assert consents.check({**a, "scope": {"hgnc_id": 2600}}) == "bad_signature"


@pytest.mark.parametrize("purpose,scope", [
    (DISCLOSE_PURPOSE, None),
    (DISCLOSE_PURPOSE, {}),
    (DISCLOSE_PURPOSE, {"hgnc_id": [2600, 11117]}),
    (DISCLOSE_PURPOSE, {"hgnc_id": 2600, "hgnc_id_2": 11117}),
    (DISCLOSE_PURPOSE, {"hgnc_id": "2600"}),
    (DISCLOSE_PURPOSE, {"hgnc_id": True}),
    (DISCLOSE_PURPOSE, {"hgnc_id": 999999}),
    (PURPOSE, {"hgnc_id": 2600}),
    ("share-everything", None),
])
def test_invalid_purpose_scope_combinations_refused(consents, purpose, scope):
    with pytest.raises(ValueError):
        consents.create("V2A", "V2B", purpose=purpose, scope=scope)


def test_disclosure_consent_revocable(consents):
    c = consents.create("V2A", "V2B", purpose=DISCLOSE_PURPOSE, scope={"hgnc_id": 2600})
    revoked = consents.revoke(c)
    assert revoked["status"] == "inactive" and revoked["scope"] == {"hgnc_id": 2600}
    jsonschema.validate(revoked, CONSENT_SCHEMA)
    assert consents.verify_signature(revoked)
    assert consents.check(c) == "revoked" and consents.check(revoked) == "revoked"


@pytest.mark.parametrize("which", ["a", "b", "both"])
def test_apsi_refuses_disclosure_consents(service, consents, authority, spy, which):
    apsi_a, apsi_b = consents.create("V2A", "V2B"), consents.create("V2B", "V2A")
    disc_a = consents.create("V2A", "V2B", purpose=DISCLOSE_PURPOSE, scope={"hgnc_id": 2600})
    disc_b = consents.create("V2B", "V2A", purpose=DISCLOSE_PURPOSE, scope={"hgnc_id": 2600})
    ca = disc_a if which in ("a", "both") else apsi_a
    cb = disc_b if which in ("b", "both") else apsi_b
    res = service.run(ca, cb, authority.sign_carrier_set("V2A", [2600]), authority.sign_carrier_set("V2B", [2600]))
    assert res["status"] == "refused_no_consent" and res["compatible"] is None and res["shared_hgnc_ids"] == []
    assert spy == []


def test_audit_records_purpose_but_no_gene(consents, audit):
    consents.create("V2A", "V2B", purpose=DISCLOSE_PURPOSE, scope={"hgnc_id": 2600})
    ev = audit.events()[-1]
    assert ev["detail"] == {"status": "active", "purpose": DISCLOSE_PURPOSE}
    assert "2600" not in str(ev)
