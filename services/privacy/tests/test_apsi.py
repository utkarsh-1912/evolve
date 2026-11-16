"""docs/04 §3 items 1, 2, 3, 6 + vignettes V1/V4 (R-PRIV-1, P-06, P-09)."""
from __future__ import annotations

from dataclasses import replace

import jsonschema
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from privacy import apsi
from privacy._common import hgnc_universe
from privacy.apsi import P, Q, Message, PsiParty, ReplayError, execute_psi, hash_to_group, in_group
from privacy.authority import Authority
from privacy.consent import APSI_SCHEMA

UNIVERSE = sorted(hgnc_universe())


def test_group_parameters_and_hash_to_group(authority):
    assert P.bit_length() == 2048 and P % 4 == 3
    h = hash_to_group(authority.sign_element(4827))
    assert in_group(h)
    assert pow(h, Q, P) == 1  # really in the order-q subgroup (one full check)
    assert not in_group(P - 1) and not in_group(1) and not in_group(0)


def test_v4_disjoint_is_compatible_and_nothing_else(service, authority, couple):
    ca, cb = couple
    sa = authority.sign_carrier_set("V4A", [6998, 4284])
    sb = authority.sign_carrier_set("V4B", [34])
    res = service.run(ca, cb, sa, sb)
    jsonschema.validate(res, APSI_SCHEMA)
    assert res["status"] == "ok" and res["compatible"] is True and res["shared_hgnc_ids"] == []
    assert set(res) == {"contract_version", "status", "compatible", "shared_hgnc_ids", "consent_ids", "audit_event_id"}


def test_v1_overlap_reveals_exactly_the_intersection(service, authority, consents):
    ca, cb = consents.create("V1A", "V1B"), consents.create("V1B", "V1A")
    res = service.run(ca, cb, authority.sign_carrier_set("V1A", [4827]), authority.sign_carrier_set("V1B", [4827]))
    jsonschema.validate(res, APSI_SCHEMA)
    assert res["status"] == "ok" and res["compatible"] is False and res["shared_hgnc_ids"] == [4827]


def test_partial_overlap_only_intersection(service, authority, couple):
    ca, cb = couple
    res = service.run(ca, cb, authority.sign_carrier_set("V4A", [2600, 4827, 6998]),
                      authority.sign_carrier_set("V4B", [4827, 34, 11117]))
    assert res["shared_hgnc_ids"] == [4827] and res["compatible"] is False


def test_module_level_run_uses_defaults():
    from privacy.authority import sign_carrier_set
    from privacy.consent import default_consent_service

    cs = default_consent_service()
    res = apsi.run(cs.create("V4A", "V4B"), cs.create("V4B", "V4A"),
                   sign_carrier_set("V4A", [6998, 4284]), sign_carrier_set("V4B", [34]))
    assert res["status"] == "ok" and res["compatible"] is True and res["shared_hgnc_ids"] == []


@settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(a=st.sets(st.sampled_from(UNIVERSE), max_size=4), b=st.sets(st.sampled_from(UNIVERSE), max_size=4))
def test_property_intersection_exact(authority, a, b):
    out = execute_psi(authority.sign_carrier_set("V4A", a), authority.sign_carrier_set("V4B", b))
    assert out.shared == a & b


def test_bobs_view_reveals_no_non_shared_element(authority):
    """Bob's-view transcript test (docs/04 §3.1).

    Everything Bob receives is (i) X_A = {h(s_i)^a}: Alice's hashed signatures raised to her secret
    exponent a, and (ii) Z_B = {h(t_j)^(ab)}: his own elements blinded by both exponents. Under the
    Decisional Diffie-Hellman assumption in the prime-order QR subgroup of the RFC 3526 group 14
    prime (short-exponent DDH variant for the 320-bit exponents), modelling h as a random oracle,
    the tuple (h(s), h(s)^a, h(t), h(t)^a) is indistinguishable from (h(s), R, h(t), h(t)^a) for a
    random group element R. Hence for every s_i not in Bob's set, h(s_i)^a is pseudorandom to Bob:
    he cannot test a candidate gene against it without a, and he cannot compute h(s_i) for genes he
    was not certified for because s_i is an RSA-FDH signature only the authority can produce. The
    only elements he can link are those whose double blinding equals one of his own Z values, i.e.
    the intersection. He also learns |A| (stated in THREAT_MODEL.md).

    This test checks the concrete, mechanical part of that argument: no raw HGNC ID, raw signature,
    unblinded hash or FDH value of Alice's non-shared genes appears in any message delivered to Bob,
    payloads are group elements only, and only one double-blinded value links across the two sides.
    """
    shared = 4827
    alice_only = [6998, 4284, 2600]
    sa = authority.sign_carrier_set("V4A", alice_only + [shared])
    sb = authority.sign_carrier_set("V4B", [shared, 34])
    out = execute_psi(sa, sb)
    assert out.shared == {shared}

    bob_rx = out.received_by("B")
    assert [m.kind for m in bob_rx] == ["blinded_set", "reblinded"]
    sigs = dict(sa.elements)
    forbidden = set()
    for h in alice_only:
        forbidden |= {h, sigs[h], hash_to_group(sigs[h]), sigs[h] % P}
    received = [x for m in bob_rx for x in m.payload]
    assert received and all(in_group(x) for x in received)
    assert not forbidden & set(received)
    for m in bob_rx:  # opaque metadata + group elements only; no id / gene fields
        assert set(vars(m)) == {"session_id", "seq", "sender", "recipient", "kind", "payload"}
    z_a = next(m for m in out.transcript if m.recipient == "A" and m.kind == "reblinded").payload
    z_b = next(m for m in bob_rx if m.kind == "reblinded").payload
    assert len(set(z_a) & set(z_b)) == 1


