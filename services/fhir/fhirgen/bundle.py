"""FHIR R4 GenomicReport bundles (R-FHIR-1; source §2.2, §3.1).

Input is a partner dict / couple dict from a data-synth cohort document (contracts/cohort.schema.json).
No probability arithmetic happens here (P-02); this module only serializes calls.
Output dicts are passed through the fhir.resources.R4B models before being returned.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Iterable

from fhir.resources.R4B import get_fhir_model_class
from fhir.resources.R4B.bundle import Bundle

from . import constants as C
from .panel import coding_transcript, gene_info, is_synthetic_hgvs

_NS = uuid.UUID("6f1b8c1e-2c1a-4e55-9d0e-5e7a1c0ffee0")  # fixed namespace -> deterministic ids
_SNV = re.compile(r"^c\.(?:SYN)?[0-9+\-*_]*([ACGT]+)>([ACGT]+)$")


def _uid(*parts: object) -> str:
    return str(uuid.uuid5(_NS, "|".join(str(p) for p in parts)))


def _url(rid: str) -> str:
    return f"urn:uuid:{rid}"


def _ref(rid: str) -> dict:
    return {"reference": _url(rid)}


def _meta(profile: str | None = None, version: int | None = None) -> dict:
    m: dict = {"tag": [dict(C.SYNTHETIC_TAG)]}
    if profile:
        m["profile"] = [profile]
    if version is not None:
        m["versionId"] = str(version)
    return m


def _cc(system: str, code_display: tuple[str, str]) -> dict:
    code, display = code_display
    return {"coding": [{"system": system, "code": code, "display": display}]}


def _loinc(code_display: tuple[str, str]) -> dict:
    return _cc(C.LOINC, code_display)


def _lab_category() -> list[dict]:
    return [
        {"coding": [{"system": C.OBS_CATEGORY, "code": "laboratory"}]},
        {"coding": [{"system": C.V2_0074, "code": "GE", "display": "Genetics"}]},
    ]


def _lab_rid() -> str:
    return _uid("SYNTHETIC-LAB")


def _lab() -> dict:
    return {"resourceType": "Organization", "id": _lab_rid(), "meta": _meta(), "name": C.SYNTHETIC_LAB_NAME}


def _placeholder_start(call: dict) -> int:
    """Deterministic SYNTHETIC placeholder coordinate (not a real genomic position)."""
    key = f"{call['hgnc_id']}|{call.get('hgvs_c')}|{call.get('hgvs_p')}|{call['variant_type']}"
    return 1 + int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 10_000_000


def _ref_alt(call: dict) -> tuple[str, str]:
    m = _SNV.match(call.get("hgvs_c") or "")
    if m:
        return m.group(1), m.group(2)
    return "N", "N"  # SYNTHETIC placeholder, flagged in Observation.note


def _variant_obs(rid: str, patient_rid: str, specimen_rid: str, call: dict) -> dict:
    gene = gene_info(call["hgnc_id"], call["gene"])
    comps: list[dict] = [
        {"code": _loinc(C.LOINC_GENE_STUDIED),
         "valueCodeableConcept": {"coding": [{"system": C.HGNC_SYSTEM, "code": f"HGNC:{call['hgnc_id']}",
                                              "display": gene["symbol"]}]}},
    ]
    refseq = call.get("refseq")
    tx = coding_transcript(call)
    if refseq and refseq.startswith(("NC_", "NG_", "LRG_")):
        comps.append({"code": _loinc(C.LOINC_GENOMIC_REF_SEQ),
                      "valueCodeableConcept": {"coding": [{"system": C.REFSEQ_SYSTEM, "code": refseq}]}})
    else:
        comps.append({"code": _loinc(C.LOINC_GENOMIC_REF_SEQ),
                      "valueCodeableConcept": {"text": "SYNTHETIC placeholder genomic reference sequence"}})
    if tx:
        comps.append({"code": _loinc(C.LOINC_TRANSCRIPT_REF_SEQ),
                      "valueCodeableConcept": {"coding": [{"system": C.REFSEQ_SYSTEM, "code": tx}]}})
    start = _placeholder_start(call)
    comps += [
        {"code": _loinc(C.LOINC_COORDINATE_SYSTEM), "valueCodeableConcept": _loinc(C.COORD_ONE_BASED)},
        {"code": _loinc(C.LOINC_EXACT_START_END),
         "valueRange": {"low": {"value": start}, "high": {"value": start}}},
    ]
    if call["variant_type"] in ("snv", "indel"):
        ref, alt = _ref_alt(call)
        comps += [
            {"code": _loinc(C.LOINC_REF_ALLELE), "valueString": ref},
            {"code": _loinc(C.LOINC_ALT_ALLELE), "valueString": alt},
        ]
    comps.append({"code": _loinc(C.LOINC_DNA_CHANGE_TYPE),
                  "valueCodeableConcept": _cc(C.SO_SYSTEM, C.DNA_CHANGE_TYPE[call["variant_type"]])})
    # HGVS is bound (required) to varnomen codes, which need an accession (DECISIONS #39):
    # c.HGVS is emitted only as "<transcript>:c.…"; synthetic c.SYN… variants emit no HGVS.
    # p.HGVS has no NP_ accession available, so it is carried as a note, not as coded HGVS.
    hgvs_c, hgvs_p = call.get("hgvs_c"), call.get("hgvs_p")
    if tx:
        comps.append({"code": _loinc(C.LOINC_CODING_HGVS),
                      "valueCodeableConcept": {"coding": [{"system": C.HGVS_SYSTEM, "code": f"{tx}:{hgvs_c}"}]}})
    notes = [{"text": C.SYNTHETIC_COORD_NOTE}]
    if hgvs_p and not is_synthetic_hgvs(hgvs_p):
        notes.append({"text": f"Protein change (not coded: no protein accession available): {hgvs_p}"})
    zyg = call["zygosity"]
    comps.append({"code": _loinc(C.LOINC_ALLELIC_STATE), "valueCodeableConcept": {"coding": [
        {"system": C.LOINC, "code": C.ALLELIC_STATE_LOINC[zyg][0], "display": C.ALLELIC_STATE_LOINC[zyg][1]},
        {"system": C.GENO_SYSTEM, "code": C.ALLELIC_STATE[zyg][0], "display": C.ALLELIC_STATE[zyg][1]}]}})
    return {
        "resourceType": "Observation", "id": rid, "meta": _meta(C.PROFILE_VARIANT),
        "status": "final", "category": _lab_category(), "code": _loinc(C.LOINC_VARIANT),
        "subject": _ref(patient_rid), "specimen": _ref(specimen_rid),
        "effectiveDateTime": C.SYNTHETIC_RECEIVED_TIME, "performer": [_ref(_lab_rid())],
        "valueCodeableConcept": _loinc(C.VARIANT_PRESENT),
        "note": notes,
        "component": comps,
    }


def _implication_obs(rid: str, patient_rid: str, variant_rid: str, call: dict) -> dict:
    gene = gene_info(call["hgnc_id"], call["gene"])
    comps = [{"code": _loinc(C.LOINC_CLIN_SIG),
              "valueCodeableConcept": _cc(C.LOINC, C.CLIN_SIG_ANSWERS[call["classification"]])}]
    if gene.get("condition"):
        comps.append({"code": _loinc(C.LOINC_ASSOCIATED_PHENOTYPE),
                      "valueCodeableConcept": {"text": gene["condition"]}})
    notes = []
    # All panel genes are autosomal recessive (source §Intro: 570 genes, >840 AR conditions).
    if call["classification"] in ("P", "LP"):
        notes.append({"text": C.CARRIER_NOTE})
    notes.append({"text": C.NOT_DIAGNOSIS_NOTE})
    return {
        "resourceType": "Observation", "id": rid, "meta": _meta(C.PROFILE_DIAGNOSTIC_IMPLICATION),
        "status": "final", "category": _lab_category(),
        "code": {"coding": [{"system": C.TBD_CODES, "code": "diagnostic-implication",
                             "display": "Diagnostic Implication"}]},
        "subject": _ref(patient_rid), "derivedFrom": [_ref(variant_rid)],
        "effectiveDateTime": C.SYNTHETIC_ISSUED_TIME, "performer": [_ref(_lab_rid())],
        "note": notes, "component": comps,
    }


def _task(rid: str, patient_rid: str, hgnc_id: int, symbol: str, variant_rid: str | None,
          implication_rid: str | None = None) -> dict:
    t = {
        "resourceType": "Task", "id": rid, "meta": _meta(C.PROFILE_FOLLOWUP_TASK),
        "status": "requested", "intent": "proposal",
        "code": {"text": "Orthogonal confirmatory testing at a technically complex locus"},
        "description": (f"Confirmatory testing for {symbol} (HGNC:{hgnc_id}) before any reassurance "
                        "or reproductive decision-making."),
        "for": _ref(patient_rid),
    }
    if variant_rid:
        t["focus"] = _ref(variant_rid)
    if implication_rid:
        t["reasonReference"] = _ref(implication_rid)
    return t


def _patient(rid: str, partner: dict) -> dict:
    return {
        "resourceType": "Patient", "id": rid, "meta": _meta(),
        "identifier": [{"system": C.SYNTHETIC_ID_SYSTEM, "value": partner["partner_id"]}],
        "gender": partner["sex"],
    }


def _validated(bundle: dict) -> dict:
    """Pass every resource and the bundle through the R4B models; return the model's JSON form."""
    for e in bundle["entry"]:
        get_fhir_model_class(e["resource"]["resourceType"]).model_validate(e["resource"])
    return json.loads(Bundle.model_validate(bundle).model_dump_json())


