"""docs/04 §3 items 8, 9, 10 + AuditEvent chain (R-PRIV-1/2/4, P-10, P-11, P-12)."""
from __future__ import annotations

import json
import logging
import pathlib
import re
from datetime import timedelta

import pytest
from hypothesis import given, settings, strategies as st

from privacy._common import hgnc_universe, utcnow
from privacy.audit import AuditLog
from privacy.cascade import TOKEN_KEYS, CascadeIssuer, CascadeTokenError, variant_digest, verify_token
from privacy.suppress import suppress

PANEL = json.loads((pathlib.Path(__file__).resolve().parents[3] / "contracts" / "gene_panel.json").read_text(encoding="utf-8"))
SYMBOLS = {g["symbol"] for g in PANEL["genes"]}
HGVS = re.compile(r"(c\.\d|p\.\(|g\.\d|[ACGT]>[ACGT])")
UNIVERSE = sorted(hgnc_universe())


# ---- audit -----------------------------------------------------------------------------------

def test_every_operation_audited_and_chain_verifies(service, consents, couple, authority, audit):
    ca, cb = couple
    res = service.run(ca, cb, authority.sign_carrier_set("V4A", [6998]), authority.sign_carrier_set("V4B", [34]))
    tok = consents.workspaces.open(res)
    consents.workspaces.read(tok)
    consents.revoke(ca)
    actions = [e["action"] for e in audit.events()]
    assert actions == ["consent.create", "consent.create", "apsi.run", "workspace.create",
                       "workspace.read", "consent.revoke"]
    assert res["audit_event_id"] == audit.events()[2]["id"]
    assert audit.verify()


def test_audit_tamper_detection(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(4):
        log.append("workspace.read", "success", entity=[f"ws-{i}"])
    assert log.verify() and AuditLog.verify_file(path)

    log._events[1]["outcome"] = "denied"  # in-memory edit
    assert not log.verify()

    lines = path.read_text(encoding="utf-8").splitlines()
    edited = json.loads(lines[2])
    edited["entity"] = ["ws-x"]
    path.write_text("\n".join(lines[:2] + [json.dumps(edited)] + lines[3:]), encoding="utf-8")
    assert not AuditLog.verify_file(path)  # file edit
    path.write_text("\n".join(lines[:1] + lines[2:]), encoding="utf-8")
    assert not AuditLog.verify_file(path)  # deletion
    path.write_text("\n".join([lines[1], lines[0]] + lines[2:]), encoding="utf-8")
    assert not AuditLog.verify_file(path)  # reorder
    path.write_text("\n".join(lines), encoding="utf-8")
    assert AuditLog.verify_file(path)      # control


def test_audit_returns_copies_and_rejects_genomic_detail():
    log = AuditLog()
    log.append("apsi.run", "success")
    log.events()[0]["outcome"] = "x"
    assert log.verify()
    with pytest.raises(ValueError):
        log.append("apsi.run", "success", detail={"genes": [6998]})


# ---- cascade token (docs/04 §3.8) ------------------------------------------------------------

def test_cascade_token_roundtrip_and_tamper():
    iss = CascadeIssuer()
    tok = iss.issue(2597, {"chrom": "chr2", "pos": 38071000, "ref": "c", "alt": "t"})  # synthetic coords
    assert set(tok) == TOKEN_KEYS
    assert tok["variant_digest"] == variant_digest({"chrom": "2", "pos": 38071000, "ref": "C", "alt": "T"})
    assert verify_token(tok, iss.public_key)["hgnc_id"] == 2597
    for bad in ({**tok, "hgnc_id": 2600}, {**tok, "patient": "V1A"}, {k: v for k, v in tok.items() if k != "expiry"}):
        with pytest.raises(CascadeTokenError):
            verify_token(bad, iss.public_key)
    with pytest.raises(CascadeTokenError):
        verify_token(tok, CascadeIssuer().public_key)
    with pytest.raises(CascadeTokenError):
        verify_token(tok, iss.public_key, now=utcnow() + timedelta(days=365))


@settings(max_examples=60, deadline=None)
@given(hgnc=st.sampled_from(UNIVERSE), variant=st.text(min_size=1, max_size=40).filter(lambda s: s.strip()),
       index_id=st.from_regex(r"V[1-5][AB]|SYN-P[0-9]{4}[AB]", fullmatch=True))
def test_cascade_token_has_no_index_identity_fuzz(hgnc, variant, index_id):
    tok = CascadeIssuer().issue(hgnc, variant)
    assert set(tok) == TOKEN_KEYS
    assert re.fullmatch(r"[0-9a-f]{64}", tok["variant_digest"])
    blob = json.dumps(tok)
    assert index_id not in blob  # the issuer API cannot even receive an identity
    norm = "".join(variant.split())
    if len(norm) >= 6:  # the raw variant is never carried, only its digest
        assert json.dumps(norm)[1:-1] not in blob.replace(tok["variant_digest"], "").replace(tok["signature"], "")


# ---- suppression (docs/04 §3.9) --------------------------------------------------------------

def test_small_cells_suppressed():
    assert suppress({"a": 0, "b": 9, "c": 10, "d": 250}) == {"a": None, "b": None, "c": 10, "d": 250}
    with pytest.raises(ValueError):
        suppress({"a": 3}, k=5)
    with pytest.raises(ValueError):
        suppress({"a": -1})


@given(st.dictionaries(st.text(max_size=5), st.integers(min_value=0, max_value=10_000)))
def test_suppression_property(counts):
    out = suppress(counts)
    assert all((v is None) == (counts[k] < 10) for k, v in out.items())


# ---- logs scan (docs/04 §3.10, P-12) ---------------------------------------------------------

def test_logs_and_audit_contain_no_gene_or_variant(service, consents, authority, audit, caplog):
    caplog.set_level(logging.DEBUG)
    ca, cb = consents.create("V1A", "V1B"), consents.create("V1B", "V1A")
    sa, sb = authority.sign_carrier_set("V1A", [4827, 2600]), authority.sign_carrier_set("V1B", [4827])
    res = service.run(ca, cb, sa, sb)
    consents.workspaces.read(consents.workspaces.open(res))
    service.run(None, cb, sa, sb)
    consents.revoke(ca)
    CascadeIssuer().issue(4827, "NM_000518.5:c.92+5G>C")
    with pytest.raises(ValueError):
        authority.sign_carrier_set("V1A", [999999])
    text = caplog.text + json.dumps(audit.events())
    assert caplog.records
    assert not any(re.search(rf"\b{re.escape(s)}\b", text) for s in SYMBOLS)
    assert not HGVS.search(text)
    assert not re.search(r"\b(4827|2600|999999)\b", text)
