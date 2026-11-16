"""assess_couple on hand-built synthetic couples, one per scenario (TASK-P1-RE §3). R-RISK-1/2/3."""
import copy
import hashlib
import json
from fractions import Fraction

import jsonschema
import pytest

from conftest import COHORT_SCHEMA, assert_schema_valid, call, couple
from risk_engine import assess_couple, gene_scenarios, load_panel, panel_from_dict
from risk_engine.panel import DEFAULT_PANEL_PATH

HBB, CYP, SMN1, MEFV, ABCA4, GJB2, DONSON = 4827, 2600, 11117, 6998, 34, 4284, 2993


def run(c):
    jsonschema.validate({"contract_version": "1.0.0", "seed": 0, "synthetic": True, "couples": [c]}, COHORT_SCHEMA)
    out = assess_couple(c)
    assert_schema_valid(out)
    return out


def test_concordant_positive_first_cousins():
    (o,) = run(couple("first_cousins", [call(HBB, "HBB")], [call(HBB, "HBB")]))
    assert o["scenario"] == "concordant_positive" and o["status"] == "ok"
    assert o["offspring_risk"] == 0.25 and o["offspring_risk_one_in"] == "1 in 4"
    assert o["F"] == 0.0625 and o["fusage"] == "genome_wide_context_only"
    assert o["escalate"] is True  # trigger (a)
    assert (o["audience"], o["carrier_role"], o["reason"]) == ("couple", None, None)
    assert o["contract_version"] == "1.1.0"


def test_discordant_cyp21a2_initial_unrelated():
    (o,) = run(couple("unrelated", [call(CYP, "CYP21A2")], [], b_assays={str(CYP): "initial"}))
    assert (o["scenario"], o["status"]) == ("discordant", "ok")
    assert o["offspring_risk_one_in"] == "1 in 426"
    assert o["posterior_carrier_b_one_in"] == "1 in 106"
    assert o["detection_rate"] == 0.92 and o["prior_carrier_b"] == 0.106
    assert o["reference_unrelated_one_in"] == "1 in 426"
    assert o["relative_to_unrelated"] is None and o["relative_to_unrelated_display"] is None  # R=0 (#19)
    assert o["F"] == 0.0
    assert o["escalate"] is True  # complex locus, trigger (b)
    assert (o["audience"], o["carrier_role"], o["reason"]) == ("carrier_partner_only", "A", None)


def test_discordant_cyp21a2_confirmatory():
    (o,) = run(couple("unrelated", [call(CYP, "CYP21A2")], [], b_assays={str(CYP): "confirmatory"}))
    assert o["offspring_risk_one_in"] == "1 in 3,380" and o["posterior_carrier_b_one_in"] == "1 in 844"
    assert o["detection_rate"] == 0.99


def test_discordant_smn1_first_cousins():
    (o,) = run(couple("first_cousins", [call(SMN1, "SMN1", vtype="cnv_deletion")], [],
                      b_assays={str(SMN1): "initial"}))
    assert o["offspring_risk_one_in"] == "1 in 321"
    assert o["posterior_carrier_b_one_in"] == "1 in 80.2"
    assert o["reference_unrelated_one_in"] == "1 in 3,800"
    assert 11.8 < o["relative_to_unrelated"] < 11.9
    assert o["relative_to_unrelated_display"] == "about 12x"
    assert o["F"] == 0.0625 and o["escalate"] is True


def test_discordant_uses_negative_partners_assay_when_b_is_carrier():
    c = couple("unrelated", [], [call(CYP, "CYP21A2")], a_assays={str(CYP): "confirmatory"},
               b_assays={str(CYP): "initial"})
    (o,) = run(c)
    assert o["detection_rate"] == 0.99 and o["carrier_role"] == "B"
    (gs,) = gene_scenarios(c)
    assert gs.carrier_roles == ("B",) and gs.negative_role == "A"


@pytest.mark.parametrize("hid,sym,reason", [(MEFV, "MEFV", "missing_detection_rate"),
                                            (GJB2, "GJB2", "missing_carrier_freq")])
def test_missing_q_or_d_needs_counselor_no_number(hid, sym, reason):
    (o,) = run(couple("unrelated", [call(hid, sym)], [], b_assays={str(hid): "initial"}))
    # missing parameter, unrelated, non-complex: no number, NOT an escalation (DECISIONS #11/#19)
    assert (o["scenario"], o["status"], o["escalate"]) == ("discordant", "needs_counselor", False)
    assert (o["reason"], o["audience"], o["carrier_role"]) == (reason, "carrier_partner_only", "A")
    assert o["offspring_risk"] is None and o["offspring_risk_one_in"] is None
    assert "posterior_carrier_b" not in o and "relative_to_unrelated" not in o
    assert o["F"] == 0.0