def test_blinding_is_fresh_per_session(authority):
    sa = authority.sign_carrier_set("V4A", [6998])
    sb = authority.sign_carrier_set("V4B", [34])
    x1 = execute_psi(sa, sb).received_by("B")[0].payload
    x2 = execute_psi(sa, sb).received_by("B")[0].payload
    assert set(x1).isdisjoint(x2)  # same gene, unlinkable across sessions


# ---- forged sets (docs/04 §3.3, P-09) ---------------------------------------------------------

def _forgeries(authority, rogue):
    good = authority.sign_carrier_set("V4A", [6998, 4284])
    other = authority.sign_carrier_set("V4X", [4827])
    (h0, s0), rest = good.elements[0], good.elements[1:]
    yield "tampered element signature", replace(good, elements=((h0, s0 ^ 1),) + rest)
    yield "client-fabricated element", replace(good, elements=good.elements + ((4827, 12345),))
    yield "element spliced from another set", replace(good, elements=good.elements + other.elements)
    yield "envelope partner rebind", replace(good, partner_id="V4C")
    yield "expiry extended", replace(good, expiry="2999-01-01T00:00:00.000000Z")
    yield "rogue authority", rogue.sign_carrier_set("V4A", [6998])


def test_forged_sets_rejected_and_psi_not_invoked(service, authority, consents, monkeypatch):
    calls = []
    monkeypatch.setattr(apsi, "execute_psi", lambda *a: calls.append(a))
    rogue = Authority(key_size=1024)
    sb = authority.sign_carrier_set("V4B", [34])
    n = 0
    for label, forged in _forgeries(authority, rogue):
        n += 1
        ca, cb = consents.create("V4A", "V4B"), consents.create("V4B", "V4A")
        res = service.run(ca, cb, forged, sb)
        assert res["status"] == "refused_invalid_signature", label
        assert res["compatible"] is None and res["shared_hgnc_ids"] == [], label
    assert n == 6 and calls == []


def test_unsigned_set_rejected(service, couple, authority):
    ca, cb = couple
    res = service.run(ca, cb, {"partner_id": "V4A", "elements": [[6998, 1]]}, authority.sign_carrier_set("V4B", [34]))
    assert res["status"] == "refused_invalid_signature"


def test_set_must_belong_to_consenting_partner(service, authority, couple):
    ca, cb = couple
    res = service.run(ca, cb, authority.sign_carrier_set("V4B", [6998]), authority.sign_carrier_set("V4A", [34]))
    assert res["status"] == "refused_invalid_signature"


def test_authority_refuses_ids_outside_panel(authority):
    with pytest.raises(ValueError):
        authority.sign_carrier_set("V4A", [999999])


# ---- replay (docs/04 §3.6) --------------------------------------------------------------------

def test_replayed_signed_set_blob_rejected(service, authority, consents):
    ca, cb = consents.create("V4A", "V4B"), consents.create("V4B", "V4A")
    sa, sb = authority.sign_carrier_set("V4A", [6998]), authority.sign_carrier_set("V4B", [34])
    assert service.run(ca, cb, sa, sb)["status"] == "ok"
    again = service.run(ca, cb, sa, sb)
    assert again["status"] == "refused_invalid_signature" and again["compatible"] is None


def test_replayed_protocol_messages_rejected(authority):
    sa, sb = authority.sign_carrier_set("V4A", [6998]), authority.sign_carrier_set("V4B", [34])
    old = execute_psi(sa, sb).transcript
    bob = PsiParty("B", "A", sb.elements, "fresh-session", initiator=False)
    with pytest.raises(ReplayError):  # cross-session replay
        bob.receive(old[0])
    alice = PsiParty("A", "B", sa.elements, "s1", initiator=True)
    bob = PsiParty("B", "A", sb.elements, "s1", initiator=False)
    m1 = alice.start()[0]
    bob.receive(m1)
    with pytest.raises(ReplayError):  # in-session duplicate delivery
        bob.receive(m1)


def test_out_of_group_element_rejected(authority):
    sb = authority.sign_carrier_set("V4B", [34])
    bob = PsiParty("B", "A", sb.elements, "s", initiator=False)
    with pytest.raises(apsi.ProtocolError):
        bob.receive(Message("s", 0, "A", "B", "blinded_set", (P - 1,)))
