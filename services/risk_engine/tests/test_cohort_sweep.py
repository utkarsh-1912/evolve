"""Cohort sweep against an INDEPENDENT oracle (R-RISK-3: 0.0% arithmetic error over the synthetic cohort).

The oracle below reads the raw contracts and recomputes everything with Fraction using different algebra:
  kinship      phi = sum (1 + F_A) / 2**(n1+n2+1)          (accumulated as a single rational)
  prior        1 - (1 - R)(1 - q)                           (complement form of R + (1-R)q)
  posterior    prior(1 - d) / (1 - prior*d)                 (simplified denominator)
  offspring    posterior / 4 ; reference = same with R = 0
It imports nothing from risk_engine except the public assess_couple() under test.
Skips cleanly while data-synth has not yet written its outputs (parallel P1 work).
"""
import json
import math
import pathlib
import re
from decimal import Decimal
from fractions import Fraction

import pytest

from conftest import ROOT, assert_schema_valid
from risk_engine import assess_couple

COHORT = ROOT / "services" / "synth" / "out" / "cohort.json"
VIGNETTES = ROOT / "tests" / "golden" / "cohort"
RAW_PANEL = json.loads((ROOT / "contracts" / "gene_panel.json").read_text(encoding="utf-8"))
ORACLE_PANEL = {g["hgnc_id"]: g for g in RAW_PANEL["genes"]}


def _q(x):
    return None if x is None else Fraction(str(x))


def oracle(couple):
    """Independent re-derivation of contract v1.1.0 records (DECISIONS #11, #17-#19)."""
    paths = couple["relationship"]["paths"]
    F = sum(((1 + Fraction(fa)) / 2 ** (n1 + n2 + 1) for n1, n2, fa in paths), Fraction(0))
    R = F + F
    by_role = {p["role"]: p for p in couple["partners"]}
    genes = sorted({c["hgnc_id"] for p in couple["partners"] for c in p["calls"]})
    expect = {}
    for h in genes:
        mine = {r: [c for c in by_role[r]["calls"] if c["hgnc_id"] == h] for r in "AB"}
        plp = {r: [c for c in mine[r] if c["classification"] != "VUS"] for r in "AB"}
        vus = {r: [c for c in mine[r] if c["classification"] == "VUS"] for r in "AB"}
        g = ORACLE_PANEL.get(h)
        rec = {"F": F, "carrier_role": None, "reason": None}
        if plp["A"] or plp["B"]:
            weird = (vus["A"] or vus["B"]
                     or any(len(plp[r]) > 1 or any(c["zygosity"] != "het" for c in plp[r]) for r in "AB"))
            if weird:
                rec.update(scenario="atypical_genotype", status="needs_counselor", escalate=True,
                           audience="counselor_only", reason="atypical_genotype")
            elif plp["A"] and plp["B"]:
                rec["scenario"] = "concordant_positive"
                if g is None:
                    rec.update(status="needs_counselor", escalate=True, audience="counselor_only",
                               reason="not_in_panel")
                else:
                    rec.update(status="ok", risk=Fraction(1, 4), escalate=True, audience="couple")
            else:
                carrier, neg = ("B", "A") if plp["B"] else ("A", "B")
                rec.update(scenario="discordant", audience="carrier_partner_only", carrier_role=carrier)
                elevated = R != 0 or bool(g and g["complex_locus"])
                stage = by_role[neg]["assays"].get(str(h))
                q = None if g is None else _q(g["carrier_freq"])
                d = _q((g.get("detection") or {}).get(stage)) if (g and stage) else None
                if g is None:
                    rec.update(status="needs_counselor", escalate=elevated, reason="not_in_panel")
                elif q is None:
                    rec.update(status="needs_counselor", escalate=elevated, reason="missing_carrier_freq")
                elif d is None:
                    rec.update(status="needs_counselor", escalate=elevated, reason="missing_detection_rate")
                elif d == 1:
                    rec.update(status="needs_counselor", escalate=True, reason="perfect_detection")
                else:
                    prior = 1 - (1 - R) * (1 - q)
                    post = prior * (1 - d) / (1 - prior * d)
                    ref = q * (1 - d) / (1 - q * d) / 4
                    rec.update(status="ok", prior=prior, post=post, d=d, risk=post / 4, ref=ref, escalate=elevated,
                               relative=None if R == 0 else (post / 4) / ref)
        elif vus["A"] and vus["B"] and any(c["in_roh_gt_10mb"] for c in vus["A"] + vus["B"]):
            rec.update(scenario="shared_vus_roh", status="needs_counselor", escalate=True,
                       audience="counselor_only", reason="shared_vus_roh")
        else:
            continue
        expect[h] = rec
    return expect


