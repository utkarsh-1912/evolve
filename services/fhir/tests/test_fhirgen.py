"""Tests for fhirgen (R-FHIR-1). In-test couples are synthetic and match contracts/cohort.schema.json."""
from __future__ import annotations

import copy
import json
import pathlib
import re

import jsonschema
import pytest

from fhirgen import (build_couple_report, build_family, build_partner_bundle, build_pedigree,
                     build_phenopacket, to_dict)
from fhirgen.validate import validate_bundle, validate_cohort, validate_pedigree, validate_phenopacket
from fhirgen import constants as C
from fhirgen.panel import cohort_schema
from fhirgen.phenopacket import phenotypic_feature

ROOT = pathlib.Path(__file__).resolve().parents[3]
GOLDEN = ROOT / "tests" / "golden" / "cohort"
COHORT = ROOT / "services" / "synth" / "out" / "cohort.json"


def _call(hgnc, gene, hgvs_c=None, hgvs_p=None, zyg="het", cls="P", vtype="snv", roh=False):
    return {"hgnc_id": hgnc, "gene": gene, "hgvs_c": hgvs_c, "hgvs_p": hgvs_p, "refseq": None,
            "zygosity": zyg, "classification": cls, "variant_type": vtype,
            "absent_gnomad": False, "absent_clinvar": False, "in_roh_gt_10mb": roh}


def _partner(pid, role, sex, calls, assays=None):
    return {"partner_id": pid, "role": role, "sex": sex, "age": 28, "bmi": 23.5, "calls": calls,
            "assays": assays or {"2600": "initial", "11117": "initial"}}


def _doc(*couples):
    return {"contract_version": "1.0.0", "seed": 1, "synthetic": True, "couples": list(couples)}


V1 = {"couple_id": "V1", "relationship": {"type": "first_cousins", "paths": [[2, 2, "0"], [2, 2, "0"]]},
      "partners": [_partner("V1A", "A", "female", [_call(4827, "HBB", "c.92+5G>C")]),
                   _partner("V1B", "B", "male", [_call(4827, "HBB", "c.92+5G>C")])]}
V2 = {"couple_id": "V2", "relationship": {"type": "unrelated", "paths": []},
      "partners": [_partner("V2A", "A", "female", [_call(2600, "CYP21A2", "c.955C>T", "p.(Gln319Ter)")]),
                   _partner("V2B", "B", "male", [])]}
V3 = {"couple_id": "V3", "relationship": {"type": "first_cousins", "paths": [[2, 2, "0"], [2, 2, "0"]]},
      "partners": [_partner("V3A", "A", "female", [_call(11117, "SMN1", vtype="cnv_deletion")]),
                   _partner("V3B", "B", "male", [])]}
V4 = {"couple_id": "V4", "relationship": {"type": "unrelated", "paths": []},
      "partners": [_partner("V4A", "A", "female", [_call(6998, "MEFV", hgvs_p="p.(Ala744Ser)"),
                                                    _call(4284, "GJB2", "c.SYN35G>A")]),
                   _partner("V4B", "B", "male", [_call(34, "ABCA4", "c.5882G>A", "p.(Gly1961Glu)")])]}
V5 = {"couple_id": "V5", "relationship": {"type": "double_first_cousins", "paths": [[2, 2, "0"]] * 4},
      "partners": [_partner("V5A", "A", "female", [_call(2993, "DONSON", "c.SYN29939C>T", cls="VUS", roh=True)]),
                   _partner("V5B", "B", "male", [_call(2993, "DONSON", "c.SYN29939C>T", cls="VUS", roh=True)])],
      "family_history": [{"relative": "sibling's child", "finding": "unexplained infant death", "hpo": None}]}
ALL = [V1, V2, V3, V4, V5]


def _res(bundle, rtype):
    return [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == rtype]


def test_in_test_fixtures_match_contract():
    jsonschema.Draft202012Validator(cohort_schema()).validate(_doc(*ALL))