def _bundle(bid: str, resources: list[dict]) -> dict:
    return {
        "resourceType": "Bundle", "id": bid, "meta": _meta(), "type": "collection",
        "timestamp": C.SYNTHETIC_ISSUED_TIME,
        "entry": [{"fullUrl": _url(r["id"]), "resource": r} for r in resources],
    }


def build_partner_bundle(partner: dict, *, version: int = 1,
                         confirm_negative_hgnc_ids: Iterable[int] = (),
                         disclosure_consent_ref: str | None = None) -> dict:
    """GenomicReport bundle for ONE partner. Contains only that partner's data (P-06).

    version > 1 marks a reissue -> DiagnosticReport.status = amended.
    confirm_negative_hgnc_ids: complex-locus genes where this partner screened negative (e.g. V2 B).
    Such a Task reveals the other partner's carrier gene, so it is created ONLY when
    `disclosure_consent_ref` (id of the carrier partner's disclosure Consent) is given (DECISIONS #16,
    provisional). Without it the IDs are ignored - fail closed. Unknown / non-complex genes are ignored.
    """
    pid = partner["partner_id"]
    patient_rid, specimen_rid, report_rid = _uid(pid, "Patient"), _uid(pid, "Specimen"), _uid(pid, "Report")
    resources: list[dict] = [_patient(patient_rid, partner), _lab(), {
        "resourceType": "Specimen", "id": specimen_rid, "meta": _meta(),
        "type": _cc(C.V2_0487, C.SPECIMEN_TYPE), "receivedTime": C.SYNTHETIC_RECEIVED_TIME,
        "subject": _ref(patient_rid),
    }]
    result_rids: list[str] = []
    tasks: list[dict] = []
    own_hgnc = set()
    for i, call in enumerate(partner["calls"]):
        v_rid, d_rid = _uid(pid, "Variant", i), _uid(pid, "Implication", i)
        resources.append(_variant_obs(v_rid, patient_rid, specimen_rid, call))
        resources.append(_implication_obs(d_rid, patient_rid, v_rid, call))
        result_rids += [d_rid, v_rid]
        own_hgnc.add(call["hgnc_id"])
        gene = gene_info(call["hgnc_id"], call["gene"])
        stage = partner["assays"].get(str(call["hgnc_id"]))
        if gene.get("complex_locus") and stage != "confirmatory":
            tasks.append(_task(_uid(pid, "Task", i), patient_rid, call["hgnc_id"], gene["symbol"], v_rid, d_rid))
    negatives = set(confirm_negative_hgnc_ids) - own_hgnc if disclosure_consent_ref else set()
    for h in sorted(negatives):
        gene = gene_info(h, f"HGNC:{h}")
        if gene.get("complex_locus") and partner["assays"].get(str(h)) != "confirmatory":
            t = _task(_uid(pid, "TaskNeg", h), patient_rid, h, gene["symbol"], None)
            # Logical reference (identifier only): the Consent lives in the consent service, not here.
            t["input"] = [{"type": {"text": "disclosure-consent"},
                           "valueReference": {"type": "Consent", "identifier": {
                               "system": C.CONSENT_ID_SYSTEM, "value": disclosure_consent_ref}}}]
            tasks.append(t)
    resources += tasks
    report = {
        "resourceType": "DiagnosticReport", "id": report_rid,
        "meta": _meta(C.PROFILE_GENOMIC_REPORT, version),
        "identifier": [{"system": C.SYNTHETIC_ID_SYSTEM, "value": f"{pid}-genomic-report-v{version}"}],
        "status": "final" if version == 1 else "amended",
        "category": [{"coding": [{"system": C.V2_0074, "code": "GE", "display": "Genetics"}]}],
        "code": _loinc(C.LOINC_GENETIC_REPORT),
        "subject": _ref(patient_rid), "issued": C.SYNTHETIC_ISSUED_TIME,
        "specimen": [_ref(specimen_rid)],
    }
    if tasks:
        report["extension"] = [{"url": C.EXT_RECOMMENDED_ACTION, "valueReference": _ref(t["id"])} for t in tasks]
    if result_rids:
        report["result"] = [_ref(r) for r in result_rids]
    resources.insert(0, report)
    return _validated(_bundle(_uid(pid, "Bundle", version), resources))


