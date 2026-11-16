"""Seeded synthetic couple-cohort generator (R-DATA-1, R-DATA-3).

SYNTHETIC DATA ONLY (P-11). Every identifier is obviously fake (SYN-...).
This module SAMPLES genotypes from published carrier frequencies; it never computes a
risk output (P-02). All couple-level risk numbers come from services/risk_engine.

Model (documented in services/synth/README.md):
* Per partner, per gene with non-null carrier_freq: Bernoulli(carrier_freq) -> het P/LP call.
* Related couples (IBD): with probability R (coefficient of relationship for the
  relationship type) partner B's carrier state at a locus is copied identical-by-descent
  from partner A (same allele, same call); otherwise it is an independent population draw.
  This keeps each partner's marginal carrier rate equal to carrier_freq while making
  consanguineous couples concordant more often.
* Allele choice for a carrier: founder variant weighted by its allele frequency (af)
  relative to the gene's allele frequency (carrier_freq/2); the remainder goes to founder
  variants with af=null if any, otherwise to clearly synthetic ids ("c.SYN<n>A>G").
* Novelty-gap flags (R-DATA-3): documented founder variants are never novel
  (absent_gnomad=absent_clinvar=False; DECISIONS #12). Synthetic non-founder calls get
  independent Bernoulli flags, absent_gnomad 0.52, absent_clinvar 0.30 (source §2.1).
  Overall realized rates are reported, not forced. IBD-copied calls copy A's flags.
"""
from __future__ import annotations

import json
import pathlib
import random
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[3]
PANEL_PATH = ROOT / "contracts" / "gene_panel.json"
CONTRACT_VERSION = "1.0.0"

# Relationship mix (docs/DECISIONS.md #10, handoffs/ANSWER-DS-1-2.md DS-2): source-realistic.
# Source §2.3: consanguineous unions (second cousins or closer) are 20-50% of marriages,
# first cousins ~1/3. 50% consanguineous = top of that range. With only the 8
# frequency-bearing genes, couple concordance is ~4-5% and is REPORTED as the 8-gene floor;
# the 4.8-13.1% band (§2.4) covers the 570-gene panel and is not targeted here.
RELATIONSHIP_MIX = [
    ("unrelated", Fraction(50, 100)),
    ("first_cousins", Fraction(33, 100)),
    ("double_first_cousins", Fraction(7, 100)),
    ("second_cousins", Fraction(10, 100)),
]

# Wright path lists [n1, n2, ancestor_F] (shape of risk_engine.Path; non-inbred ancestors).
PATHS = {
    "unrelated": [],
    "first_cousins": [[2, 2, "0"], [2, 2, "0"]],
    "double_first_cousins": [[2, 2, "0"], [2, 2, "0"], [2, 2, "0"], [2, 2, "0"]],
    "second_cousins": [[3, 3, "0"], [3, 3, "0"]],
}

# Coefficient of relationship used ONLY as the IBD sampling probability (genotype
# simulation, not a risk output). Standard values; first/double-first match
# tests/golden/risk_vectors.json "wright" entries; second cousins = 1/32.
IBD_R = {
    "unrelated": Fraction(0),
    "first_cousins": Fraction(1, 8),
    "double_first_cousins": Fraction(1, 4),
    "second_cousins": Fraction(1, 32),
}

ABSENT_GNOMAD_P = 0.52  # source §2.1 / charter R-DATA-3
ABSENT_CLINVAR_P = 0.30
SYNTHETIC_LP_SHARE = 0.20  # TODO(verify): share of synthetic (non-founder) calls labelled LP vs P; not in source
CONFIRMATORY_SHARE = 0.30  # task card item 3
N_SYNTHETIC_ALLELES = 3  # synthetic allele pool size per gene
AGE_RANGE = (18, 45)
BMI_RANGE = (19.0, 40.0)


def load_panel() -> dict:
    return json.loads(PANEL_PATH.read_text(encoding="utf-8"))


def sampled_genes(panel: dict) -> list[dict]:
    """Genes eligible for random sampling: non-null carrier_freq (gene_panel.rules)."""
    return [g for g in panel["genes"] if g.get("carrier_freq") is not None]


def _allele_options(gene: dict) -> list[tuple[dict, float]]:
    """(allele, weight) list for one gene. Weights are founder af / (carrier_freq/2)."""
    gene_af = gene["carrier_freq"] / 2.0  # approx. allele freq from carrier freq (HWE, rare-allele)
    founders = gene.get("founder_variants", [])
    known = [f for f in founders if f.get("af") is not None]
    unknown = [f for f in founders if f.get("af") is None]
    opts: list[tuple[dict, float]] = []
    used = 0.0
    for f in known:
        w = min(f["af"] / gene_af, 1.0 - used)
        opts.append((_founder_allele(f), w))
        used += w
    rest = max(0.0, 1.0 - used)
    if rest > 0:
        if unknown:
            for f in unknown:
                opts.append((_founder_allele(f), rest / len(unknown)))
        else:
            vt = "cnv_deletion" if gene["symbol"] == "HBA2" else "snv"  # HBA2: CNV/deletion calling (source §2.1)
            for k in range(N_SYNTHETIC_ALLELES):
                opts.append((_synthetic_allele(gene, k, vt), rest / N_SYNTHETIC_ALLELES))
    return opts