@pytest.mark.parametrize("couple", ALL, ids=lambda c: c["couple_id"])
def test_partner_bundles_validate(couple):
    for p in couple["partners"]:
        assert validate_bundle(build_partner_bundle(p)) == []


def test_variant_components_and_geno():
    b = build_partner_bundle(V2["partners"][0])
    var = next(o for o in _res(b, "Observation") if C.PROFILE_VARIANT in o["meta"]["profile"])
    comps = {c["code"]["coding"][0]["code"]: c for c in var["component"]}
    assert comps[C.LOINC_GENE_STUDIED[0]]["valueCodeableConcept"]["coding"][0] == {
        "system": "http://www.genenames.org", "code": "HGNC:2600", "display": "CYP21A2"}
    assert comps[C.LOINC_REF_ALLELE[0]]["valueString"] == "C"
    assert comps[C.LOINC_ALT_ALLELE[0]]["valueString"] == "T"
    assert [x["code"] for x in comps[C.LOINC_ALLELIC_STATE[0]]["valueCodeableConcept"]["coding"]] == ["LA6706-1", "GENO:0000135"]
    for k in (C.LOINC_GENOMIC_REF_SEQ, C.LOINC_COORDINATE_SYSTEM, C.LOINC_EXACT_START_END, C.LOINC_CODING_HGVS):
        assert k[0] in comps
    assert C.SYNTHETIC_COORD_NOTE in [n["text"] for n in var["note"]]
    hom = copy.deepcopy(V1["partners"][0])
    hom["calls"][0]["zygosity"] = "hom"
    var = next(o for o in _res(build_partner_bundle(hom), "Observation") if "component" in o and
               C.PROFILE_VARIANT in o["meta"]["profile"])
    assert any("GENO:0000136" in [x["code"] for x in c["valueCodeableConcept"]["coding"]]
               for c in var["component"] if c["code"]["coding"][0]["code"] == C.LOINC_ALLELIC_STATE[0])


def test_implication_derived_from_and_carrier_note():
    b = build_partner_bundle(V1["partners"][0])
    imp = next(o for o in _res(b, "Observation") if C.PROFILE_DIAGNOSTIC_IMPLICATION in o["meta"]["profile"])
    urls = {e["fullUrl"]: e["resource"] for e in b["entry"]}
    assert C.PROFILE_VARIANT in urls[imp["derivedFrom"][0]["reference"]]["meta"]["profile"]
    assert C.CARRIER_NOTE in [n["text"] for n in imp["note"]]
    # VUS: no "carrier" wording
    vb = build_partner_bundle(V5["partners"][0])
    vimp = next(o for o in _res(vb, "Observation") if C.PROFILE_DIAGNOSTIC_IMPLICATION in o["meta"]["profile"])
    assert C.CARRIER_NOTE not in [n["text"] for n in vimp["note"]]
    assert validate_bundle(vb) == []


def test_report_specimen_version_amended():
    b = build_partner_bundle(V1["partners"][0])
    dr = _res(b, "DiagnosticReport")[0]
    assert C.PROFILE_GENOMIC_REPORT in dr["meta"]["profile"] and dr["status"] == "final"
    sp = _res(b, "Specimen")[0]
    assert sp["type"] and sp["receivedTime"]
    b2 = build_partner_bundle(V1["partners"][0], version=2)
    dr2 = _res(b2, "DiagnosticReport")[0]
    assert dr2["status"] == "amended" and dr2["meta"]["versionId"] == "2"
    assert validate_bundle(b2) == []


@pytest.mark.parametrize("couple,gene", [(V2, 2600), (V3, 11117)], ids=["CYP21A2", "SMN1"])
def test_complex_locus_recommended_action_task(couple, gene):
    b = build_partner_bundle(couple["partners"][0])
    dr = _res(b, "DiagnosticReport")[0]
    tasks = _res(b, "Task")
    assert len(tasks) == 1 and f"HGNC:{gene}" in tasks[0]["description"]
    assert dr["extension"][0]["url"] == C.EXT_RECOMMENDED_ACTION
    assert dr["extension"][0]["valueReference"]["reference"] == f"urn:uuid:{tasks[0]['id']}"