def test_missing_d_escalates_when_related():  # DECISIONS #19, trigger (b)
    (o,) = run(couple("first_cousins", [call(HBB, "HBB")], [], b_assays={str(HBB): "initial"}))
    assert (o["status"], o["reason"], o["escalate"]) == ("needs_counselor", "missing_detection_rate", True)


@pytest.mark.parametrize("assays", [{}, {str(SMN1): "confirmatory"}])
def test_missing_assay_stage_or_uncurated_stage_needs_counselor(assays):
    (o,) = run(couple("unrelated", [call(SMN1, "SMN1")], [], b_assays=assays))
    assert o["status"] == "needs_counselor" and o["offspring_risk"] is None
    assert o["reason"] == "missing_detection_rate" and o["escalate"] is True  # complex locus (#19)


def test_v4_like_three_private_discordant_genes():
    c = couple("unrelated", [call(MEFV, "MEFV"), call(GJB2, "GJB2")], [call(ABCA4, "ABCA4")],
               a_assays={str(ABCA4): "initial"}, b_assays={str(MEFV): "initial", str(GJB2): "initial"})
    out = run(c)
    assert [o["gene"] for o in out] == ["ABCA4", "GJB2", "MEFV"]  # sorted by hgnc_id (34, 4284, 6998)
    assert all(o["scenario"] == "discordant" and o["status"] == "needs_counselor" for o in out)
    assert not any(o["escalate"] for o in out)  # Compatible + private counseling (source §2.4, DECISIONS #11)
    assert {o["gene"]: o["carrier_role"] for o in out} == {"ABCA4": "B", "GJB2": "A", "MEFV": "A"}
    assert all(o["audience"] == "carrier_partner_only" for o in out)
    routes = {g.gene: g.carrier_roles for g in gene_scenarios(c)}
    assert routes == {"ABCA4": ("B",), "MEFV": ("A",), "GJB2": ("A",)}


def test_shared_vus_in_roh_escalates_without_number():
    c = couple("double_first_cousins", [call(DONSON, "DONSON", "VUS", roh=True)],
               [call(DONSON, "DONSON", "VUS", roh=True)])
    (o,) = run(c)
    assert (o["scenario"], o["status"], o["escalate"]) == ("shared_vus_roh", "needs_counselor", True)
    assert (o["reason"], o["audience"]) == ("shared_vus_roh", "counselor_only")
    assert o["offspring_risk"] is None and o["F"] == 0.125


@pytest.mark.parametrize("a_roh,b_roh,expected", [(True, False, 1), (False, False, 0)])
def test_shared_vus_roh_flag_on_either_partner(a_roh, b_roh, expected):
    c = couple("first_cousins", [call(DONSON, "DONSON", "VUS", roh=a_roh)],
               [call(DONSON, "DONSON", "VUS", roh=b_roh)])
    assert len(run(c)) == expected


def test_vus_in_one_partner_only_emits_nothing():
    assert run(couple("first_cousins", [call(DONSON, "DONSON", "VUS", roh=True)], [])) == []


@pytest.mark.parametrize("a_calls,b_calls", [
    ([call(HBB, "HBB", zyg="hom")], []),
    ([call(HBB, "HBB", zyg="hom")], [call(HBB, "HBB")]),
    ([call(CYP, "CYP21A2"), call(CYP, "CYP21A2", cls="LP")], []),
    ([call(CYP, "CYP21A2")], [call(CYP, "CYP21A2", cls="VUS")]),
    ([call(HBB, "HBB")], [call(HBB, "HBB"), call(HBB, "HBB", cls="VUS")]),
])
def test_atypical_inputs_fail_safe_to_counselor(a_calls, b_calls):  # DECISIONS #18
    out = run(couple("unrelated", a_calls, b_calls, b_assays={str(CYP): "initial", str(HBB): "initial"}))
    (o,) = out
    assert (o["scenario"], o["status"], o["escalate"]) == ("atypical_genotype", "needs_counselor", True)
    assert (o["reason"], o["audience"], o["carrier_role"]) == ("atypical_genotype", "counselor_only", None)
    assert o["offspring_risk"] is None


