"""Five canonical vignettes V1-V5 as cohort documents (R-DATA-2; source §2.4).

SYNTHETIC DATA ONLY. Expected numbers are COPIED from docs/07-RISK-MATH-SPEC.md §3 /
tests/golden/risk_vectors.json (which reproduce source §2.4). Nothing is computed here (P-02).
The `expected` block is free-form (cohort.schema.json allows any object):
  - couple_escalation: the system action the source §2.4 requires for the couple
    (CounselorCopilot trigger), which may be realised outside RiskOutput.escalate.
  - genes[]: per-gene expectation for risk_engine.assess_couple outputs.
"""
from __future__ import annotations

from .cohort import CONTRACT_VERSION, load_panel, sampled_genes

VIGNETTE_SEED = 0  # hand-authored fixtures; no sampling involved

_PATHS = {
    "unrelated": [],
    "first_cousins": [[2, 2, "0"], [2, 2, "0"]],
    "double_first_cousins": [[2, 2, "0"], [2, 2, "0"], [2, 2, "0"], [2, 2, "0"]],
}

HBB, CYP21A2, SMN1, MEFV, GJB2, ABCA4, DONSON = 4827, 2600, 11117, 6998, 4284, 34, 2993


def _call(hgnc_id, gene, hgvs_c, hgvs_p, cls="P", vt="snv", gnomad=False, clinvar=False, roh=False):
    return {"hgnc_id": hgnc_id, "gene": gene, "hgvs_c": hgvs_c, "hgvs_p": hgvs_p, "refseq": None,
            "zygosity": "het", "classification": cls, "variant_type": vt,
            "absent_gnomad": gnomad, "absent_clinvar": clinvar, "in_roh_gt_10mb": roh}


def _partner(vid, role, sex, age, bmi, calls, extra_assays=(), stage=None):
    panel_ids = [g["hgnc_id"] for g in sampled_genes(load_panel())]
    ids = panel_ids + [h for h in extra_assays if h not in panel_ids]
    assays = {str(h): "initial" for h in ids}
    for h, s in (stage or {}).items():
        assays[str(h)] = s
    return {"partner_id": f"{vid}{role}", "role": role, "sex": sex, "age": age, "bmi": bmi,
            "calls": calls, "assays": assays}


def _doc(couple):
    return {"contract_version": CONTRACT_VERSION, "seed": VIGNETTE_SEED, "synthetic": True, "couples": [couple]}


def _v1():
    hbb = lambda: _call(HBB, "HBB", "c.92+5G>C", None)  # noqa: E731  ClinVar Pathogenic per §2.4 -> absent_clinvar False
    return _doc({
        "couple_id": "V1",
        "relationship": {"type": "first_cousins", "paths": _PATHS["first_cousins"]},
        "partners": [_partner("V1", "A", "female", 24, 23.4, [hbb()]),
                     _partner("V1", "B", "male", 27, 26.1, [hbb()])],
        "expected": {
            "source": "architecture-source §2.4 Vignette 1; docs/07 §3 (V1 HBB concordant)",
            "relationship": {"F": "1/16", "R": "1/8"},
            "apsi": {"status": "incompatible", "intersection_hgnc_ids": [HBB]},
            "couple_escalation": True,
            "genes": [{"gene": "HBB", "hgnc_id": HBB, "scenario": "concordant_positive", "status": "ok",
                       "offspring_risk": "1/4", "offspring_one_in": 4.0, "escalate": True, "audience": "couple"}],
            "required_actions": ["mutual consent disclosure via APSI", "escalate to genetic counselor",
                                 "non-directive options", "certificate issued regardless of result (P-14)"],
        },
    })


def _v2():
    return _doc({
        "couple_id": "V2",
        "relationship": {"type": "unrelated", "paths": _PATHS["unrelated"]},
        "partners": [_partner("V2", "A", "female", 29, 24.8, [_call(CYP21A2, "CYP21A2", "c.955C>T", "p.(Gln319Ter)")]),
                     _partner("V2", "B", "male", 31, 27.9, [])],
        "expected": {
            "source": "architecture-source §2.4 Vignette 2; docs/07 §3; tests/golden/risk_vectors.json V2-*",
            "relationship": {"F": "0", "R": "0"},
            "apsi": {"status": "compatible", "intersection_hgnc_ids": []},
            "couple_escalation": True,
            "genes": [{"gene": "CYP21A2", "hgnc_id": CYP21A2, "scenario": "discordant", "status": "ok",
                       "screen_negative_partner": "B", "assay_stage_b": "initial", "q": "0.106", "d": "0.92",
                       "prior": 0.106, "posterior": 0.0094, "posterior_one_in": 106.4,
                       "offspring_one_in": 425.7, "offspring_one_in_display": "426",
                       "confirmatory_task_required": True, "escalate": True,
                       "audience": "carrier_partner_only",
                       "visible_to": "A only (not in APSI intersection, P-06)",
                       "reference_if_confirmatory": {"d": "0.99", "posterior": 0.00118, "posterior_one_in": 844.4,
                                                     "offspring_one_in": 3377.6}}],
            "required_actions": ["flag CYP21A2 technical complexity",
                                 "FHIR Task for confirmatory testing of B before any reassurance (P-04)"],
        },
    })


