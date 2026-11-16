"""Validation harness for fhirgen output (R-FHIR-1; source §3.1).

Checks (P1 gate per DECISIONS #6 - the HL7 validator CLI is a P4 stretch and is NOT run here):
 (a) R4B model round-trip of the bundle and of every entry resource
 (b) reference walker: every reference resolves to an entry fullUrl; zero dangling hasMember/derivedFrom
 (c) no Observation listed in both DiagnosticReport.result and any hasMember
 (d) required profile components / elements present
 plus Phenopacket and Pedigree structural checks.

CLI: python -m fhirgen.validate <cohort.json> [more.json ...]
Prints counts only (no gene symbols or variants - P-12). Exit 1 on any error.
"""
from __future__ import annotations

import json
import sys
from typing import Iterable

import jsonschema
from fhir.resources.R4B import get_fhir_model_class
from fhir.resources.R4B.bundle import Bundle

from . import constants as C
from .bundle import build_couple_report, build_partner_bundle
from .panel import cohort_schema
from .phenopacket import RESOURCES, build_family, build_pedigree, build_phenopacket

VARIANT_REQUIRED = {C.LOINC_GENE_STUDIED[0], C.LOINC_GENOMIC_REF_SEQ[0], C.LOINC_COORDINATE_SYSTEM[0],
                    C.LOINC_EXACT_START_END[0], C.LOINC_ALLELIC_STATE[0]}
SEQ_CHANGE_TYPES = {C.DNA_CHANGE_TYPE["snv"][0], C.DNA_CHANGE_TYPE["indel"][0]}


