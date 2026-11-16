"""Hypothesis property tests (R-RISK-1/2/3). derandomize=True keeps CI deterministic."""
import hashlib
import json
from fractions import Fraction

from hypothesis import given, settings, strategies as st

from conftest import PATHS, assert_schema_valid, call
from risk_engine import Path, assess_couple, discordant, gene_scenarios, load_panel, lock, wright

SET = settings(max_examples=300, derandomize=True, deadline=None)
probs = st.fractions(min_value=0, max_value=1, max_denominator=10_000)
open_probs = st.fractions(min_value=Fraction(1, 10_000), max_value=Fraction(9_999, 10_000), max_denominator=10_000)
path_st = st.builds(Path, st.integers(1, 6), st.integers(1, 6),
                    st.fractions(min_value=0, max_value=Fraction(1, 2), max_denominator=64))


@SET
@given(st.lists(path_st, max_size=6), st.randoms(use_true_random=False))
def test_wright_R_is_twice_F_and_order_invariant(paths, rnd):
    f, r = wright(paths)
    assert r == 2 * f and f >= 0
    shuffled = list(paths)
    rnd.shuffle(shuffled)
    assert wright(shuffled) == (f, r)


@SET
@given(st.lists(path_st, max_size=5), path_st)
def test_wright_adding_a_path_strictly_increases_F(paths, extra):
    assert wright(paths + [extra])[0] > wright(paths)[0]


@SET
@given(path_st)
def test_wright_ancestor_inbreeding_scales_term(p):
    base = wright([Path(p.n1, p.n2, 0)])[0]
    assert wright([p])[0] == base * (1 + p.ancestor_f)


@SET
@given(probs, open_probs, st.sampled_from([Fraction(0), Fraction(1, 32), Fraction(1, 8), Fraction(1, 4)]))
def test_discordant_negative_test_never_raises_risk(q, d, r):
    res = discordant(q, d, r)
    assert 0 <= res["posterior_carrier_b"] <= res["prior_carrier_b"] <= 1
    assert res["offspring_risk"] == res["posterior_carrier_b"] / 4


@SET
@given(open_probs, open_probs, open_probs)
def test_discordant_monotone_in_d_and_R(q, d1, d2):
    lo, hi = sorted((d1, d2))
    assert discordant(q, hi, 0)["posterior_carrier_b"] <= discordant(q, lo, 0)["posterior_carrier_b"]
    assert discordant(q, lo, Fraction(1, 8))["posterior_carrier_b"] >= discordant(q, lo, 0)["posterior_carrier_b"]


@SET
@given(probs, st.sampled_from([Fraction(0), Fraction(1, 8)]))
def test_useless_assay_keeps_prior(q, r):
    res = discordant(q, 0, r)
    assert res["posterior_carrier_b"] == res["prior_carrier_b"]


# ---- assess_couple over generated synthetic couples ----
PANEL = load_panel()
GENE_IDS = sorted(PANEL.genes) + [99999]
SYMBOL = {h: (PANEL.gene(h).symbol if PANEL.gene(h) else "SYNGENE") for h in GENE_IDS}

call_st = st.builds(
    lambda h, cls, zyg, roh: call(h, SYMBOL[h], cls, zyg, roh),
    st.sampled_from(GENE_IDS), st.sampled_from(["P", "LP", "VUS"]),
    st.sampled_from(["het", "het", "het", "hom"]), st.booleans())
assays_st = st.dictionaries(st.sampled_from([str(h) for h in GENE_IDS]), st.sampled_from(["initial", "confirmatory"]))


@st.composite
def couples(draw):
    rel = draw(st.sampled_from(sorted(PATHS)))
    parts = []
    for role in "AB":
        parts.append({"partner_id": f"SYN-P0001{role}", "role": role, "sex": "female" if role == "A" else "male",
                      "age": 30, "bmi": None, "calls": draw(st.lists(call_st, max_size=4)), "assays": draw(assays_st)})
    return {"couple_id": "SYN-C0001", "relationship": {"type": rel, "paths": PATHS[rel]}, "partners": parts}


@SET
@given(couples())
def test_assess_outputs_are_valid_safe_and_deterministic(c):
    out = assess_couple(c)
    assert_schema_valid(out)
    assert out == assess_couple(json.loads(json.dumps(c)))  # determinism
    ids = [o["hgnc_id"] for o in out]
    assert ids == sorted(set(ids))  # one per gene, sorted
    plp_genes = {x["hgnc_id"] for p in c["partners"] for x in p["calls"] if x["classification"] != "VUS"}
    vus_genes = {x["hgnc_id"] for p in c["partners"] for x in p["calls"] if x["classification"] == "VUS"}
    assert set(ids) <= plp_genes | vus_genes
    assert plp_genes <= set(ids)  # every P/LP gene is reported
    for o in out:
        assert o["fusage"] == "genome_wide_context_only" and o["F"] is not None
        body = {k: v for k, v in o.items() if k != "digest"}
        assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == o["digest"]
        if o["status"] == "needs_counselor":
            assert o["offspring_risk"] is None and o["offspring_risk_one_in"] is None
            assert isinstance(o["escalate"], bool) and o["reason"] is not None
            if o["scenario"] != "discordant":  # only missing-parameter discordant may be non-escalating
                assert o["escalate"] is True
        else:
            assert o["reason"] is None
        if o["scenario"] == "discordant" and o["status"] == "ok":
            assert o["offspring_risk"] > 0 and o["offspring_risk_one_in"]  # never "no risk" (P-04)
            assert o["reference_unrelated_one_in"]
            if c["relationship"]["paths"]:
                assert o["relative_to_unrelated"] >= 1 and o["relative_to_unrelated_display"].startswith("about ")
            else:  # R = 0 (DECISIONS #19)
                assert o["relative_to_unrelated"] is None and o["relative_to_unrelated_display"] is None
        elif o["status"] == "ok":
            assert o["scenario"] == "concordant_positive" and o["offspring_risk"] == 0.25 and o["escalate"]
    roles = {g.hgnc_id: g for g in gene_scenarios(c)}
    carried = {r: {x["hgnc_id"] for x in p["calls"] if x["classification"] != "VUS"}
               for r, p in (("A", c["partners"][0]), ("B", c["partners"][1]))}
    for o in out:
        if o["scenario"] == "discordant":  # private to the carrier (P-06)
            assert o["audience"] == "carrier_partner_only"
            assert roles[o["hgnc_id"]].carrier_roles == (o["carrier_role"],)
        else:
            assert o.get("carrier_role") is None
        if o["audience"] == "couple":  # only genes both partners carry (APSI intersection) reach the couple
            assert o["hgnc_id"] in carried["A"] & carried["B"]


@SET
@given(probs, open_probs, st.sampled_from([Fraction(0), Fraction(1, 8)]))
def test_lock_validates_and_digest_changes_with_content(q, d, r):
    kw = dict(f=r / 2, reference_unrelated=discordant(q, d, 0), audience="carrier_partner_only", carrier_role="A")
    a = lock(discordant(q, d, r), gene="SYNG1", hgnc_id=99999, **kw)
    b = lock(discordant(q, d, r), gene="SYNG1", hgnc_id=99998, **kw)
    assert_schema_valid([a, b])
    assert a["digest"] != b["digest"]
