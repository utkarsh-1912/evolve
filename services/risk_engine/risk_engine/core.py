from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Optional, Union

CONTRACT_VERSION = "1.1.0"
AUDIENCES = ("couple", "carrier_partner_only", "counselor_only")
REASONS = ("missing_carrier_freq", "missing_detection_rate", "shared_vus_roh", "atypical_genotype",
           "related_concordant_negative", "perfect_detection", "not_in_panel")
Num = Union[int, float, str, Fraction]


def _fr(x: Num) -> Fraction:
    """Exact conversion; floats go through str() so 0.106 means 106/1000."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, float):
        return Fraction(str(x))
    return Fraction(x)


def _check_prob(name: str, x: Fraction) -> None:
    if not (0 <= x <= 1):
        raise ValueError(f"{name} must be in [0,1], got {x}")


@dataclass(frozen=True)
class Path:
    """One path between partners through a common ancestor.

    n1/n2 = meioses from each partner up to the ancestor; ancestor_f = inbreeding of ancestor.
    """
    n1: int
    n2: int
    ancestor_f: Num = 0


def wright(paths: Iterable[Path]) -> tuple[Fraction, Fraction]:
    """Return (F, R). kinship phi = sum (1/2)^(n1+n2+1) * (1+F_A); F = phi; R = 2*phi."""
    phi = Fraction(0)
    for p in paths:
        if p.n1 < 1 or p.n2 < 1:
            raise ValueError("path lengths must be >= 1")
        fa = _fr(p.ancestor_f)
        _check_prob("ancestor_f", fa)
        phi += Fraction(1, 2 ** (p.n1 + p.n2 + 1)) * (1 + fa)
    return phi, 2 * phi


def _posterior(prior: Fraction, d: Fraction) -> Fraction:
    miss = prior * (1 - d)
    return miss / (miss + (1 - prior))


def concordant_positive() -> dict:
    return {"scenario": "concordant_positive", "status": "ok", "offspring_risk": Fraction(1, 4)}


def discordant(q: Num, d: Num, r: Num = 0) -> dict:
    q, d, r = _fr(q), _fr(d), _fr(r)
    for n, v in (("q", q), ("d", d), ("R", r)):
        _check_prob(n, v)
    prior = r + (1 - r) * q
    post = _posterior(prior, d)
    return {
        "scenario": "discordant", "status": "ok", "q": q, "d": d, "R": r,
        "prior_carrier_b": prior, "posterior_carrier_b": post,
        "offspring_risk": post / 4,
    }


def concordant_negative(q: Num, d_a: Num, d_b: Optional[Num] = None, r: Num = 0) -> dict:
    """Both screen-negative. Related case is unspecified in the source -> needs_counselor, no number (P-20)."""
    q, r = _fr(q), _fr(r)
    d_a = _fr(d_a)
    d_b = d_a if d_b is None else _fr(d_b)
    if r != 0:
        return {"scenario": "concordant_negative", "status": "needs_counselor",
                "reason": "TODO(verify): related concordant-negative formula not in source",
                "reason_code": "related_concordant_negative", "offspring_risk": None}
    pa, pb = _posterior(q, d_a), _posterior(q, d_b)
    return {"scenario": "concordant_negative", "status": "ok", "posterior_carrier_a": pa,
            "posterior_carrier_b": pb, "offspring_risk": pa * pb / 4}


def _sig(x: Fraction, digits: int) -> str:
    """Round once to `digits` significant figures; Western digits, ',' thousands separator."""
    v = float(f"{float(x):.{digits}g}")
    return f"{v:,.10g}"


def _one_in_n(x: Fraction) -> Optional[str]:
    return None if x == 0 else _sig(1 / x, 3)  # "1 in N": 3 s.f. (docs/07 §4)


def _one_in(x: Fraction) -> Optional[str]:
    n = _one_in_n(x)
    return None if n is None else f"1 in {n}"


def _one_in_ar(x: Fraction) -> Optional[str]:
    n = _one_in_n(x)  # same rounded number as the EN sibling (DECISIONS #48)
    return None if n is None else f"1 من كل {n}"


def _times(x: Fraction) -> str:
    return f"about {_sig(x, 2)}x"  # 2 s.f. ("about 12x")


def _times_ar(x: Fraction) -> str:
    return f"حوالي {_sig(x, 2)} ضعفاً"


def lock(result: dict, *, gene: str, hgnc_id: int, f: Optional[Fraction] = None,
         reference_unrelated: Optional[dict] = None, escalate: Optional[bool] = None,
         audience: str = "counselor_only", carrier_role: Optional[str] = None,
         reason: Optional[str] = None) -> dict:
    """Freeze a result into the locked, hashable JSON that downstream text may quote (rule1). Contract v1.1.0.

    escalate: explicit CounselorCopilot trigger flag (source A7 (a)-(c), DECISIONS #11/#19). If omitted, a
      needs_counselor result defaults to True (fail-safe); an ok result carries no flag.
    audience: who may see the record (P-06); defaults to the most restrictive, counselor_only.
    reason: required iff status is needs_counselor (falls back to result["reason_code"]); must be null when ok.
    Relative risk (and its display) is null when R = 0 (DECISIONS #19).
    """
    if audience not in AUDIENCES:
        raise ValueError(f"unknown audience {audience!r}")
    if carrier_role not in ("A", "B", None):
        raise ValueError(f"unknown carrier_role {carrier_role!r}")
    if reason is None:
        reason = result.get("reason_code")
    if result["status"] == "ok":
        if reason is not None:
            raise ValueError("reason must be null when status is ok")
    elif reason not in REASONS:
        raise ValueError(f"needs_counselor requires a reason from {REASONS}, got {reason!r}")
    risk = result.get("offspring_risk")
    out = {
        "contract_version": CONTRACT_VERSION,
        "gene": gene,
        "hgnc_id": hgnc_id,
        "scenario": result["scenario"],
        "status": result["status"],
        "fusage": "genome_wide_context_only",
        "audience": audience,
        "carrier_role": carrier_role,
        "reason": reason,
        "F": None if f is None else float(f),
        "offspring_risk": None if risk is None else float(risk),
        "offspring_risk_one_in": None if risk is None else _one_in(risk),
        "offspring_risk_one_in_ar": None if risk is None else _one_in_ar(risk),
    }
    if "posterior_carrier_b" in result:
        out["prior_carrier_b"] = float(result["prior_carrier_b"]) if "prior_carrier_b" in result else None
        out["posterior_carrier_b"] = float(result["posterior_carrier_b"])
        out["posterior_carrier_b_one_in"] = _one_in(result["posterior_carrier_b"])
        out["posterior_carrier_b_one_in_ar"] = _one_in_ar(result["posterior_carrier_b"])
        out["detection_rate"] = float(result["d"]) if "d" in result else None
    if reference_unrelated and reference_unrelated.get("offspring_risk"):
        ref = reference_unrelated["offspring_risk"]
        related = result.get("R", 1) != 0  # R absent -> caller asserted a reference comparison
        rel = risk / ref if (risk is not None and related) else None
        out["relative_to_unrelated"] = None if rel is None else float(rel)
        out["relative_to_unrelated_display"] = None if rel is None else _times(rel)
        out["relative_to_unrelated_display_ar"] = None if rel is None else _times_ar(rel)
        out["reference_unrelated_one_in"] = _one_in(ref)
        out["reference_unrelated_one_in_ar"] = _one_in_ar(ref)
    if escalate is not None:
        out["escalate"] = bool(escalate)
    elif result["status"] == "needs_counselor":
        out["escalate"] = True  # fail-safe default when the caller states no trigger decision
    digest = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
    return {**out, "digest": digest}
