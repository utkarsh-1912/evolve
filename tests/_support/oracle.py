"""Independent math oracle (docs/07 Wright + Bayes, DECISIONS #11, #17-#20 routing) written from the spec with exact
Fractions. Lives under tests/ on purpose: probability arithmetic is banned in services/ outside risk_engine (P-02); the eval
harness imports it from here to verify, never to produce user-facing numbers. Uses only contracts, never risk_engine internals.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

import qa_support as qs

TOL = 1e-12
PLP = ("P", "LP")


def o_wright(paths) -> tuple[Fraction, Fraction]:
    phi = sum((Fraction(1, 2 ** (n1 + n2 + 1)) * (1 + Fraction(fa)) for n1, n2, fa in paths), Fraction(0))
    return phi, 2 * phi


def o_discordant(q: Fraction, d: Fraction, r: Fraction) -> dict:
    prior = r + (1 - r) * q
    miss = prior * (1 - d)
    post = miss / (miss + (1 - prior))
    return {"prior": prior, "post": post, "off": post / 4}


def o_sig(x: Fraction, sig: int) -> str:
    """Round an exact rational to `sig` significant figures (half-up), thousands separators, no trailing zeros."""
    with localcontext() as ctx:
        ctx.prec = 60
        dec = Decimal(x.numerator) / Decimal(x.denominator)
        q = dec.quantize(Decimal(1).scaleb(dec.adjusted() - sig + 1), rounding=ROUND_HALF_UP)
    if q == q.to_integral_value():
        return f"{int(q):,}"
    s = format(q.normalize(), "f")
    ip, fp = s.split(".")
    return f"{int(ip):,}.{fp}"


def o_one_in(x: Fraction | None) -> str | None:
    return None if x is None or x == 0 else f"1 in {o_sig(1 / x, 3)}"


def o_panel() -> dict:
    return {g["hgnc_id"]: g for g in qs.panel()["genes"]}


def oracle(couple: dict) -> dict[int, dict]:
    panel = o_panel()
    f, r = o_wright(couple["relationship"]["paths"])
    parts = {p["role"]: p for p in couple["partners"]}
    calls = {role: {} for role in "AB"}
    for role, p in parts.items():
        for c in p.get("calls") or []:
            calls[role].setdefault(c["hgnc_id"], []).append(c)
    out: dict[int, dict] = {}
    for hid in sorted(set(calls["A"]) | set(calls["B"])):
        g = panel.get(hid)
        plp = {x: [c for c in calls[x].get(hid, []) if c["classification"] in PLP] for x in "AB"}
        vus = {x: [c for c in calls[x].get(hid, []) if c["classification"] == "VUS"] for x in "AB"}
        carriers = [x for x in "AB" if plp[x]]
        base = {"F": f, "carrier_role": None, "offspring": None, "post": None, "prior": None, "d": None,
                "rel": None, "ref_off": None}
        if carriers:
            atypical = any(len(plp[x]) > 1 or any(c["zygosity"] == "hom" for c in plp[x]) for x in carriers) \
                or bool(vus["A"] or vus["B"])
            if atypical:  # DECISIONS #18
                out[hid] = {**base, "scenario": "atypical_genotype", "status": "needs_counselor",
                            "reason": "atypical_genotype", "audience": "counselor_only", "escalate": True}
            elif len(carriers) == 2:
                if g is None:
                    out[hid] = {**base, "scenario": "concordant_positive", "status": "needs_counselor",
                                "reason": "not_in_panel", "audience": "counselor_only", "escalate": True}
                else:
                    out[hid] = {**base, "scenario": "concordant_positive", "status": "ok", "reason": None,
                                "audience": "couple", "escalate": True, "offspring": Fraction(1, 4)}
            else:
                carrier = carriers[0]
                neg = "B" if carrier == "A" else "A"
                complex_locus = bool(g and g.get("complex_locus"))
                elevated = r > 0 or complex_locus  # trigger (b), DECISIONS #19
                rec = {**base, "scenario": "discordant", "audience": "carrier_partner_only", "carrier_role": carrier}
                q = None if g is None or g.get("carrier_freq") is None else Fraction(str(g["carrier_freq"]))
                stage = (parts[neg].get("assays") or {}).get(str(hid))
                dval = None if g is None or stage not in ("initial", "confirmatory") else (g.get("detection") or {}).get(stage)
                d = None if dval is None else Fraction(str(dval))
                if g is None or q is None or d is None:
                    reason = "not_in_panel" if g is None else ("missing_carrier_freq" if q is None else "missing_detection_rate")
                    out[hid] = {**rec, "status": "needs_counselor", "reason": reason, "escalate": elevated}
                elif d == 1:
                    out[hid] = {**rec, "status": "needs_counselor", "reason": "perfect_detection", "escalate": True}
                else:
                    res, ref = o_discordant(q, d, r), o_discordant(q, d, Fraction(0))
                    out[hid] = {**rec, "status": "ok", "reason": None, "escalate": elevated, "offspring": res["off"],
                                "post": res["post"], "prior": res["prior"], "d": d, "ref_off": ref["off"],
                                "rel": None if r == 0 else res["off"] / ref["off"]}
        elif vus["A"] and vus["B"] and any(c["in_roh_gt_10mb"] for c in vus["A"] + vus["B"]):
            out[hid] = {**base, "scenario": "shared_vus_roh", "status": "needs_counselor", "reason": "shared_vus_roh",
                        "audience": "counselor_only", "escalate": True}
    return out


def compare(couple: dict, engine: list[dict]) -> list[str]:
    exp = oracle(couple)
    got = {r["hgnc_id"]: r for r in engine}
    cid = couple["couple_id"]
    errs = []
    if set(exp) != set(got):
        return [f"{cid}: gene set oracle={sorted(exp)} engine={sorted(got)}"]

    def num(name, e, g):
        if e is None:
            if g is not None:
                errs.append(f"{cid}/{hid} {name}: oracle None, engine {g}")
        elif g is None or abs(float(e) - g) > TOL:
            errs.append(f"{cid}/{hid} {name}: oracle {float(e)!r}, engine {g!r}")

    for hid, e in exp.items():
        g = got[hid]
        for k_e, k_g in (("scenario", "scenario"), ("status", "status"), ("reason", "reason"), ("audience", "audience"),
                         ("carrier_role", "carrier_role")):
            if e[k_e] != g.get(k_g):
                errs.append(f"{cid}/{hid} {k_g}: oracle {e[k_e]!r}, engine {g.get(k_g)!r}")
        if g.get("escalate", False) != e["escalate"]:
            errs.append(f"{cid}/{hid} escalate: oracle {e['escalate']}, engine {g.get('escalate')}")
        num("F", e["F"], g.get("F"))
        num("offspring_risk", e["offspring"], g.get("offspring_risk"))
        num("posterior_carrier_b", e["post"], g.get("posterior_carrier_b"))
        num("prior_carrier_b", e["prior"], g.get("prior_carrier_b"))
        num("detection_rate", e["d"], g.get("detection_rate"))
        num("relative_to_unrelated", e["rel"], g.get("relative_to_unrelated"))
        for name, ev in (("offspring_risk_one_in", o_one_in(e["offspring"])),
                         ("posterior_carrier_b_one_in", o_one_in(e["post"])),
                         ("reference_unrelated_one_in", o_one_in(e["ref_off"]))):
            if g.get(name) != ev:
                errs.append(f"{cid}/{hid} {name}: oracle {ev!r}, engine {g.get(name)!r}")
        rel_disp = None if e["rel"] is None else f"about {o_sig(e['rel'], 2)}x"
        if g.get("relative_to_unrelated_display") != rel_disp:
            errs.append(f"{cid}/{hid} relative_to_unrelated_display: oracle {rel_disp!r}, engine {g.get('relative_to_unrelated_display')!r}")
        if e["status"] != "ok" and g.get("offspring_risk") is not None:
            errs.append(f"{cid}/{hid}: needs_counselor record carries a number (P-20)")
    return errs