def test_no_task_for_non_complex_or_already_confirmed():
    assert _res(build_partner_bundle(V1["partners"][0]), "Task") == []
    p = copy.deepcopy(V2["partners"][0])
    p["assays"]["2600"] = "confirmatory"
    assert _res(build_partner_bundle(p), "Task") == []


def test_confirm_negative_ignored_without_disclosure_consent():
    b = build_partner_bundle(V2["partners"][1], confirm_negative_hgnc_ids=[2600])
    assert _res(b, "Task") == [] and "CYP21A2" not in json.dumps(b)
    assert validate_bundle(b) == []


def test_confirm_negative_task_for_screen_negative_partner():
    b = build_partner_bundle(V2["partners"][1], confirm_negative_hgnc_ids=[2600, 4827],
                             disclosure_consent_ref="SYN-CONSENT-0001")
    tasks = _res(b, "Task")
    assert len(tasks) == 1 and "HGNC:2600" in tasks[0]["description"]  # HBB is not a complex locus
    ref = tasks[0]["input"][0]["valueReference"]
    assert ref["type"] == "Consent" and ref["identifier"]["value"] == "SYN-CONSENT-0001"
    assert validate_bundle(b) == []
    assert _res(build_partner_bundle(V2["partners"][1]), "Task") == []  # default: nothing disclosed


def test_partner_bundle_holds_only_own_data():
    for couple in ALL:
        a, b = couple["partners"]
        text = json.dumps(build_partner_bundle(a))
        assert b["partner_id"] not in text
        for c in b["calls"]:
            if c["hgnc_id"] not in {x["hgnc_id"] for x in a["calls"]}:
                assert c["gene"] not in text and f"HGNC:{c['hgnc_id']}\"" not in text


def _gene_tokens(call):
    return [call["gene"], f'"HGNC:{call["hgnc_id"]}"'] + [x for x in (call["hgvs_c"], call["hgvs_p"]) if x]


def test_couple_report_v4_empty_intersection_leaks_nothing():
    cr = build_couple_report(V4, shared_hgnc_ids=[])
    assert validate_bundle(cr) == []
    text = json.dumps(cr)
    for p in V4["partners"]:
        for c in p["calls"]:
            for tok in _gene_tokens(c):
                assert tok not in text
    assert "result" not in _res(cr, "DiagnosticReport")[0]


def test_couple_report_only_shared_genes():
    couple = copy.deepcopy(V4)
    couple["partners"][1]["calls"].append(_call(6998, "MEFV", hgvs_p="p.(Ala744Ser)"))
    cr = build_couple_report(couple, shared_hgnc_ids=[6998])
    assert validate_bundle(cr) == []
    text = json.dumps(cr)
    assert "MEFV" in text
    for tok in _gene_tokens(V4["partners"][0]["calls"][1]) + _gene_tokens(V4["partners"][1]["calls"][0]):
        assert tok not in text  # GJB2 (A only) and ABCA4 (B only) never appear


def test_couple_report_structure_v1():
    cr = build_couple_report(V1, shared_hgnc_ids=[4827])
    assert validate_bundle(cr) == []
    dr = _res(cr, "DiagnosticReport")[0]
    group = _res(cr, "Group")[0]
    assert dr["subject"]["reference"] == f"urn:uuid:{group['id']}" and len(group["member"]) == 2
    urls = {e["fullUrl"]: e["resource"] for e in cr["entry"]}
    for r in dr["result"]:
        grp = urls[r["reference"]]
        assert grp["hasMember"]
        for m in grp["hasMember"]:
            assert m not in dr["result"]
            assert C.PROFILE_DIAGNOSTIC_IMPLICATION in urls[m["reference"]]["meta"]["profile"]