def _sig_ok(text, true, sig_max):
    """text is true rounded to <= sig_max significant figures (checked numerically, not by re-formatting)."""
    n = Decimal(text.replace(",", ""))
    half_unit = Fraction(1, 2) * Fraction(10) ** (math.floor(math.log10(true)) - (sig_max - 1))
    return abs(Fraction(n) - true) <= half_unit * (1 + Fraction(1, 10**9)) and len(n.normalize().as_tuple().digits) <= sig_max


def one_in_ok(s, x):
    """'1 in N' with N = 1/x rounded to 3 significant figures."""
    m = re.fullmatch(r"1 in ([0-9][0-9,]*(?:\.[0-9]+)?)", s or "")
    return bool(m) and _sig_ok(m.group(1), 1 / x, 3)


def times_ok(s, x):
    """'about Nx' with N = x rounded to 2 significant figures."""
    m = re.fullmatch(r"about ([0-9][0-9,]*(?:\.[0-9]+)?)x", s or "")
    return bool(m) and _sig_ok(m.group(1), x, 2)


def mismatches(couple):
    got = {o["hgnc_id"]: o for o in assess_couple(couple)}
    exp = oracle(couple)
    bad = []
    if set(got) != set(exp):
        return [f"{couple['couple_id']}: genes {sorted(got)} != oracle {sorted(exp)}"]
    for h, e in exp.items():
        o = got[h]
        checks = [o["scenario"] == e["scenario"], o["status"] == e["status"], o.get("escalate") == e["escalate"],
                  o["F"] == float(e["F"]), o["audience"] == e["audience"], o.get("carrier_role") == e["carrier_role"],
                  o["reason"] == e["reason"], o["contract_version"] == "1.1.0"]
        if "risk" in e:
            checks += [o["offspring_risk"] == float(e["risk"]), one_in_ok(o["offspring_risk_one_in"], e["risk"])]
        else:
            checks += [o["offspring_risk"] is None, o["offspring_risk_one_in"] is None]
        if "post" in e:
            checks += [o["prior_carrier_b"] == float(e["prior"]), o["posterior_carrier_b"] == float(e["post"]),
                       o["detection_rate"] == float(e["d"]), one_in_ok(o["posterior_carrier_b_one_in"], e["post"]),
                       one_in_ok(o["reference_unrelated_one_in"], e["ref"])]
            if e["relative"] is None:
                checks += [o["relative_to_unrelated"] is None, o["relative_to_unrelated_display"] is None]
            else:
                checks += [o["relative_to_unrelated"] == float(e["relative"]),
                           times_ok(o["relative_to_unrelated_display"], e["relative"])]
        if not all(checks):
            bad.append(f"{couple['couple_id']} hgnc {h}: engine {o} vs oracle {e}")
    return bad


