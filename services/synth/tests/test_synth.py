"""data-synth tests (R-DATA-1/2/3): schema validity, determinism, frequency recovery, vignettes."""
import json
import math
import pathlib
import subprocess
import sys

import jsonschema
import pytest

from synth import build_report, build_vignettes, dumps, generate_cohort, load_panel
from synth.cohort import ABSENT_CLINVAR_P, ABSENT_GNOMAD_P, sampled_genes

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "contracts" / "cohort.schema.json").read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)
GOLDEN_DIR = ROOT / "tests" / "golden" / "cohort"
COHORT_OUT = ROOT / "services" / "synth" / "out" / "cohort.json"


@pytest.fixture(scope="module")
def cohort42():
    return generate_cohort(42, 1000)


def _errors(doc):
    return [f"{list(e.path)}: {e.message}" for e in VALIDATOR.iter_errors(doc)]


def test_schema_valid(cohort42):
    assert _errors(cohort42) == []
    assert len(cohort42["couples"]) == 1000 and cohort42["synthetic"] is True


def test_determinism_identical_bytes():
    assert dumps(generate_cohort(42, 200)).encode() == dumps(generate_cohort(42, 200)).encode()
    assert dumps(generate_cohort(42, 200)) != dumps(generate_cohort(43, 200))


def test_saved_cohort_matches_generator():
    """The committed seed-42 file is exactly what the generator produces (consumers rely on it)."""
    assert COHORT_OUT.exists(), "run: python -m synth --seed 42 --n 1000"
    assert COHORT_OUT.read_bytes() == dumps(generate_cohort(42, 1000)).encode("utf-8")


def test_cli_writes_identical_file(tmp_path):
    out = tmp_path / "c.json"
    subprocess.run([sys.executable, "-m", "synth", "--seed", "42", "--n", "50", "--out", str(out)],
                   check=True, cwd=ROOT / "services" / "synth", capture_output=True)
    assert out.read_bytes() == dumps(generate_cohort(42, 50)).encode("utf-8")
    assert (tmp_path / "c_report.json").exists()


def test_ids_obviously_fake_and_sexes(cohort42):
    for c in cohort42["couples"]:
        assert c["couple_id"].startswith("SYN-C")
        a, b = c["partners"]
        assert {a["sex"], b["sex"]} == {"female", "male"}
        for p in (a, b):
            assert p["partner_id"].startswith("SYN-P")
            assert 18 <= p["age"] <= 45 and 19.0 <= p["bmi"] <= 40.0


def test_only_frequency_bearing_genes_sampled(cohort42):
    allowed = {g["hgnc_id"] for g in sampled_genes(load_panel())}
    for c in cohort42["couples"]:
        for p in c["partners"]:
            for call in p["calls"]:
                assert call["hgnc_id"] in allowed
                assert call["classification"] in ("P", "LP") and call["zygosity"] == "het"


def test_carrier_rate_recovery_large_sample():
    """Each gene's realized carrier rate is within sampling error of the target.
    Tolerance 3.89 SD (two-sided ~1e-4 per gene) widened by sqrt(2) for within-couple IBD correlation."""
    doc = generate_cohort(2024, 10000)
    rep = build_report(doc)
    for r in rep["carrier_rates"]:
        n, p = r["individuals"], r["target"]
        tol = 3.89 * math.sqrt(2) * math.sqrt(p * (1 - p) / n)
        assert abs(r["carriers"] / n - p) <= tol, r


def test_founders_never_novel(cohort42):
    """DECISIONS #12: documented founder alleles are never flagged absent from gnomAD/ClinVar."""
    founders = set()
    for g in load_panel()["genes"]:
        for f in g.get("founder_variants", []):
            founders.add((g["hgnc_id"], f.get("hgvs_c"), f.get("hgvs_p"), f["variant_type"]))
    seen = 0
    for c in cohort42["couples"]:
        for p in c["partners"]:
            for call in p["calls"]:
                if (call["hgnc_id"], call["hgvs_c"], call["hgvs_p"], call["variant_type"]) in founders:
                    seen += 1
                    assert call["absent_gnomad"] is False and call["absent_clinvar"] is False, call
    assert seen > 0
    for doc in build_vignettes().values():
        for p in doc["couples"][0]["partners"]:
            for call in p["calls"]:
                if (call["hgnc_id"], call["hgvs_c"], call["hgvs_p"], call["variant_type"]) in founders:
                    assert not call["absent_gnomad"] and not call["absent_clinvar"]


def test_novelty_gap_rates_on_synthetic_variants():
    rep = build_report(generate_cohort(2024, 10000))
    ng = rep["novelty_gap"]
    n = ng["synthetic_calls"]
    for k, target in (("synthetic_absent_gnomad_rate", ABSENT_GNOMAD_P),
                      ("synthetic_absent_clinvar_rate", ABSENT_CLINVAR_P)):
        tol = 3.89 * math.sqrt(2) * math.sqrt(target * (1 - target) / n)
        assert abs(ng[k] - target) <= tol + 1e-4


def test_concordance_reported_with_ci(cohort42):
    """DECISIONS #10: concordance is reported (8-gene floor) with a CI; no band assertion."""
    c = build_report(cohort42)["concordance"]
    assert 0 <= c["ci95"][0] <= c["rate"] <= c["ci95"][1] <= 1
    assert c["concordant_couples"] == round(c["rate"] * 1000)
    assert "in_band" not in c