# ---------------- FHIR ----------------
def _refs(obj, path: str = "") -> Iterable[tuple[str, str]]:
    """Yield (element path, reference string) for every Reference in a resource."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "reference" and isinstance(v, str):
                yield path, v
            else:
                yield from _refs(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _refs(v, path)


def _redact(e: Exception) -> str:
    """Error text without input values (values may hold gene/variant strings - P-12)."""
    if hasattr(e, "errors"):
        try:
            return "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['type']}" for x in e.errors())[:300]
        except Exception:  # noqa: BLE001
            pass
    return type(e).__name__


def check_roundtrip(bundle: dict) -> list[str]:
    errs = []
    try:
        if json.loads(Bundle.model_validate(bundle).model_dump_json()) != bundle:
            errs.append("roundtrip: Bundle changed after R4B model round-trip")
    except Exception as e:  # noqa: BLE001 - report any model error
        return [f"roundtrip: Bundle invalid: {_redact(e)}"]
    for i, e in enumerate(bundle.get("entry", [])):
        r = e.get("resource", {})
        try:
            cls = get_fhir_model_class(r.get("resourceType", ""))
            if json.loads(cls.model_validate(r).model_dump_json()) != r:
                errs.append(f"roundtrip: entry[{i}] {r.get('resourceType')} changed after round-trip")
        except Exception as ex:  # noqa: BLE001
            errs.append(f"roundtrip: entry[{i}] {r.get('resourceType')} invalid: {_redact(ex)}")
    return errs


def check_references(bundle: dict) -> list[str]:
    entries = bundle.get("entry", [])
    urls = [e.get("fullUrl") for e in entries]
    errs = [f"refs: duplicate fullUrl {u}" for u in {u for u in urls if urls.count(u) > 1}]
    known = set(urls)
    for i, e in enumerate(entries):
        r = e["resource"]
        if e.get("fullUrl") != f"urn:uuid:{r.get('id')}":
            errs.append(f"refs: entry[{i}] fullUrl does not match resource id")
        for path, ref in _refs(r):
            if ref not in known:
                errs.append(f"refs: entry[{i}] {r['resourceType']}.{path} dangling -> {ref}")
    return errs


def check_result_vs_hasmember(bundle: dict) -> list[str]:
    result, members = set(), set()
    for e in bundle.get("entry", []):
        r = e["resource"]
        if r["resourceType"] == "DiagnosticReport":
            result |= {x["reference"] for x in r.get("result", [])}
        if r["resourceType"] == "Observation":
            members |= {x["reference"] for x in r.get("hasMember", [])}
    return [f"structure: {ref} is in both DiagnosticReport.result and hasMember" for ref in sorted(result & members)]


def _codes(cc: dict) -> set[str]:
    return {c.get("code") for c in (cc or {}).get("coding", [])}


def check_required(bundle: dict) -> list[str]:
    errs = []
    entries = [e["resource"] for e in bundle.get("entry", [])]
    by_url = {e["fullUrl"]: e["resource"] for e in bundle.get("entry", [])}
    reports = [r for r in entries if r["resourceType"] == "DiagnosticReport"]
    if len(reports) != 1:
        errs.append(f"required: expected exactly 1 DiagnosticReport, found {len(reports)}")
    for r in reports:
        if C.PROFILE_GENOMIC_REPORT not in r.get("meta", {}).get("profile", []):
            errs.append("required: DiagnosticReport missing genomics-report profile")
        if not r.get("meta", {}).get("versionId") or not r.get("identifier"):
            errs.append("required: DiagnosticReport missing version/identifier")
        v = r.get("meta", {}).get("versionId")
        if v and v != "1" and r.get("status") != "amended":
            errs.append("required: reissued DiagnosticReport must have status=amended")
        for s in r.get("specimen", []):
            sp = by_url.get(s["reference"], {})
            if not sp.get("type") or not sp.get("receivedTime"):
                errs.append("required: Specimen missing type or receivedTime")
        for ext in r.get("extension", []):
            if ext.get("url") == C.EXT_RECOMMENDED_ACTION:
                t = by_url.get(ext.get("valueReference", {}).get("reference"), {})
                if t.get("resourceType") != "Task":
                    errs.append("required: recommended-action does not reference a Task")
    for r in entries:
        if r["resourceType"] != "Observation":
            continue
        prof = r.get("meta", {}).get("profile", [])
        comp_codes = {}
        for c in r.get("component", []):
            for code in _codes(c.get("code")):
                comp_codes[code] = c
        if C.PROFILE_VARIANT in prof:
            missing = VARIANT_REQUIRED - comp_codes.keys()
            if missing:
                errs.append(f"required: Variant {r['id']} missing components {sorted(missing)}")
            gene = comp_codes.get(C.LOINC_GENE_STUDIED[0], {})
            gcode = next(iter(gene.get("valueCodeableConcept", {}).get("coding", [])), {})
            if gcode.get("system") != C.HGNC_SYSTEM or not str(gcode.get("code", "")).removeprefix("HGNC:").isdigit():
                errs.append(f"required: Variant {r['id']} gene-studied is not a numeric HGNC ID")
            state = _codes(comp_codes.get(C.LOINC_ALLELIC_STATE[0], {}).get("valueCodeableConcept"))
            if not state & {v[0] for v in C.ALLELIC_STATE.values()}:
                errs.append(f"required: Variant {r['id']} allelic state not a GENO term")
            ctype = _codes(comp_codes.get(C.LOINC_DNA_CHANGE_TYPE[0], {}).get("valueCodeableConcept"))
            if ctype & SEQ_CHANGE_TYPES and not {C.LOINC_REF_ALLELE[0], C.LOINC_ALT_ALLELE[0]} <= comp_codes.keys():
                errs.append(f"required: Variant {r['id']} missing ref/alt allele")
        if C.PROFILE_DIAGNOSTIC_IMPLICATION in prof:
            if not r.get("derivedFrom"):
                errs.append(f"required: DiagnosticImplication {r['id']} has no derivedFrom")
            for d in r.get("derivedFrom", []):
                tgt = by_url.get(d["reference"], {})
                if C.PROFILE_VARIANT not in tgt.get("meta", {}).get("profile", []):
                    errs.append(f"required: DiagnosticImplication {r['id']} derivedFrom is not a Variant")
            sig = _codes(comp_codes.get(C.LOINC_CLIN_SIG[0], {}).get("valueCodeableConcept"))
            plp = {C.CLIN_SIG_ANSWERS["P"][0], C.CLIN_SIG_ANSWERS["LP"][0]}
            notes = [n.get("text") for n in r.get("note", [])]
            if sig & plp and C.CARRIER_NOTE not in notes:
                errs.append(f"required: P/LP DiagnosticImplication {r['id']} missing carrier note")
            if not sig & plp and C.CARRIER_NOTE in notes:
                errs.append(f"required: non-P/LP DiagnosticImplication {r['id']} must not say carrier")
    return errs


def validate_bundle(bundle: dict) -> list[str]:
    return check_roundtrip(bundle) + check_references(bundle) + check_result_vs_hasmember(bundle) + check_required(bundle)


# ---------------- Phenopacket / Pedigree ----------------
def _curies(msg) -> set[str]:
    """All OntologyClass ids used anywhere in a protobuf message."""
    out = set()
    for fd, val in msg.ListFields():
        repeated = fd.is_repeated if hasattr(fd, "is_repeated") else fd.label == fd.LABEL_REPEATED
        vals = val if repeated else [val]
        for v in vals:
            if hasattr(v, "ListFields"):
                if v.DESCRIPTOR.name == "OntologyClass":
                    out.add(v.id)
                elif v.DESCRIPTOR.name == "GeneDescriptor":
                    out.add(v.value_id)
                out |= _curies(v)
    return out


def validate_phenopacket(packet, ancestors: dict[str, set[str]] | None = None) -> list[str]:
    """Structural checks. `ancestors` maps HPO id -> its ancestor ids; the HPO ontology is not available
    offline, so without it only exact-duplicate terms are caught (phenopacket-tools is Java; P4)."""
    errs = []
    if not packet.id or not packet.subject.id:
        errs.append("phenopacket: missing id or subject.id")
    md = packet.meta_data
    if not md.HasField("created") or not md.created_by or md.phenopacket_schema_version != "2.0":
        errs.append("phenopacket: incomplete metaData")
    declared = {r.namespace_prefix for r in md.resources}
    for curie in _curies(packet):
        prefix = curie.split(":", 1)[0]
        if prefix not in declared:
            errs.append(f"phenopacket: prefix {prefix} used but not declared in metaData.resources")
        if prefix not in RESOURCES:
            errs.append(f"phenopacket: unknown prefix {prefix}")
    terms = [f.type.id for f in packet.phenotypic_features]
    if len(terms) != len(set(terms)):
        errs.append("phenopacket: duplicate phenotypic feature term")
    anc = ancestors or {}
    for t in terms:
        if anc.get(t, set()) & set(terms):
            errs.append("phenopacket: term and its ancestor both present")
    for m in packet.measurements:
        if m.value.HasField("quantity") and not m.value.quantity.unit.id:
            errs.append("phenopacket: measurement without unit")
    for it in packet.interpretations:
        for gi in it.diagnosis.genomic_interpretations:
            vd = gi.variant_interpretation.variation_descriptor
            if not vd.gene_context.value_id or not vd.allelic_state.id:
                errs.append(f"phenopacket: interpretation {it.id} variant lacks gene or allelic state")
            if gi.subject_or_biosample_id != packet.subject.id:
                errs.append(f"phenopacket: interpretation {it.id} refers to another subject")
    return errs


def validate_pedigree(ped, couple: dict) -> list[str]:
    import phenopackets as pp
    errs = []
    persons = {p.individual_id: p for p in ped.persons}
    if len(persons) != len(ped.persons):
        errs.append("pedigree: duplicate individual_id")
    for p in ped.persons:
        for pid, want, label in ((p.paternal_id, pp.MALE, "father"), (p.maternal_id, pp.FEMALE, "mother")):
            if pid and pid not in persons:
                errs.append(f"pedigree: {p.individual_id} {label} dangling")
            elif pid and persons[pid].sex != want:
                errs.append(f"pedigree: {p.individual_id} {label} has wrong sex")
            if pid == p.individual_id:
                errs.append("pedigree: self-parent")
    ids = [p["partner_id"] for p in couple["partners"]]
    if not all(i in persons for i in ids):
        return errs + ["pedigree: partner missing"]

    def ancestors(i, seen=None):
        seen = set() if seen is None else seen
        p = persons.get(i)
        for par in (p.paternal_id, p.maternal_id) if p else ():
            if par and par not in seen:
                seen.add(par)
                ancestors(par, seen)
        return seen

    shared = ancestors(ids[0]) & ancestors(ids[1])
    related = couple["relationship"]["type"] != "unrelated"
    if related and not shared:
        errs.append("pedigree: related couple has no common ancestor")
    if not related and shared:
        errs.append("pedigree: unrelated couple shares an ancestor")
    return errs


# ---------------- Cohort driver ----------------
def _test_intersection(couple: dict) -> set[int]:
    """Harness-only stand-in for the APSI result (set intersection of P/LP genes) so the couple report
    path is exercised. Production couple reports must take the intersection from privacy.apsi."""
    a, b = ([{c["hgnc_id"] for c in p["calls"] if c["classification"] in ("P", "LP")} for p in couple["partners"]])
    return a & b


def validate_cohort(doc: dict) -> dict:
    counts = {"couples": 0, "partner_bundles": 0, "couple_reports": 0, "phenopackets": 0,
              "pedigrees": 0, "families": 0, "resources": 0, "errors": 0}
    errors: list[str] = []
    for e in jsonschema.Draft202012Validator(cohort_schema()).iter_errors(doc):
        errors.append(f"cohort schema: {e.json_path} fails {e.validator}")
    if errors:
        counts["errors"] = len(errors)
        return {"counts": counts, "errors": errors}
    for couple in doc["couples"]:
        cid = couple["couple_id"]
        counts["couples"] += 1
        for partner in couple["partners"]:
            b = build_partner_bundle(partner)
            counts["partner_bundles"] += 1
            counts["resources"] += len(b["entry"])
            errors += [f"{partner['partner_id']} bundle: {x}" for x in validate_bundle(b)]
            errors += [f"{partner['partner_id']} phenopacket: {x}" for x in validate_phenopacket(build_phenopacket(partner))]
            counts["phenopackets"] += 1
        cr = build_couple_report(couple, _test_intersection(couple))
        counts["couple_reports"] += 1
        counts["resources"] += len(cr["entry"])
        errors += [f"{cid} couple report: {x}" for x in validate_bundle(cr)]
        errors += [f"{cid} pedigree: {x}" for x in validate_pedigree(build_pedigree(couple), couple)]
        counts["pedigrees"] += 1
        fam = build_family(couple)
        family_packets = list(fam.relatives)
        if fam.HasField("proband"):
            family_packets.insert(0, fam.proband)
        for rel in family_packets:
            errors += [f"{cid} family: {x}" for x in validate_phenopacket(rel)]
        counts["families"] += 1
    counts["errors"] = len(errors)
    return {"counts": counts, "errors": errors}


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python -m fhirgen.validate <cohort.json> [more.json ...]")
        return 2
    total = 0
    for path in argv:
        with open(path, encoding="utf-8") as fh:
            out = validate_cohort(json.load(fh))
        c = out["counts"]
        print(f"{path}: " + " ".join(f"{k}={v}" for k, v in c.items()))
        for e in out["errors"][:50]:
            print(f"  ERROR {e}")
        total += c["errors"]
    print("RESULT: " + ("PASS (0 errors)" if total == 0 else f"FAIL ({total} errors)")
          + " - R4B models + ref-walker + structure checks (HL7 validator CLI: see fhirgen.hl7_summary)")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
