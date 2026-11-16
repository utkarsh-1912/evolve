"""Profile URLs, code systems and codes used by fhirgen (R-FHIR-1; source §2.2, §3.1).

IG pin: HL7 FHIR Genomics Reporting IG `hl7.fhir.uv.genomics-reporting` 3.0.0 (STU3), FHIR R4
(models: fhir.resources.R4B). See services/fhir/ig-lock.json. Source §2.2 names "STU3 / v4.0.0-cibuild";
we pin the published STU3 release because a ci-build is not a stable target.

Nothing here has been checked against the IG package offline (the HL7 validator and IG packages are a
P4 stretch, DECISIONS #6). Every URL/code below is therefore TODO(verify) against the pinned package;
the ones we are least sure of are listed in UNVERIFIED with a reason. Change values only here.
"""
from __future__ import annotations

IG_PACKAGE = "hl7.fhir.uv.genomics-reporting"
IG_VERSION = "3.0.0"  # TODO(verify) pin decision recorded for orchestrator in DONE-P1-FH.md
IG_BASE = "http://hl7.org/fhir/uv/genomics-reporting"

# ---- Profiles (TODO(verify) against IG 3.0.0) ----
PROFILE_GENOMIC_REPORT = f"{IG_BASE}/StructureDefinition/genomic-report"  # checked in IG 3.0.0 package
PROFILE_VARIANT = f"{IG_BASE}/StructureDefinition/variant"
PROFILE_DIAGNOSTIC_IMPLICATION = f"{IG_BASE}/StructureDefinition/diagnostic-implication"
PROFILE_FOLLOWUP_TASK = f"{IG_BASE}/StructureDefinition/followup-recommendation"  # checked in IG 3.0.0
EXT_RECOMMENDED_ACTION = f"{IG_BASE}/StructureDefinition/recommended-action"

# ---- Code systems ----
LOINC = "http://loinc.org"
HGNC_SYSTEM = "http://www.genenames.org"  # IG 3.0.0 ValueSet hgnc-vs; value form "HGNC:<numeric id>"
HGVS_SYSTEM = "http://varnomen.hgvs.org"  # IG 3.0.0 ValueSet hgvs-vs (required binding)
REFSEQ_SYSTEM = "http://www.ncbi.nlm.nih.gov/refseq"
GENO_SYSTEM = "http://purl.obolibrary.org/obo/geno.owl"  # TODO(verify) exact system URI used by the IG
TBD_CODES = f"{IG_BASE}/CodeSystem/tbd-codes-cs"
V2_0074 = "http://terminology.hl7.org/CodeSystem/v2-0074"  # diagnostic service section
V2_0487 = "http://terminology.hl7.org/CodeSystem/v2-0487"  # specimen type
OBS_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"
ACT_REASON = "http://terminology.hl7.org/CodeSystem/v3-ActReason"
SYNTHETIC_LAB_NAME = "SYNTHETIC demo genomics laboratory (not a real organization)"
SYNTHETIC_ID_SYSTEM = "urn:synthetic:inherited-risk-demo:partner-id"

# Every resource is tagged as test data (P-11: synthetic only).
SYNTHETIC_TAG = {"system": ACT_REASON, "code": "HTEST", "display": "test health data"}

# ---- LOINC codes (TODO(verify) each against IG 3.0.0 bindings) ----
LOINC_GENETIC_REPORT = ("51969-4", "Genetic analysis report")
LOINC_VARIANT = ("69548-6", "Genetic variant assessment")
LOINC_GENE_STUDIED = ("48018-6", "Gene studied [ID]")
LOINC_GENOMIC_REF_SEQ = ("48013-7", "Genomic reference sequence [ID]")
LOINC_TRANSCRIPT_REF_SEQ = ("51958-7", "Transcript reference sequence [ID]")
LOINC_COORDINATE_SYSTEM = ("92822-6", "Genomic coordinate system [Type]")
LOINC_EXACT_START_END = ("81254-5", "Genomic allele start-end")
LOINC_REF_ALLELE = ("69547-8", "Genomic ref allele [ID]")
LOINC_ALT_ALLELE = ("69551-0", "Genomic alt allele [ID]")
LOINC_GENOMIC_HGVS = ("81290-9", "Genomic DNA change (gHGVS)")
LOINC_CODING_HGVS = ("48004-6", "DNA change (c.HGVS)")
LOINC_PROTEIN_HGVS = ("48005-3", "Amino acid change (pHGVS)")
LOINC_ALLELIC_STATE = ("53034-5", "Allelic state")
LOINC_DNA_CHANGE_TYPE = ("48019-4", "DNA change type")
LOINC_CLIN_SIG = ("53037-8", "Genetic variation clinical significance [Imp]")
LOINC_ASSOCIATED_PHENOTYPE = ("81259-4", "Associated phenotype")