def build_couple_report(couple: dict, shared_hgnc_ids: Iterable[int], *, version: int = 1) -> dict:
    """Couple-level report (CodeX GenomeX prenatal-carrier pattern: partner observations nested under
    an overarching report). ONLY calls in `shared_hgnc_ids` (the consented APSI intersection) appear;
    every other gene of either partner is omitted entirely (P-06).

    Structure: DiagnosticReport(subject=Group of both partners).result -> one grouping Observation per
    partner -> hasMember DiagnosticImplication -> derivedFrom Variant. hasMember children are never
    listed in result.
    """
    shared = set(shared_hgnc_ids)
    cid = couple["couple_id"]
    group_rid, report_rid = _uid(cid, "Group"), _uid(cid, "CoupleReport", version)
    resources: list[dict] = [_lab()]
    members, result_rids = [], []
    for partner in couple["partners"]:
        pid = partner["partner_id"]
        patient_rid = _uid(cid, pid, "Patient")
        resources.append(_patient(patient_rid, partner))
        members.append({"entity": _ref(patient_rid)})
        child_rids = []
        for i, call in enumerate(partner["calls"]):
            if call["hgnc_id"] not in shared:
                continue
            v_rid, d_rid = _uid(cid, pid, "Variant", i), _uid(cid, pid, "Implication", i)
            v = _variant_obs(v_rid, patient_rid, "", call)
            v.pop("specimen")  # specimens are per-partner and not part of the couple report
            resources += [v, _implication_obs(d_rid, patient_rid, v_rid, call)]
            child_rids.append(d_rid)
        if child_rids:
            g_rid = _uid(cid, pid, "PartnerGroup")
            resources.append({
                "resourceType": "Observation", "id": g_rid, "meta": _meta(), "status": "final",
                "category": _lab_category(),
                "code": {"text": f"Partner {partner['role']} findings in consented shared genes"},
                "subject": _ref(patient_rid), "effectiveDateTime": C.SYNTHETIC_ISSUED_TIME,
                "performer": [_ref(_lab_rid())], "hasMember": [_ref(r) for r in child_rids],
            })
            result_rids.append(g_rid)
    group = {"resourceType": "Group", "id": group_rid, "meta": _meta(), "type": "person", "actual": True,
             "quantity": len(members), "member": members}
    report = {
        "resourceType": "DiagnosticReport", "id": report_rid,
        "meta": _meta(C.PROFILE_GENOMIC_REPORT, version),
        "identifier": [{"system": C.SYNTHETIC_ID_SYSTEM, "value": f"{cid}-couple-report-v{version}"}],
        "status": "final" if version == 1 else "amended",
        "category": [{"coding": [{"system": C.V2_0074, "code": "GE", "display": "Genetics"}]}],
        "code": _loinc(C.LOINC_GENETIC_REPORT),
        "subject": _ref(group_rid), "issued": C.SYNTHETIC_ISSUED_TIME,
    }
    if result_rids:
        report["result"] = [_ref(r) for r in result_rids]
    return _validated(_bundle(_uid(cid, "CoupleBundle", version), [report, group] + resources))