def test_validator_catches_dangling_and_duplicates():
    cr = build_couple_report(V1, shared_hgnc_ids=[4827])
    bad = copy.deepcopy(cr)
    imp = next(r for r in _res(bad, "Observation") if C.PROFILE_DIAGNOSTIC_IMPLICATION in r["meta"]["profile"])
    imp["derivedFrom"] = [{"reference": "urn:uuid:00000000-0000-4000-8000-000000000000"}]
    assert any("dangling" in e for e in validate_bundle(bad))
    bad2 = copy.deepcopy(cr)
    dr = _res(bad2, "DiagnosticReport")[0]
    grp = next(r for r in _res(bad2, "Observation") if "hasMember" in r)
    dr["result"].append(grp["hasMember"][0])
    assert any("both DiagnosticReport.result and hasMember" in e for e in validate_bundle(bad2))
    bad3 = copy.deepcopy(build_partner_bundle(V2["partners"][0]))
    var = next(r for r in _res(bad3, "Observation") if C.PROFILE_VARIANT in r["meta"]["profile"])
    var["component"] = [c for c in var["component"] if c["code"]["coding"][0]["code"] != C.LOINC_GENE_STUDIED[0]]
    assert any("missing components" in e for e in validate_bundle(bad3))
    bad4 = copy.deepcopy(build_partner_bundle(V2["partners"][0]))
    _res(bad4, "Observation")[0]["status"] = 123
    assert any(e.startswith("roundtrip") for e in validate_bundle(bad4))


def test_deterministic():
    assert build_partner_bundle(V1["partners"][0]) == build_partner_bundle(V1["partners"][0])


# ---------------- Phenopackets / Pedigree ----------------
@pytest.mark.parametrize("couple", ALL, ids=lambda c: c["couple_id"])
def test_phenopackets_validate(couple):
    for p in couple["partners"]:
        packet = build_phenopacket(p)
        assert validate_phenopacket(packet) == []
        d = to_dict(packet)
        assert d["subject"]["id"] == p["partner_id"]
        other = next(x for x in couple["partners"] if x is not p)
        assert other["partner_id"] not in json.dumps(d)


def test_phenopacket_content():
    d = to_dict(build_phenopacket(V2["partners"][0], features=[("HP:0000001", "x", False), ("HP:0000002", "y", True)]))
    assert [f.get("excluded", False) for f in d["phenotypicFeatures"]] == [False, True]
    gi = d["interpretations"][0]["diagnosis"]["genomicInterpretations"][0]
    vd = gi["variantInterpretation"]["variationDescriptor"]
    assert vd["geneContext"]["valueId"] == "HGNC:2600"
    assert vd["allelicState"]["id"] == "GENO:0000135"
    assert C.CARRIER_NOTE in d["interpretations"][0]["summary"]
    assert "not a diagnosis" in d["interpretations"][0]["summary"]
    assert d["measurements"][0]["value"]["quantity"]["unit"]["id"] == "UCUM:kg/m2"
    assert d["metaData"]["phenopacketSchemaVersion"] == "2.0"


def test_phenopacket_validator_catches_problems():
    p = build_phenopacket(V1["partners"][0], features=[("HP:0000001", "x", False), ("HP:0000002", "y", False)])
    assert validate_phenopacket(p, ancestors={"HP:0000002": {"HP:0000001"}}) == ["phenopacket: term and its ancestor both present"]
    p.phenotypic_features.append(phenotypic_feature("HP:0000001", "x"))
    assert "phenopacket: duplicate phenotypic feature term" in validate_phenopacket(p)
    q = build_phenopacket(V1["partners"][0])
    q.phenotypic_features.append(phenotypic_feature("HP:0000001", "x"))  # HP not declared in metaData
    assert any("not declared" in e for e in validate_phenopacket(q))


