"""GA4GH Phenopacket v2 + Pedigree (R-FHIR-1; source §2.2).

- build_phenopacket(partner): one packet per partner, that partner's data only (P-06).
- build_pedigree(couple): GA4GH Pedigree from relationship.type (structure only, no genotypes).
- build_family(couple): Family with pedigree + relatives' phenopackets from couple family_history.
  Partners' genomic interpretations are NOT placed in the Family (it is a couple-level artifact).

No Mondo IDs exist in the contracts, so diseases use a local SYN: placeholder namespace - TODO(verify).
Carrier status is not a diagnosis (P-17): interpretations carry that statement in their summary.
"""
from __future__ import annotations

from typing import Iterable

import phenopackets as pp
from google.protobuf.json_format import MessageToDict
from google.protobuf.timestamp_pb2 import Timestamp

from . import constants as C
from .panel import coding_transcript, gene_info, is_synthetic_hgvs

SCHEMA_VERSION = "2.0"
CREATED = "2026-01-12T06:00:00Z"  # fixed synthetic timestamp for determinism
UNPINNED = "unpinned-TODO(verify)"

RESOURCES = {
    "HP": ("hp", "human phenotype ontology", "http://purl.obolibrary.org/obo/hp.owl", "http://purl.obolibrary.org/obo/HP_"),
    "GENO": ("geno", "Genotype Ontology", "http://purl.obolibrary.org/obo/geno.owl", "http://purl.obolibrary.org/obo/GENO_"),
    "HGNC": ("hgnc", "HUGO Gene Nomenclature Committee", "https://www.genenames.org", "https://identifiers.org/hgnc:"),
    "SO": ("so", "Sequence Ontology", "http://purl.obolibrary.org/obo/so.owl", "http://purl.obolibrary.org/obo/SO_"),
    "LOINC": ("loinc", "Logical Observation Identifiers Names and Codes", "https://loinc.org", "https://loinc.org/"),
    "UCUM": ("ucum", "Unified Code for Units of Measure", "http://unitsofmeasure.org", "http://unitsofmeasure.org/"),
    "SYN": ("syn", "SYNTHETIC local placeholder terms (TODO(verify) map to Mondo)",
            "urn:synthetic:inherited-risk-demo", "urn:synthetic:inherited-risk-demo:"),
}

ACMG = {"P": pp.PATHOGENIC, "LP": pp.LIKELY_PATHOGENIC, "VUS": pp.UNCERTAIN_SIGNIFICANCE}
SEX = {"female": pp.FEMALE, "male": pp.MALE}


def _meta_data(prefixes: Iterable[str]) -> pp.MetaData:
    ts = Timestamp()
    ts.FromJsonString(CREATED)
    res = []
    for p in sorted(set(prefixes)):
        rid, name, url, iri = RESOURCES[p]
        res.append(pp.Resource(id=rid, name=name, url=url, version=UNPINNED, namespace_prefix=p, iri_prefix=iri))
    return pp.MetaData(created=ts, created_by="fhirgen (SYNTHETIC demo data)", resources=res,
                       phenopacket_schema_version=SCHEMA_VERSION)


def phenotypic_feature(hpo: str, label: str, excluded: bool = False) -> pp.PhenotypicFeature:
    return pp.PhenotypicFeature(type=pp.OntologyClass(id=hpo, label=label), excluded=excluded)


def _variation_descriptor(pid: str, idx: int, call: dict) -> pp.VariationDescriptor:
    gene = gene_info(call["hgnc_id"], call["gene"])
    tx = coding_transcript(call)  # DECISIONS #39; None for synthetic or unanchored variants
    exprs = []
    if tx:
        exprs.append(pp.Expression(syntax="hgvs.c", value=f"{tx}:{call['hgvs_c']}"))
    if call.get("hgvs_p") and not is_synthetic_hgvs(call["hgvs_p"]):
        exprs.append(pp.Expression(syntax="hgvs.p", value=call["hgvs_p"]))
    geno_id, geno_label = C.ALLELIC_STATE[call["zygosity"]]
    so_id, so_label = C.DNA_CHANGE_TYPE[call["variant_type"]]
    vd = pp.VariationDescriptor(
        id=f"{pid}-var-{idx}",
        label=f"{gene['symbol']} " + next((h for h in (call.get("hgvs_c"), call.get("hgvs_p"))
                                            if h and not is_synthetic_hgvs(h)), f"synthetic {so_label}"),
        gene_context=pp.GeneDescriptor(value_id=f"HGNC:{call['hgnc_id']}", symbol=gene["symbol"]),
        expressions=exprs,
        molecule_context=pp.genomic,
        allelic_state=pp.OntologyClass(id=geno_id, label=geno_label),
    )
    if call["variant_type"] == "cnv_deletion":
        vd.structural_type.CopyFrom(pp.OntologyClass(id=so_id, label=so_label))
    return vd


