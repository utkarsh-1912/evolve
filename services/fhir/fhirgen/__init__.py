"""fhirgen - FHIR R4 GenomicReport bundles, GA4GH Phenopacket v2 and Pedigree (R-FHIR-1).

Named `fhirgen` (not `fhir`) so it does not shadow the installed `fhir.resources` package.
Synthetic data only (P-11).
"""
from .bundle import build_couple_report, build_partner_bundle
from .phenopacket import build_family, build_pedigree, build_phenopacket, to_dict

__all__ = ["build_partner_bundle", "build_couple_report", "build_phenopacket", "build_pedigree",
           "build_family", "to_dict"]  # validators: import from fhirgen.validate