def test_oracle_self_check_against_doc_numbers():
    """Guard against a broken oracle: it must reproduce docs/07 §3 independently."""
    v3 = {"couple_id": "SYN-C0001", "relationship": {"type": "first_cousins", "paths": [[2, 2, "0"], [2, 2, "0"]]},
          "partners": [{"role": "A", "assays": {}, "calls": [
              {"hgnc_id": 11117, "classification": "P", "zygosity": "het", "in_roh_gt_10mb": False}]},
              {"role": "B", "assays": {"11117": "initial"}, "calls": []}]}
    e = oracle(v3)[11117]
    assert round(float(1 / e["risk"]), 1) == 320.6 and round(float(1 / e["ref"]), 1) == 3800.2
    assert one_in_ok("1 in 321", e["risk"]) and not one_in_ok("1 in 320", e["risk"])
    assert one_in_ok("1 in 3,800", e["ref"]) and one_in_ok("1 in 80.2", e["post"])


def test_cohort_sweep_zero_mismatches():
    if not COHORT.exists():
        pytest.skip(f"{COHORT.relative_to(ROOT)} not yet produced by data-synth (TASK-P1-DS, parallel)")
    doc = json.loads(COHORT.read_text(encoding="utf-8"))
    assert doc["synthetic"] is True
    couples = doc["couples"]
    assert couples, "cohort is empty"
    bad, n_out = [], 0
    for c in couples:
        out = assess_couple(c)
        assert_schema_valid(out)
        n_out += len(out)
        bad += mismatches(c)
    assert not bad, f"{len(bad)} mismatches over {len(couples)} couples; first: {bad[:3]}"


def _vignette(vid):
    p = VIGNETTES / f"{vid}.json"
    if not p.exists():
        pytest.skip(f"{p.relative_to(ROOT)} not yet produced by data-synth (TASK-P1-DS, parallel)")
    (c,) = json.loads(p.read_text(encoding="utf-8"))["couples"]
    out = assess_couple(c)
    assert_schema_valid(out)
    assert not mismatches(c)
    by_gene = {o["gene"]: o for o in out}
    exp = (c.get("expected") or {}).get("genes", [])
    assert sorted(by_gene) == sorted(e["gene"] for e in exp)  # data-synth's expected gene list
    for e in exp:  # cross-check against data-synth's expected block (written from docs/07, not computed)
        o = by_gene[e["gene"]]
        assert o["hgnc_id"] == e["hgnc_id"] and o["status"] == e["status"]
        if e.get("scenario") is not None:
            assert o["scenario"] == e["scenario"]
        if "escalate" in e:
            assert o["escalate"] == e["escalate"]
        if "offspring_one_in_display" in e:
            assert o["offspring_risk_one_in"] == f"1 in {e['offspring_one_in_display']}"
    return by_gene


def test_v1_concordant_hbb_quarter():
    o = _vignette("V1")["HBB"]
    assert o["scenario"] == "concordant_positive" and o["offspring_risk"] == 0.25 and o["escalate"] is True


def test_v2_cyp21a2_offspring_1_in_426():
    o = _vignette("V2")["CYP21A2"]
    assert o["scenario"] == "discordant" and o["offspring_risk_one_in"] == "1 in 426"


def test_v3_smn1_offspring_1_in_321():
    o = _vignette("V3")["SMN1"]
    assert o["offspring_risk_one_in"] == "1 in 321" and o["reference_unrelated_one_in"] == "1 in 3,800"


def test_v5_donson_vus_roh_escalates():
    out = _vignette("V5")
    o = out["DONSON"]
    assert (o["scenario"], o["status"], o["escalate"]) == ("shared_vus_roh", "needs_counselor", True)
    assert (o["reason"], o["audience"]) == ("shared_vus_roh", "counselor_only")
    assert o["offspring_risk"] is None and o["F"] == 0.125
    assert any(x["escalate"] for x in out.values())


def test_v4_no_concordant_gene_and_no_escalation():
    out = _vignette("V4")
    assert out and all(o["scenario"] == "discordant" for o in out.values())
    assert not any(o["escalate"] for o in out.values())  # DECISIONS #11: Compatible + private counseling
    assert all(o["audience"] == "carrier_partner_only" for o in out.values())  # P-06
    assert {g: o["carrier_role"] for g, o in out.items()} == {"MEFV": "A", "GJB2": "A", "ABCA4": "B"}