VARIANT_PRESENT = ("LA9633-4", "Present")  # TODO(verify)
COORD_ONE_BASED = ("LA30102-0", "1-based character counting")  # LA30100-4 is 0-based interval (validator)

CLIN_SIG_ANSWERS = {  # TODO(verify) LOINC answer list LL4034-6
    "P": ("LA6668-3", "Pathogenic"),
    "LP": ("LA26332-9", "Likely pathogenic"),
    "VUS": ("LA26333-7", "Uncertain significance"),
}

# Allelic state (DECISIONS #15): GENO:0000135 heterozygous, GENO:0000136 homozygous,
# GENO:0000134 hemizygous. Source §2.2 maps hom to 0000134 - treated as a source erratum, TODO(verify).
# "hemi" is not in the cohort contract's zygosity enum (het/hom); supported for future X-linked use.
ALLELIC_STATE = {
    "het": ("GENO:0000135", "heterozygous"),
    "hom": ("GENO:0000136", "homozygous"),
    "hemi": ("GENO:0000134", "hemizygous"),
}
# LOINC LL381-5 answers, sent alongside GENO (extensible binding). TODO(verify) via validator display check.
ALLELIC_STATE_LOINC = {
    "het": ("LA6706-1", "Heterozygous"),
    "hom": ("LA6705-3", "Homozygous"),
    "hemi": ("LA6707-9", "Hemizygous"),
}
CONSENT_ID_SYSTEM = "urn:synthetic:inherited-risk-demo:consent-id"

# Sequence Ontology terms for DNA change type. TODO(verify) all three.
SO_SYSTEM = "http://www.sequenceontology.org"
DNA_CHANGE_TYPE = {
    "snv": ("SO:0001483", "SNV"),
    "indel": ("SO:1000032", "delins"),
    "cnv_deletion": ("SO:0001743", "copy_number_loss"),
}

# Specimen: source §3.1 says "blood or saliva"; contract does not say which -> blood placeholder.
SPECIMEN_TYPE = ("BLD", "Whole blood")

# Fixed synthetic timestamps so output is deterministic (placeholders, not real events).
SYNTHETIC_RECEIVED_TIME = "2026-01-05T08:00:00+04:00"
SYNTHETIC_ISSUED_TIME = "2026-01-12T10:00:00+04:00"

CARRIER_NOTE = "this patient is at least a carrier"  # source §2.2 verbatim
NOT_DIAGNOSIS_NOTE = "Carrier status is not a diagnosis. Decision support only - not medical advice."
SYNTHETIC_COORD_NOTE = (
    "SYNTHETIC demo record: genomic reference sequence, coordinates and any allele marked 'N' "
    "are placeholders, not real genomic data."
)

UNVERIFIED = {
    "IG_VERSION": "source names STU3 / v4.0.0-cibuild; 3.0.0 chosen, needs orchestrator confirmation",
    "GENO_SYSTEM": "system URI for GENO codes not confirmed offline",
    "ALLELIC_STATE": "GENO IDs per DECISIONS #15 (source erratum); confirm against GENO OWL",
    "CLIN_SIG_ANSWERS": "LOINC answer codes not confirmed offline",
    "DNA_CHANGE_TYPE": "SO term IDs not confirmed offline",
    "COUPLE_REPORT_PATTERN": "CodeX GenomeX prenatal carrier profile URLs not available offline; "
                             "couple report uses base genomics-report profile + Group subject",
    "REFSEQ_TRANSCRIPTS": "gene_panel refseq_transcript (MANE Select) used for founder c.HGVS; only ABCA4 "
                          "NM_000350.3 is source-cited (refseq_verified_from_source), all others TODO(verify) "
                          "(DECISIONS #39)",
    "DISEASE_CODES": "No Mondo IDs in contracts/gene_panel.json; phenopackets use local SYN: placeholder terms",
}