def _founder_allele(f: dict) -> dict:
    return {"hgvs_c": f.get("hgvs_c"), "hgvs_p": f.get("hgvs_p"), "variant_type": f["variant_type"],
            "classification": "P", "founder": True}


def _synthetic_allele(gene: dict, k: int, variant_type: str) -> dict:
    hgvs_c = None if variant_type == "cnv_deletion" else f"c.SYN{gene['hgnc_id']}{k}A>G"
    return {"hgvs_c": hgvs_c, "hgvs_p": None, "variant_type": variant_type,
            "classification": None, "founder": False, "syn_index": k}


def _make_call(rng: random.Random, gene: dict, allele: dict) -> dict:
    cls = allele["classification"] or ("LP" if rng.random() < SYNTHETIC_LP_SHARE else "P")
    return {
        "hgnc_id": gene["hgnc_id"],
        "gene": gene["symbol"],
        "hgvs_c": allele["hgvs_c"],
        "hgvs_p": allele["hgvs_p"],
        "refseq": None,  # transcript not stated in source; fhir-interop uses placeholders
        "zygosity": "het",
        "classification": cls,
        "variant_type": allele["variant_type"],
        "absent_gnomad": (not allele["founder"]) and rng.random() < ABSENT_GNOMAD_P,
        "absent_clinvar": (not allele["founder"]) and rng.random() < ABSENT_CLINVAR_P,
        "in_roh_gt_10mb": False,
    }


def _draw_allele(rng: random.Random, opts: list[tuple[dict, float]]) -> dict:
    return rng.choices([a for a, _ in opts], weights=[w for _, w in opts], k=1)[0]


def _relationship(rng: random.Random) -> str:
    x = rng.random()
    acc = 0.0
    for name, share in RELATIONSHIP_MIX:
        acc += float(share)
        if x < acc:
            return name
    return RELATIONSHIP_MIX[-1][0]


def _partner(idx: int, role: str, sex: str, rng: random.Random) -> dict:
    return {
        "partner_id": f"SYN-P{idx:04d}{role}",
        "role": role,
        "sex": sex,
        "age": rng.randint(*AGE_RANGE),
        "bmi": round(rng.uniform(*BMI_RANGE), 1),
        "calls": [],
        "assays": {},
    }


def generate_cohort(seed: int, n: int = 1000) -> dict:
    """Return a cohort document valid against contracts/cohort.schema.json. Deterministic in seed."""
    panel = load_panel()
    genes = sampled_genes(panel)
    options = {g["hgnc_id"]: _allele_options(g) for g in genes}
    rng = random.Random(seed)
    couples = []
    for i in range(1, n + 1):
        rel = _relationship(rng)
        sex_a = rng.choice(["female", "male"])
        sex_b = "male" if sex_a == "female" else "female"
        a = _partner(i, "A", sex_a, rng)
        b = _partner(i, "B", sex_b, rng)
        r_ibd = float(IBD_R[rel])
        for g in genes:
            hid = g["hgnc_id"]
            a["assays"][str(hid)] = "initial"
            b["assays"][str(hid)] = "initial"
            call_a = None
            if rng.random() < g["carrier_freq"]:
                call_a = _make_call(rng, g, _draw_allele(rng, options[hid]))
                a["calls"].append(call_a)
            if r_ibd > 0 and rng.random() < r_ibd:
                # IBD at this locus: B carries A's allele (or A's non-carrier allele).
                if call_a is not None:
                    b["calls"].append(dict(call_a))
            elif rng.random() < g["carrier_freq"]:
                b["calls"].append(_make_call(rng, g, _draw_allele(rng, options[hid])))
        # Assay stage: ~30% of CYP21A2-negative partners in discordant CYP21A2 couples get confirmatory.
        for g in genes:
            if not g.get("detection", {}).get("confirmatory"):
                continue
            hid = g["hgnc_id"]
            has_a = any(c["hgnc_id"] == hid for c in a["calls"])
            has_b = any(c["hgnc_id"] == hid for c in b["calls"])
            if has_a != has_b:
                neg = b if has_a else a
                if rng.random() < CONFIRMATORY_SHARE:
                    neg["assays"][str(hid)] = "confirmatory"
        couples.append({
            "couple_id": f"SYN-C{i:04d}",
            "relationship": {"type": rel, "paths": [list(p) for p in PATHS[rel]]},
            "partners": [a, b],
        })
    return {"contract_version": CONTRACT_VERSION, "seed": seed, "synthetic": True, "couples": couples}


def dumps(doc: dict) -> str:
    """Canonical serialization: same document -> identical bytes."""
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