@pytest.mark.parametrize("couple", ALL, ids=lambda c: c["couple_id"])
def test_pedigrees(couple):
    ped = build_pedigree(couple)
    assert validate_pedigree(ped, couple) == []


def test_pedigree_shapes():
    assert len(build_pedigree(V2).persons) == 2
    assert len(build_pedigree(V1).persons) == 2 + 4 + 2  # GF, GM, 2 fathers, 2 mothers, partners
    v5 = build_pedigree(V5)
    a = next(p for p in v5.persons if p.individual_id == "V5A")
    b = next(p for p in v5.persons if p.individual_id == "V5B")
    persons = {p.individual_id: p for p in v5.persons}
    # double first cousins: both pairs of grandparents shared
    assert {persons[a.paternal_id].paternal_id, persons[a.maternal_id].paternal_id} == \
           {persons[b.paternal_id].paternal_id, persons[b.maternal_id].paternal_id}
    sc = copy.deepcopy(V1)
    sc["relationship"]["type"] = "second_cousins"
    assert validate_pedigree(build_pedigree(sc), sc) == []


def test_family_carries_no_partner_genotypes():
    fam = build_family(V5)
    d = json.dumps(to_dict(fam))
    assert "DONSON" not in d and "interpretations" not in d
    assert fam.proband.subject.id == "V5-REL0"


def test_in_test_cohort_validates():
    out = validate_cohort(_doc(*ALL))
    assert out["errors"] == [] and out["counts"]["couples"] == 5


# ---------------- Real data-synth outputs (when present) ----------------
_GOLDEN_FILES = sorted(GOLDEN.glob("V*.json")) if GOLDEN.exists() else []


@pytest.mark.skipif(not _GOLDEN_FILES, reason="tests/golden/cohort/V*.json not produced yet (data-synth)")
@pytest.mark.parametrize("path", _GOLDEN_FILES, ids=lambda p: p.stem)
def test_real_vignettes_validate(path):
    out = validate_cohort(json.loads(path.read_text(encoding="utf-8")))
    assert out["errors"] == [], out["errors"][:10]


@pytest.mark.skipif(not (GOLDEN / "V4.json").exists(), reason="V4.json not produced yet (data-synth)")
def test_real_v4_couple_report_no_leak():
    couple = json.loads((GOLDEN / "V4.json").read_text(encoding="utf-8"))["couples"][0]
    text = json.dumps(build_couple_report(couple, shared_hgnc_ids=[]))
    for p in couple["partners"]:
        for c in p["calls"]:
            assert not re.search(rf'"{re.escape(c["gene"])}"|HGNC:{c["hgnc_id"]}"', text)


@pytest.mark.skipif(not COHORT.exists(), reason="services/synth/out/cohort.json not produced yet (data-synth)")
def test_real_cohort_sweep():
    out = validate_cohort(json.loads(COHORT.read_text(encoding="utf-8")))
    assert out["errors"] == [], out["errors"][:10]
    assert out["counts"]["partner_bundles"] == 2 * out["counts"]["couples"]


@pytest.mark.parametrize("zyg,code", [("het", "GENO:0000135"), ("hom", "GENO:0000136"), ("hemi", "GENO:0000134")])
def test_allelic_state_geno_decision_15(zyg, code):
    """DECISIONS #15. 'hemi' is outside the cohort contract enum; builder-level fixture only."""
    p = copy.deepcopy(V1["partners"][0])
    p["calls"][0]["zygosity"] = zyg
    b = build_partner_bundle(p)
    assert validate_bundle(b) == []
    assert f'"{code}"' in json.dumps(b)
    pk = build_phenopacket(p)
    assert validate_phenopacket(pk) == []
    vd = to_dict(pk)["interpretations"][0]["diagnosis"]["genomicInterpretations"][0]["variantInterpretation"]["variationDescriptor"]
    assert vd["allelicState"]["id"] == code