def test_gene_absent_from_panel():
    (o,) = run(couple("first_cousins", [call(99999, "SYNGENE")], []))
    assert (o["scenario"], o["status"], o["escalate"]) == ("discordant", "needs_counselor", True)  # R>0
    assert o["reason"] == "not_in_panel" and o["audience"] == "carrier_partner_only"
    (o,) = run(couple("unrelated", [call(99999, "SYNGENE")], []))
    assert (o["reason"], o["escalate"]) == ("not_in_panel", False)
    (o,) = run(couple("unrelated", [call(99999, "SYNGENE")], [call(99999, "SYNGENE")]))
    assert (o["scenario"], o["status"], o["escalate"]) == ("concordant_positive", "needs_counselor", True)
    assert (o["reason"], o["audience"]) == ("not_in_panel", "counselor_only")
    assert o["offspring_risk"] is None and o["gene"] == "SYNGENE"


def test_no_calls_no_outputs():
    assert run(couple("first_cousins")) == []


def _synthetic_panel(d):
    return panel_from_dict({"contract_version": "1.0.0", "genes": [
        {"symbol": "SYNG1", "hgnc_id": 99999, "carrier_freq": 0.05, "complex_locus": False,
         "detection": {"initial": d}}]})


def test_unrelated_noncomplex_discordant_does_not_force_escalation():
    c = couple("unrelated", [call(99999, "SYNG1")], [], b_assays={"99999": "initial"})
    (o,) = assess_couple(c, panel=_synthetic_panel(0.9))
    assert_schema_valid([o])
    assert o["status"] == "ok" and o["escalate"] is False


def test_related_noncomplex_discordant_escalates():
    c = couple("second_cousins", [call(99999, "SYNG1")], [], b_assays={"99999": "initial"})
    (o,) = assess_couple(c, panel=_synthetic_panel(0.9))
    assert_schema_valid([o])
    assert o["status"] == "ok" and o["escalate"] is True
    assert o["relative_to_unrelated"] > 1 and o["relative_to_unrelated_display"].startswith("about ")


def test_perfect_assay_never_yields_zero_risk_label():
    c = couple("unrelated", [call(99999, "SYNG1")], [], b_assays={"99999": "initial"})
    (o,) = assess_couple(c, panel=_synthetic_panel(1))
    assert_schema_valid([o])
    assert o["status"] == "needs_counselor" and o["offspring_risk"] is None and o["escalate"] is True  # #18
    assert o["reason"] == "perfect_detection"


def test_ancestor_inbreeding_paths_feed_F():
    c = couple("first_cousins", [call(HBB, "HBB")], [call(HBB, "HBB")],
               paths=[[2, 2, "1/16"], [2, 2, "1/16"]])
    (o,) = run(c)
    assert o["F"] == float(Fraction(17, 256))


def test_determinism_same_input_same_digest():
    c = couple("first_cousins", [call(SMN1, "SMN1"), call(HBB, "HBB")], [call(HBB, "HBB")],
               b_assays={str(SMN1): "initial"})
    a, b = assess_couple(c), assess_couple(copy.deepcopy(c))
    assert a == b
    rev = copy.deepcopy(c)
    rev["partners"][0]["calls"].reverse()
    rev["partners"].reverse()
    assert [o["digest"] for o in assess_couple(rev)] == [o["digest"] for o in a]