def build_phenopacket(partner: dict, features: Iterable[tuple[str, str, bool]] = ()) -> pp.Phenopacket:
    """Phenopacket v2 for ONE partner. `features` = (HPO id, label, excluded) about this partner only."""
    pid = partner["partner_id"]
    prefixes = {"GENO", "HGNC", "SYN"}
    subject = pp.Individual(id=pid, sex=SEX[partner["sex"]])
    subject.time_at_last_encounter.age.iso8601duration = f"P{partner['age']}Y"
    feats = [phenotypic_feature(h, label, ex) for h, label, ex in features]
    if feats:
        prefixes.add("HP")
    measurements = []
    if partner.get("bmi") is not None:
        prefixes |= {"LOINC", "UCUM"}
        m = pp.Measurement(assay=pp.OntologyClass(id="LOINC:39156-5", label="Body mass index (BMI) [Ratio]"))
        m.value.quantity.CopyFrom(pp.Quantity(unit=pp.OntologyClass(id="UCUM:kg/m2", label="kg/m2"),
                                              value=float(partner["bmi"])))
        # Reference range omitted: not stated in the source doc (P-20).
        measurements.append(m)
    interps = []
    for i, call in enumerate(partner["calls"]):
        gene = gene_info(call["hgnc_id"], call["gene"])
        vd = _variation_descriptor(pid, i, call)
        if call["variant_type"] == "cnv_deletion":
            prefixes.add("SO")
        gi = pp.GenomicInterpretation(
            subject_or_biosample_id=pid, interpretation_status=pp.GenomicInterpretation.UNKNOWN_STATUS,
            variant_interpretation=pp.VariantInterpretation(
                acmg_pathogenicity_classification=ACMG[call["classification"]], variation_descriptor=vd))
        summary = "Carrier screening finding for an autosomal recessive condition. " + C.NOT_DIAGNOSIS_NOTE
        if call["classification"] in ("P", "LP"):
            summary = f"{C.CARRIER_NOTE}. " + summary
        interps.append(pp.Interpretation(
            id=f"{pid}-interp-{i}", progress_status=pp.Interpretation.UNKNOWN_PROGRESS, summary=summary,
            diagnosis=pp.Diagnosis(
                disease=pp.OntologyClass(id=f"SYN:{call['hgnc_id']}",
                                         label=gene.get("condition") or f"{gene['symbol']}-related condition"),
                genomic_interpretations=[gi])))
    return pp.Phenopacket(id=f"{pid}-phenopacket", subject=subject, phenotypic_features=feats,
                          measurements=measurements, interpretations=interps, meta_data=_meta_data(prefixes))


# ---------------- Pedigree ----------------
def _person(fam: str, iid: str, sex, father: str = "", mother: str = "",
            affected=pp.Pedigree.Person.MISSING) -> pp.Pedigree.Person:
    return pp.Pedigree.Person(family_id=fam, individual_id=iid, paternal_id=father, maternal_id=mother,
                              sex=sex, affected_status=affected)


def build_pedigree(couple: dict) -> pp.Pedigree:
    """Pedigree for the couple from relationship.type. Linking parents are modelled as fathers
    (a synthetic structural choice; only the degree of relationship matters for this demo)."""
    cid = couple["couple_id"]
    a, b = sorted(couple["partners"], key=lambda p: p["role"])
    rel = couple["relationship"]["type"]
    M, F = pp.MALE, pp.FEMALE
    people: list[pp.Pedigree.Person] = []

    def add(iid, sex, father="", mother="", affected=pp.Pedigree.Person.MISSING):
        people.append(_person(cid, iid, sex, father, mother, affected))
        return iid

    def child_of(prefix, father, mother):
        """returns (father_id, mother_id) for a partner whose father descends from (father, mother)."""
        f = add(f"{cid}-{prefix}-F", M, father, mother)
        m = add(f"{cid}-{prefix}-M", F)
        return f, m

    if rel == "unrelated":
        pa = pb = ("", "")
    elif rel == "first_cousins":
        gf, gm = add(f"{cid}-GF", M), add(f"{cid}-GM", F)
        pa, pb = child_of("A", gf, gm), child_of("B", gf, gm)
    elif rel == "second_cousins":
        ggf, ggm = add(f"{cid}-GGF", M), add(f"{cid}-GGM", F)
        ga, gb = child_of("GA", ggf, ggm), child_of("GB", ggf, ggm)
        pa, pb = child_of("A", *ga), child_of("B", *gb)
    elif rel == "double_first_cousins":
        gf1, gm1 = add(f"{cid}-GF1", M), add(f"{cid}-GM1", F)
        gf2, gm2 = add(f"{cid}-GF2", M), add(f"{cid}-GM2", F)
        pa = (add(f"{cid}-A-F", M, gf1, gm1), add(f"{cid}-A-M", F, gf2, gm2))
        pb = (add(f"{cid}-B-F", M, gf1, gm1), add(f"{cid}-B-M", F, gf2, gm2))
    else:
        raise ValueError(f"unknown relationship type: {rel}")
    for partner, (f, m) in ((a, pa), (b, pb)):
        add(partner["partner_id"], SEX[partner["sex"]], f, m)
    for i, h in enumerate(couple.get("family_history") or []):
        add(f"{cid}-REL{i}", pp.UNKNOWN_SEX, affected=pp.Pedigree.Person.AFFECTED)
    return pp.Pedigree(persons=people)


def build_family(couple: dict) -> pp.Family:
    """Family: pedigree + phenopackets for affected relatives from couple family_history.
    Relatives' pedigree position is unknown from the free-text `relative` field, so they are unlinked."""
    cid = couple["couple_id"]
    rel_pps = []
    for i, h in enumerate(couple.get("family_history") or []):
        feats = [phenotypic_feature(h["hpo"], h["finding"])] if h.get("hpo") else []
        rel_pps.append(pp.Phenopacket(
            id=f"{cid}-REL{i}-phenopacket", subject=pp.Individual(id=f"{cid}-REL{i}", sex=pp.UNKNOWN_SEX),
            phenotypic_features=feats, meta_data=_meta_data({"HP"} if feats else set())))
    fam = pp.Family(id=f"{cid}-family", pedigree=build_pedigree(couple),
                    relatives=rel_pps[1:], meta_data=_meta_data({"HP"}))
    if rel_pps:
        fam.proband.CopyFrom(rel_pps[0])
    return fam


def to_dict(msg) -> dict:
    return MessageToDict(msg, preserving_proto_field_name=False)