def test_relationship_mix_source_realistic():
    """Consanguineous share (second cousins or closer) <= 50% (+ sampling error); first cousins ~1/3."""
    doc = generate_cohort(42, 1000)
    n = len(doc["couples"])
    cons = sum(c["relationship"]["type"] != "unrelated" for c in doc["couples"])
    fc = sum(c["relationship"]["type"] == "first_cousins" for c in doc["couples"])
    sd = math.sqrt(0.25 / n)
    assert cons / n <= 0.50 + 3 * sd
    assert abs(fc / n - 0.33) <= 3 * math.sqrt(0.33 * 0.67 / n)
    from synth.cohort import RELATIONSHIP_MIX
    assert sum(float(s) for k, s in RELATIONSHIP_MIX if k != "unrelated") <= 0.50 + 1e-12


def test_consanguineous_more_concordant():
    by = build_report(generate_cohort(5, 20000))["by_relationship"]
    assert by["unrelated"]["concordance_rate"] < by["first_cousins"]["concordance_rate"] \
        < by["double_first_cousins"]["concordance_rate"]


def test_confirmatory_only_for_negative_partner_in_discordant_cyp21a2(cohort42):
    n_conf = 0
    for c in cohort42["couples"]:
        a, b = c["partners"]
        for p, other in ((a, b), (b, a)):
            if p["assays"].get("2600") == "confirmatory":
                n_conf += 1
                assert not any(x["hgnc_id"] == 2600 for x in p["calls"])
                assert any(x["hgnc_id"] == 2600 for x in other["calls"])
            assert set(p["assays"].values()) <= {"initial", "confirmatory"}
    assert n_conf > 0


def test_relationship_paths(cohort42):
    expected = {"unrelated": 0, "second_cousins": 2, "first_cousins": 2, "double_first_cousins": 4}
    for c in cohort42["couples"]:
        assert len(c["relationship"]["paths"]) == expected[c["relationship"]["type"]]


# ---- Vignettes V1-V5 (R-DATA-2) ----
VIGNETTES = build_vignettes()


@pytest.mark.parametrize("vid", ["V1", "V2", "V3", "V4", "V5"])
def test_vignette_schema_and_golden_file(vid):
    doc = VIGNETTES[vid]
    assert _errors(doc) == []
    assert doc["couples"][0]["couple_id"] == vid and len(doc["couples"]) == 1
    path = GOLDEN_DIR / f"{vid}.json"
    assert path.exists()
    assert path.read_bytes() == dumps(doc).encode("utf-8"), "golden fixture drifted from vignettes.py"


def _genes(p):
    return {(c["gene"], c["classification"]) for c in p["calls"]}


def test_vignette_shapes():
    v = {k: d["couples"][0] for k, d in VIGNETTES.items()}
    a, b = v["V1"]["partners"]
    assert v["V1"]["relationship"]["type"] == "first_cousins"
    assert [c["hgvs_c"] for c in a["calls"]] == [c["hgvs_c"] for c in b["calls"]] == ["c.92+5G>C"]
    a, b = v["V2"]["partners"]
    assert v["V2"]["relationship"]["type"] == "unrelated" and a["calls"][0]["hgvs_c"] == "c.955C>T"
    assert b["calls"] == [] and b["assays"]["2600"] == "initial"
    a, b = v["V3"]["partners"]
    assert v["V3"]["relationship"]["type"] == "first_cousins"
    assert a["calls"][0]["variant_type"] == "cnv_deletion" and b["calls"] == [] and b["assays"]["11117"] == "initial"
    a, b = v["V4"]["partners"]
    assert _genes(a) == {("MEFV", "P"), ("GJB2", "P")} and _genes(b) == {("ABCA4", "P")}
    assert v["V4"]["expected"]["apsi"]["intersection_hgnc_ids"] == []
    a, b = v["V5"]["partners"]
    assert v["V5"]["relationship"]["type"] == "double_first_cousins"
    for p in (a, b):
        (c,) = p["calls"]
        assert (c["gene"], c["classification"], c["absent_gnomad"], c["absent_clinvar"], c["in_roh_gt_10mb"]) \
            == ("DONSON", "VUS", True, True, True)
        assert c["hgvs_c"].startswith("c.SYN")
    assert v["V5"]["family_history"] and v["V5"]["expected"]["couple_escalation"] is True


def test_vignette_expected_numbers_match_golden_vectors():
    """Expected numbers are copied from tests/golden/risk_vectors.json, not computed here."""
    vec = {d["id"]: d for d in json.loads((ROOT / "tests/golden/risk_vectors.json").read_text())["discordant"]}
    v2 = VIGNETTES["V2"]["couples"][0]["expected"]["genes"][0]
    v3 = VIGNETTES["V3"]["couples"][0]["expected"]["genes"][0]
    for exp, key in ((v2, "V2-initial"), (v3, "V3-cousins")):
        for f in ("prior", "posterior", "posterior_one_in", "offspring_one_in"):
            assert exp[f] == vec[key][f]
    assert v2["reference_if_confirmatory"]["offspring_one_in"] == vec["V2-confirmatory"]["offspring_one_in"]
    assert v3["reference_unrelated_offspring_one_in"] == vec["V3-unrelated"]["offspring_one_in"]
