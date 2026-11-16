"""Couple assessment: one locked RiskOutput per relevant gene (R-RISK-1/2/3, docs/07, TASK-P1-RE).

Input: one couple object per contracts/cohort.schema.json. Output: list of locked RiskOutput dicts
(contracts/risk_output.schema.json v1.1.0), sorted by hgnc_id, deterministic.

Per-gene rules. escalate=true only for CounselorCopilot triggers (DECISIONS #11, #18, #19):
  scenario             when                                         status / number / escalate / audience
  concordant_positive  both partners: exactly one het P/LP call     ok, 1/4, true (trigger a), couple
                       ... gene not in panel                        needs_counselor(not_in_panel), true,
                                                                    counselor_only
  discordant           one partner P/LP, other no call in gene      ok via q, d (negative partner's assay stage),
                                                                    R from paths; escalate iff R>0 or complex
                                                                    locus (trigger b); carrier_partner_only
                       ... q null / d null / gene not in panel      needs_counselor(missing_carrier_freq |
                                                                    missing_detection_rate | not_in_panel), no
                                                                    number, escalate iff R>0 or complex locus
                       ... d == 1 (a zero reads as "no risk", P-04) needs_counselor(perfect_detection), true
  atypical_genotype    hom P/LP, >=2 P/LP in one gene for one       needs_counselor(atypical_genotype), true,
                       partner, or any VUS in a gene with P/LP      counselor_only
  shared_vus_roh       no P/LP; both partners have a VUS in the     needs_counselor(shared_vus_roh), true
                       gene and at least one is in ROH >10 Mb       (trigger c, P-05), counselor_only
F from wright() is always attached with fusage "genome_wide_context_only" (P-03).

PRIVACY (P-06): only concordant_positive genes (the APSI intersection) are audience "couple". A discordant
record is for the carrier partner only (carrier_role). Anything ambiguous is counselor_only (fail closed).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

from .core import Path, concordant_positive, discordant, lock, wright
from .panel import Panel, load_panel

PLP = ("P", "LP")


@dataclass(frozen=True)
class GeneScenario:
    """Pure set logic (no probabilities): which scenario applies to a gene and who carries it."""
    hgnc_id: int
    gene: str
    scenario: str                    # concordant_positive | discordant | atypical_genotype | shared_vus_roh
    carrier_roles: tuple[str, ...]   # roles ("A"/"B") with a P/LP call in this gene
    negative_role: Optional[str]     # discordant only: the screen-negative partner
    in_panel: bool                   # False -> no q/d available


def _partners(couple: dict) -> dict[str, dict]:
    ps = couple.get("partners")
    if not isinstance(ps, list) or len(ps) != 2:
        raise ValueError("couple must have exactly two partners")
    by_role = {p.get("role"): p for p in ps}
    if set(by_role) != {"A", "B"}:
        raise ValueError("partners must have roles A and B")
    return by_role


def _paths(couple: dict) -> list[Path]:
    rel = couple.get("relationship")
    if not isinstance(rel, dict) or not isinstance(rel.get("paths"), list):
        raise ValueError("couple.relationship.paths is required")
    out = []
    for p in rel["paths"]:
        if not isinstance(p, (list, tuple)) or len(p) != 3:
            raise ValueError("each Wright path must be [n1, n2, ancestor_F]")
        n1, n2, fa = p
        if isinstance(n1, bool) or isinstance(n2, bool) or not isinstance(n1, int) or not isinstance(n2, int):
            raise ValueError("Wright path lengths must be integers")
        if not isinstance(fa, str):
            raise ValueError("ancestor_F must be a string fraction, e.g. '0' or '1/16'")
        out.append(Path(n1, n2, Fraction(fa)))
    return out


def gene_scenarios(couple: dict, panel: Optional[Panel] = None) -> list[GeneScenario]:
    """Classify each relevant gene. Set logic only; sorted by hgnc_id. Also usable for routing (P-06)."""
    panel = panel or load_panel()
    parts = _partners(couple)
    calls: dict[str, dict[int, list[dict]]] = {"A": {}, "B": {}}
    symbols: dict[int, str] = {}
    for role, p in parts.items():
        for c in p.get("calls") or []:
            calls[role].setdefault(c["hgnc_id"], []).append(c)
            symbols.setdefault(c["hgnc_id"], c["gene"])

    out: list[GeneScenario] = []
    for hid in sorted(set(calls["A"]) | set(calls["B"])):
        info = panel.gene(hid)
        symbol = info.symbol if info is not None else symbols[hid]
        in_panel = info is not None
        plp = {r: [c for c in calls[r].get(hid, []) if c["classification"] in PLP] for r in ("A", "B")}
        vus = {r: [c for c in calls[r].get(hid, []) if c["classification"] == "VUS"] for r in ("A", "B")}
        carriers = tuple(r for r in ("A", "B") if plp[r])
        if carriers:
            atypical = (
                any(len(plp[r]) > 1 or any(c["zygosity"] == "hom" for c in plp[r]) for r in carriers)
                or bool(vus["A"] or vus["B"])
            )
            neg = None if len(carriers) == 2 else ("B" if carriers == ("A",) else "A")
            if atypical:
                scenario = "atypical_genotype"
            elif neg is None:
                scenario = "concordant_positive"
            else:
                scenario = "discordant"
            out.append(GeneScenario(hid, symbol, scenario, carriers, neg, in_panel))
        elif vus["A"] and vus["B"] and any(c["in_roh_gt_10mb"] for c in vus["A"] + vus["B"]):
            out.append(GeneScenario(hid, symbol, "shared_vus_roh", (), None, in_panel))
    return out


def _needs_counselor(scenario: str) -> dict:
    return {"scenario": scenario, "status": "needs_counselor", "offspring_risk": None}


def assess_couple(couple: dict, panel: Optional[Panel] = None) -> list[dict]:
    """Return one locked RiskOutput per relevant gene (see module docstring). Deterministic, no I/O beyond
    the cached panel contract. Raises ValueError on malformed input (caller must fail closed)."""
    panel = panel or load_panel()
    f, r = wright(_paths(couple))
    parts = _partners(couple)
    results: list[dict] = []
    for gs in gene_scenarios(couple, panel):
        kw = {"gene": gs.gene, "hgnc_id": gs.hgnc_id, "f": f}
        if gs.scenario in ("atypical_genotype", "shared_vus_roh"):
            results.append(lock(_needs_counselor(gs.scenario), escalate=True, audience="counselor_only",
                                reason=gs.scenario, **kw))
            continue
        if gs.scenario == "concordant_positive":
            if gs.in_panel:
                results.append(lock(concordant_positive(), escalate=True, audience="couple", **kw))
            else:
                results.append(lock(_needs_counselor(gs.scenario), escalate=True, audience="counselor_only",
                                    reason="not_in_panel", **kw))
            continue
        # discordant: private to the carrier partner (P-06)
        kw.update(audience="carrier_partner_only", carrier_role=gs.carrier_roles[0])
        info = panel.gene(gs.hgnc_id)
        elevated = r > 0 or (info is not None and info.complex_locus)  # trigger (b), DECISIONS #19
        q = panel.carrier_freq(gs.hgnc_id)
        stage = (parts[gs.negative_role].get("assays") or {}).get(str(gs.hgnc_id))
        d = panel.detection_rate(gs.hgnc_id, stage)
        if info is None or q is None or d is None:
            reason = "not_in_panel" if info is None else ("missing_carrier_freq" if q is None
                                                          else "missing_detection_rate")
            results.append(lock(_needs_counselor("discordant"), escalate=elevated, reason=reason, **kw))
            continue
        if d == 1:  # a zero would read as "no risk" (P-04); DECISIONS #18
            results.append(lock(_needs_counselor("discordant"), escalate=True, reason="perfect_detection", **kw))
            continue
        res = discordant(q, d, r)
        ref = discordant(q, d, 0)
        results.append(lock(res, reference_unrelated=ref, escalate=elevated, **kw))
    return results