def test_digest_is_sha256_of_content():
    (o,) = run(couple("first_cousins", [call(SMN1, "SMN1")], [], b_assays={str(SMN1): "initial"}))
    body = {k: v for k, v in o.items() if k != "digest"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == o["digest"]


def test_outputs_carry_no_variant_strings():
    (o,) = run(couple("unrelated", [call(CYP, "CYP21A2")], [], b_assays={str(CYP): "initial"}))
    assert "c.SYN" not in json.dumps(o)


@pytest.mark.parametrize("mutate", [
    lambda c: c["partners"].pop(),
    lambda c: c["partners"][1].update(role="A"),
    lambda c: c.pop("relationship"),
    lambda c: c["relationship"].update(paths=[[2, 2]]),
    lambda c: c["relationship"].update(paths=[[2, "2", "0"]]),
    lambda c: c["relationship"].update(paths=[[True, 2, "0"]]),
    lambda c: c["relationship"].update(paths=[[2, 2, 0]]),
    lambda c: c["relationship"].update(paths=[[0, 2, "0"]]),
    lambda c: c["relationship"].update(paths=[[2, 2, "3/2"]]),
])
def test_malformed_input_raises(mutate):
    c = couple("first_cousins", [call(HBB, "HBB")], [call(HBB, "HBB")])
    mutate(c)
    with pytest.raises(ValueError):
        assess_couple(c)


# ---- panel.py ----

def test_panel_lookup_values_from_contract():
    p = load_panel()
    assert p is load_panel(DEFAULT_PANEL_PATH)  # cached
    assert p.carrier_freq(CYP) == Fraction(106, 1000)
    assert p.detection_rate(CYP, "initial") == Fraction(92, 100)
    assert p.detection_rate(CYP, "confirmatory") == Fraction(99, 100)
    assert p.detection_rate(SMN1, "confirmatory") is None
    assert p.detection_rate(HBB, "initial") is None
    assert p.detection_rate(CYP, None) is None and p.detection_rate(CYP, "bogus") is None
    assert p.carrier_freq(GJB2) is None
    assert p.carrier_freq(424242) is None and p.detection_rate(424242, "initial") is None
    assert p.gene(SMN1).complex_locus is True
    with pytest.raises(TypeError):
        p.genes[1] = None  # immutable


@pytest.mark.parametrize("doc", [
    {"contract_version": "2.0.0", "genes": []},
    {"contract_version": "1.0.0", "genes": [{"symbol": "X", "hgnc_id": 1, "carrier_freq": 0.1},
                                            {"symbol": "Y", "hgnc_id": 1, "carrier_freq": 0.1}]},
    {"contract_version": "1.0.0", "genes": [{"symbol": "X", "hgnc_id": 1, "carrier_freq": 1.5}]},
    {"contract_version": "1.0.0", "genes": [{"symbol": "X", "hgnc_id": 1, "carrier_freq": True}]},
    {"contract_version": "1.0.0", "genes": [{"symbol": "X", "hgnc_id": 1, "carrier_freq": [0.1]}]},
])
def test_panel_rejects_bad_contract(doc):
    with pytest.raises(ValueError):
        panel_from_dict(doc)


def test_panel_defaults_and_ignores_unknown_stage():
    p = panel_from_dict({"contract_version": "1.0.0", "genes": [
        {"symbol": "X", "hgnc_id": 1, "carrier_freq": "0.1", "detection": {"initial": 0.9, "other": 0.5}}]})
    g = p.gene(1)
    assert g.complex_locus is False and dict(g.detection) == {"initial": Fraction(9, 10)}
    assert panel_from_dict({"contract_version": "1.0.0", "genes": [
        {"symbol": "X", "hgnc_id": 1, "carrier_freq": None}]}).gene(1).detection == {}


# ---- core.py paths not reached via assess_couple ----

def test_core_unrelated_concordant_negative_and_zero_display():
    from risk_engine import concordant_negative, discordant, lock
    res = concordant_negative(Fraction(13, 1000), "0.92")
    assert res["status"] == "ok" and res["offspring_risk"] == res["posterior_carrier_a"] * res["posterior_carrier_b"] / 4
    zero = lock(discordant(0, "0.92"), gene="SYNG1", hgnc_id=99999, audience="carrier_partner_only",
                carrier_role="A")
    assert zero["offspring_risk"] == 0.0 and zero["offspring_risk_one_in"] is None
    assert_schema_valid([zero])


def test_core_float_inputs_are_exact_decimal():
    from risk_engine import discordant
    assert discordant(0.106, 0.92) == discordant("0.106", "0.92")
    assert discordant(0.106, 0.92)["q"] == Fraction(106, 1000)


def test_lock_contract_checks():
    from risk_engine import concordant_negative, concordant_positive, lock
    rel = lock(concordant_negative("0.013", "0.92", r="1/8"), gene="SMN1", hgnc_id=11117)
    assert (rel["reason"], rel["audience"], rel["escalate"]) == ("related_concordant_negative", "counselor_only", True)
    assert_schema_valid([rel])
    for kw in (dict(audience="everyone"), dict(carrier_role="C"), dict(reason="missing_carrier_freq")):
        with pytest.raises(ValueError):
            lock(concordant_positive(), gene="HBB", hgnc_id=4827, **kw)
    with pytest.raises(ValueError):  # needs_counselor without a reason
        lock({"scenario": "discordant", "status": "needs_counselor", "offspring_risk": None}, gene="X", hgnc_id=1)


def test_relative_display_rounding():
    from risk_engine import discordant, lock
    o = lock(discordant("0.013", "0.92", "1/8"), gene="SMN1", hgnc_id=11117, audience="carrier_partner_only",
             carrier_role="A", reference_unrelated=discordant("0.013", "0.92", 0))
    assert o["relative_to_unrelated_display"] == "about 12x"