def _v3():
    smn1 = _call(SMN1, "SMN1", None, None, vt="cnv_deletion")
    return _doc({
        "couple_id": "V3",
        "relationship": {"type": "first_cousins", "paths": _PATHS["first_cousins"]},
        "partners": [_partner("V3", "A", "female", 26, 22.1, [smn1]),
                     _partner("V3", "B", "male", 30, 28.5, [])],
        "expected": {
            "source": "architecture-source §2.4 Vignette 3; docs/07 §3; tests/golden/risk_vectors.json V3-*",
            "relationship": {"F": "1/16", "R": "1/8"},
            "apsi": {"status": "compatible", "intersection_hgnc_ids": []},
            "couple_escalation": True,
            "genes": [{"gene": "SMN1", "hgnc_id": SMN1, "scenario": "discordant", "status": "ok",
                       "screen_negative_partner": "B", "assay_stage_b": "initial", "q": "0.013", "d": "0.92",
                       "R": "1/8", "prior": 0.13637, "posterior": 0.01248, "posterior_one_in": 80.2,
                       "offspring_one_in": 320.6, "offspring_one_in_display": "321",
                       "reference_unrelated_offspring_one_in": 3800.2, "escalate": True,
                       "confirmatory_task_required": True, "audience": "carrier_partner_only",
                       "visible_to": "A only (not in APSI intersection, P-06)"}],
            "required_actions": ["prevent false-negative clearance", "explain residual risk",
                                 "specialist genetic counseling + extended family phasing"],
        },
    })


def _v4():
    return _doc({
        "couple_id": "V4",
        "relationship": {"type": "unrelated", "paths": _PATHS["unrelated"]},
        "partners": [
            _partner("V4", "A", "female", 25, 21.7,
                     [_call(MEFV, "MEFV", None, "p.(Ala744Ser)"),
                      _call(GJB2, "GJB2", f"c.SYN{GJB2}0A>G", None)],
                     extra_assays=[GJB2]),
            _partner("V4", "B", "male", 28, 25.3,
                     [_call(ABCA4, "ABCA4", "c.5882G>A", "p.(Gly1961Glu)")],
                     extra_assays=[GJB2]),
        ],
        "expected": {
            "source": "architecture-source §2.4 Vignette 4 (privacy test)",
            "relationship": {"F": "0", "R": "0"},
            "apsi": {"status": "compatible", "label": "Compatible / No Shared Recessive Risk",
                     "intersection_hgnc_ids": []},
            "couple_escalation": False,
            "genes": [
                {"gene": "MEFV", "hgnc_id": MEFV, "scenario": "discordant", "status": "needs_counselor",
                 "escalate": False, "audience": "carrier_partner_only", "reason": "missing_detection_rate",
                 "visible_to": "A only"},
                {"gene": "GJB2", "hgnc_id": GJB2, "scenario": "discordant", "status": "needs_counselor",
                 "escalate": False, "audience": "carrier_partner_only", "reason": "missing_carrier_freq",
                 "visible_to": "A only"},
                {"gene": "ABCA4", "hgnc_id": ABCA4, "scenario": "discordant", "status": "needs_counselor",
                 "escalate": False, "audience": "carrier_partner_only", "reason": "missing_detection_rate",
                 "visible_to": "B only"},
            ],
            "privacy": {"never_shown_to_B": ["MEFV", "GJB2"], "never_shown_to_A": ["ABCA4"]},
            "notes": "Source gives no number for V4 (residual risk 'low', driven by q on opposing genes). "
                     "Per-gene needs_counselor (missing q/d) is NON-escalating: unrelated couple, no complex locus "
                     "(DECISIONS #11, #19; handoffs/ANSWER-DS-1-2.md DS-1.4).",
        },
    })


def _v5():
    vus = lambda: _call(DONSON, "DONSON", f"c.SYN{DONSON}9C>T", None, cls="VUS",  # noqa: E731
                        gnomad=True, clinvar=True, roh=True)
    return _doc({
        "couple_id": "V5",
        "relationship": {"type": "double_first_cousins", "paths": _PATHS["double_first_cousins"]},
        "partners": [_partner("V5", "A", "female", 27, 24.0, [vus()]),
                     _partner("V5", "B", "male", 32, 29.2, [vus()])],
        "family_history": [{
            "relative": "infant relative (pedigree position not stated in source §2.4)",
            "finding": "Unexplained neonatal or infant death (HPO code TODO(verify))",
            "hpo": "HP:0001522",
        }],
        "expected": {
            "source": "architecture-source §2.4 Vignette 5",
            "relationship": {"F": "1/8", "R": "1/4"},
            "p_lp_screen": "negative",
            "couple_escalation": True,
            "suppress_automated_clearance": True,
            "genes": [{"gene": "DONSON", "hgnc_id": DONSON, "scenario": "shared_vus_roh", "status": "needs_counselor",
                       "escalate": True, "audience": "counselor_only", "reason": "shared_vus_roh"}],
            "red_flags": ["unexplained infant death", "double first cousins", "shared ROH variant"],
            "notes": "Scenario shared_vus_roh per risk_output v1.1.0 (DECISIONS #13, #17); counselor_only per #20 "
                     "(P-05, trigger c). HPO HP:0001522 (Death in infancy) TODO(verify).",
        },
    })


def build_vignettes() -> dict[str, dict]:
    return {"V1": _v1(), "V2": _v2(), "V3": _v3(), "V4": _v4(), "V5": _v5()}
