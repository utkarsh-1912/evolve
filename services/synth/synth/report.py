"""Calibration report for a generated cohort (R-DATA-1 / R-DATA-3).

Descriptive statistics of the SAMPLED data only (counts, proportions, Wilson 95% CIs).
"Concordant" here means: both partners carry a P/LP call in the same gene (the cohort-level
incompatibility rate used for calibration against the source's 4.8%-13.1% band, §2.4).
No risk output is computed here (P-02).
"""
from __future__ import annotations

import math

from .cohort import load_panel, sampled_genes

Z95 = 1.959963984540054
BAND = (0.048, 0.131)  # source §2.4 spectrum (570 genes); reference only, not a target (DECISIONS #10)


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def _plp_genes(partner: dict) -> set[int]:
    return {c["hgnc_id"] for c in partner["calls"] if c["classification"] in ("P", "LP")}


def _is_synthetic(call: dict) -> bool:
    """Non-founder alleles carry a c.SYN id, or are HBA2 synthetic deletions (no founders listed)."""
    return (call["hgvs_c"] or "").startswith("c.SYN") or call["gene"] == "HBA2"


def build_report(doc: dict) -> dict:
    genes = sampled_genes(load_panel())
    couples = doc["couples"]
    partners = [p for c in couples for p in c["partners"]]
    n_ind = len(partners)
    carrier_rows = []
    for g in genes:
        k = sum(1 for p in partners if g["hgnc_id"] in _plp_genes(p))
        lo, hi = wilson(k, n_ind)
        carrier_rows.append({
            "gene": g["symbol"], "hgnc_id": g["hgnc_id"], "target": g["carrier_freq"],
            "carriers": k, "individuals": n_ind, "realized": round(k / n_ind, 4) if n_ind else None,
            "ci95": [round(lo, 4), round(hi, 4)], "target_in_ci95": lo <= g["carrier_freq"] <= hi,
        })
    by_rel: dict[str, list[int]] = {}
    conc_total = 0
    calls = flags_g = flags_c = 0
    syn_calls = syn_g = syn_c = 0
    for c in couples:
        a, b = c["partners"]
        conc = bool(_plp_genes(a) & _plp_genes(b))
        conc_total += conc
        row = by_rel.setdefault(c["relationship"]["type"], [0, 0])
        row[0] += 1
        row[1] += conc
        for p in c["partners"]:
            for call in p["calls"]:
                if call["classification"] in ("P", "LP"):
                    calls += 1
                    flags_g += call["absent_gnomad"]
                    flags_c += call["absent_clinvar"]
                    if _is_synthetic(call):
                        syn_calls += 1
                        syn_g += call["absent_gnomad"]
                        syn_c += call["absent_clinvar"]
    n_c = len(couples)
    lo, hi = wilson(conc_total, n_c)
    rate = conc_total / n_c if n_c else 0.0
    return {
        "synthetic": True,
        "seed": doc["seed"],
        "couples": n_c,
        "carrier_rates": carrier_rows,
        "concordance": {
            "concordant_couples": conc_total, "rate": round(rate, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "note": "8-gene floor; reported, not targeted (DECISIONS #10)",
            "reference_band_570_genes": list(BAND),
        },
        "by_relationship": {
            k: {"couples": v[0], "share": round(v[0] / n_c, 4), "concordant": v[1],
                "concordance_rate": round(v[1] / v[0], 4) if v[0] else None}
            for k, v in sorted(by_rel.items())
        },
        "novelty_gap": {
            "plp_calls": calls,
            "absent_gnomad": flags_g, "absent_gnomad_rate": round(flags_g / calls, 4) if calls else None,
            "absent_gnomad_target": 0.52,
            "absent_clinvar": flags_c, "absent_clinvar_rate": round(flags_c / calls, 4) if calls else None,
            "absent_clinvar_target": 0.30,
            "note": "founder variants never flagged (DECISIONS #12); targets apply to synthetic variants",
            "synthetic_calls": syn_calls,
            "synthetic_absent_gnomad_rate": round(syn_g / syn_calls, 4) if syn_calls else None,
            "synthetic_absent_clinvar_rate": round(syn_c / syn_calls, 4) if syn_calls else None,
        },
    }


def format_report(rep: dict) -> str:
    lines = [f"SYNTHETIC cohort report  seed={rep['seed']}  couples={rep['couples']}",
             f"{'gene':<9}{'target':>8}{'realized':>10}  95% CI            in CI"]
    for r in rep["carrier_rates"]:
        lines.append(f"{r['gene']:<9}{r['target']:>8.3f}{r['realized']:>10.4f}  "
                     f"[{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}]  {r['target_in_ci95']}")
    c = rep["concordance"]
    lines.append(f"concordant couples: {c['concordant_couples']}/{rep['couples']} = {c['rate']:.4f} "
                 f"(95% CI {c['ci95'][0]:.4f}-{c['ci95'][1]:.4f}); {c['note']}")
    for k, v in rep["by_relationship"].items():
        lines.append(f"  {k:<22} n={v['couples']:<5} share={v['share']:.3f} concordant={v['concordant']} "
                     f"rate={v['concordance_rate']}")
    ng = rep["novelty_gap"]
    lines.append(f"novelty gap: absent_gnomad {ng['absent_gnomad_rate']}, "
                 f"absent_clinvar {ng['absent_clinvar_rate']} over {ng['plp_calls']} P/LP calls (founders never flagged); "
                 f"synthetic-only: gnomad {ng['synthetic_absent_gnomad_rate']} (target 0.52), "
                 f"clinvar {ng['synthetic_absent_clinvar_rate']} (target 0.30) over {ng['synthetic_calls']}")
    return "\n".join(lines)
