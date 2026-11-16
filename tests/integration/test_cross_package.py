"""Cross-package checks (R-RISK-3, R-FHIR-1, R-PRIV-1; docs/04 §1 cohort sweep, P-06).

1. Independent math oracle over services/synth/out/cohort.json: re-implements docs/07 (Wright + Bayes) with
   exact Fractions and the set logic / routing of DECISIONS #11, #17-19 straight from the contracts. It does NOT
   import risk_engine internals; risk_engine is used only through its public `assess_couple`. 0 mismatches.
2. FHIR couple reports built from a real APSI run contain no non-shared partner gene.
"""
from __future__ import annotations

import json
import pathlib
import sys
from fractions import Fraction

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "_support"))
import qa_support as qs  # noqa: E402
from oracle import compare, o_discordant, o_one_in, o_sig, o_wright  # noqa: E402,F401

COHORT = qs.ROOT / "services" / "synth" / "out" / "cohort.json"
PLP = ("P", "LP")


# ------------------------------------------------------------------ tests
@pytest.fixture(scope="module")
def assess():
    qs.add_path("risk_engine")
    from risk_engine import assess_couple  # public API only
    return assess_couple


def test_oracle_reproduces_doc_golden_numbers():
    """Oracle self-check against docs/07 §3 before trusting it as a reference."""
    v2 = o_discordant(Fraction("0.106"), Fraction("0.92"), Fraction(0))
    assert o_one_in(v2["post"]) == "1 in 106" and o_one_in(v2["off"]) == "1 in 426"
    v2c = o_discordant(Fraction("0.106"), Fraction("0.99"), Fraction(0))
    assert o_one_in(v2c["post"]) == "1 in 844" and o_one_in(v2c["off"]) == "1 in 3,380"
    v3 = o_discordant(Fraction("0.013"), Fraction("0.92"), Fraction(1, 8))
    assert abs(float(v3["prior"]) - 0.13637) < 1e-5 and o_one_in(v3["post"]) == "1 in 80.2"
    assert o_one_in(v3["off"]) == "1 in 321"
    ref = o_discordant(Fraction("0.013"), Fraction("0.92"), Fraction(0))
    assert o_one_in(ref["off"]) == "1 in 3,800" and o_sig(v3["off"] / ref["off"], 2) == "12"
    assert o_wright([[2, 2, "0"], [2, 2, "0"]]) == (Fraction(1, 16), Fraction(1, 8))
    assert o_wright([[2, 2, "0"]] * 4) == (Fraction(1, 8), Fraction(1, 4))


@pytest.mark.parametrize("vid", qs.VIGNETTES)
def test_vignettes_match_oracle(assess, vid):
    c = qs.vignette(vid)
    assert compare(c, assess(c)) == []


def test_cohort_sweep_zero_mismatches(assess):
    if not COHORT.exists():
        pytest.skip("services/synth/out/cohort.json not generated")
    doc = json.loads(COHORT.read_text(encoding="utf-8"))
    assert doc["synthetic"] is True
    errs, n_records, n_numeric = [], 0, 0
    for c in doc["couples"]:
        recs = assess(c)
        n_records += len(recs)
        n_numeric += sum(r["status"] == "ok" for r in recs)
        errs += compare(c, recs)
    print(f"\ncohort sweep: couples={len(doc['couples'])} records={n_records} numeric={n_numeric} mismatches={len(errs)}")
    assert len(doc["couples"]) == 1000
    assert n_numeric > 0
    assert errs == [], errs[:20]


# ------------------------------------------------------------------ FHIR couple report (P-06)
@pytest.fixture(scope="module")
def apsi_shared():
    qs.add_path("privacy")
    from privacy.apsi import ApsiService
    from privacy.audit import AuditLog
    from privacy.authority import Authority
    from privacy.consent import ConsentService

    auth, audit = Authority(), AuditLog()
    cs = ConsentService(audit=audit)
    svc = ApsiService(authority=auth.public_key, consents=cs, audit=audit)

    def run(couple):
        a, b = couple["partners"]
        ca, cb = cs.create(a["partner_id"], b["partner_id"]), cs.create(b["partner_id"], a["partner_id"])
        sets = [auth.sign_carrier_set(p["partner_id"], {c["hgnc_id"] for c in p.get("calls") or [] if c["classification"] in PLP})
                for p in (a, b)]
        res = svc.run(ca, cb, *sets)
        assert res["status"] == "ok", res
        return res["shared_hgnc_ids"]
    return run


@pytest.mark.parametrize("vid", ["V2", "V3", "V4"])
def test_fhir_couple_report_contains_no_partner_gene(apsi_shared, vid):
    qs.add_path("fhirgen")
    from fhirgen import build_couple_report
    couple = qs.vignette(vid)
    shared = apsi_shared(couple)
    assert set(shared) == qs.intersection_hgnc(couple) == set()
    blob = json.dumps(build_couple_report(couple, shared_hgnc_ids=shared), ensure_ascii=False)
    for p in couple["partners"]:
        hits = qs.term_hits(blob, qs.partner_terms(p))
        assert not hits, f"{vid} couple report leaks {p['partner_id']}: {hits}"
        for c in p.get("calls") or []:
            assert f'"{c["hgnc_id"]}"' not in blob and f"HGNC:{c['hgnc_id']}" not in blob


def test_fhir_couple_report_v1_positive_control(apsi_shared):
    """The shared gene DOES appear (otherwise the negative tests above would be vacuous)."""
    qs.add_path("fhirgen")
    from fhirgen import build_couple_report
    couple = qs.vignette("V1")
    shared = apsi_shared(couple)
    assert shared == [4827]
    blob = json.dumps(build_couple_report(couple, shared_hgnc_ids=shared))
    assert "HBB" in blob or "4827" in blob