def test_ig_300_conformance_choices():
    """Profile/binding choices taken from the downloaded IG 3.0.0 package (P4)."""
    b = build_partner_bundle(V2["partners"][0])
    dr = _res(b, "DiagnosticReport")[0]
    assert dr["meta"]["profile"] == ["http://hl7.org/fhir/uv/genomics-reporting/StructureDefinition/genomic-report"]
    task = _res(b, "Task")[0]
    assert task["meta"]["profile"][0].endswith("/followup-recommendation")
    imp = next(o for o in _res(b, "Observation") if C.PROFILE_DIAGNOSTIC_IMPLICATION in o["meta"]["profile"])
    assert task["reasonReference"]["reference"] == f"urn:uuid:{imp['id']}"
    var = next(o for o in _res(b, "Observation") if C.PROFILE_VARIANT in o["meta"]["profile"])
    hg = [c for c in var["component"] if c["code"]["coding"][0]["code"] == C.LOINC_CODING_HGVS[0]][0]
    assert hg["valueCodeableConcept"]["coding"][0]["system"] == "http://varnomen.hgvs.org"
    # synthetic placeholder HGVS is never emitted as an HGVS code
    v5 = json.dumps(build_partner_bundle(V5["partners"][0]))
    assert "c.SYN" not in v5


# ---------------- DECISIONS #39: transcript-anchored HGVS ----------------
def _hgvs_codes(bundle):
    return [c["valueCodeableConcept"]["coding"][0]["code"] for o in _res(bundle, "Observation")
            for c in o.get("component", []) if c["code"]["coding"][0]["code"] in (C.LOINC_CODING_HGVS[0], C.LOINC_PROTEIN_HGVS[0])]


def test_founder_hgvs_uses_panel_transcript():
    b = build_partner_bundle(V2["partners"][0])  # CYP21A2 founder c.955C>T, refseq null
    assert _hgvs_codes(b) == ["NM_000500.9:c.955C>T"]
    var = next(o for o in _res(b, "Observation") if C.PROFILE_VARIANT in o["meta"]["profile"])
    tx = [c for c in var["component"] if c["code"]["coding"][0]["code"] == C.LOINC_TRANSCRIPT_REF_SEQ[0]]
    assert tx[0]["valueCodeableConcept"]["coding"][0]["code"] == "NM_000500.9"
    assert any("p.(Gln319Ter)" in n["text"] for n in var["note"])  # p. kept as note, not coded
    exprs = to_dict(build_phenopacket(V2["partners"][0]))["interpretations"][0]["diagnosis"][
        "genomicInterpretations"][0]["variantInterpretation"]["variationDescriptor"]["expressions"]
    assert {"syntax": "hgvs.c", "value": "NM_000500.9:c.955C>T"} in exprs
    assert _hgvs_codes(build_partner_bundle(V1["partners"][0])) == ["NM_000518.5:c.92+5G>C"]
    assert _hgvs_codes(build_partner_bundle(V4["partners"][1])) == ["NM_000350.3:c.5882G>A"]


def test_call_refseq_overrides_panel_transcript():
    p = copy.deepcopy(V2["partners"][0])
    p["calls"][0]["refseq"] = "NM_999999.1"
    assert _hgvs_codes(build_partner_bundle(p)) == ["NM_999999.1:c.955C>T"]


def test_no_hgvs_for_synthetic_or_unanchored_variants():
    for p in (V5["partners"][0], V4["partners"][0]):  # DONSON c.SYN…, GJB2 c.SYN… + MEFV p.-only
        b = build_partner_bundle(p)
        assert _hgvs_codes(b) == [] and "SYN" not in json.dumps(b).replace("SYNTHETIC", "")
        d = json.dumps(to_dict(build_phenopacket(p)))
        assert "c.SYN" not in d
        assert validate_bundle(b) == []
    q = copy.deepcopy(V2["partners"][0])
    q["calls"][0]["hgvs_c"] = "c.100A>G"  # not a founder, no refseq -> no accession -> no HGVS
    assert _hgvs_codes(build_partner_bundle(q)) == []
