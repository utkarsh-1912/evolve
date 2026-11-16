"""Five charter dimensions from event logs (R-EVAL-1, docs/00-CHARTER.md success metrics, docs/04 §5).

Dimensions
  1 comprehension   share of personas answering all MMIC-style items correctly (target >= 0.85) and the
                    GCOS-24/GOS pre->post shift (target: paired sign-flip test p < 0.01)
  2 informed_choice share with SURE 4/4 after counseling (target >= 0.90) and coercion/directive flags (target 0)
  3 loop_velocity   share of incompatible couples booked within 48 h (target 1.0) and confirmatory tasks
                    completed (target >= 0.95)
  4 calibration     arithmetic mismatches in the cohort sweep (target 0) and FHIR/Phenopacket errors (target 0)
  5 privacy         unauthorized leaks under red-team (target 0) and interception share (target 1.0)

Every report is stamped SIMULATED. Dimensions 1-3 come from simulated personas and are not clinical findings.
This module counts events only; it never computes or alters any risk value (P-02).
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import datetime
from typing import Iterable, Optional

from .events import COMPREHENSION_ITEMS, GUARDRAIL_KEYS, GUARDRAIL_OUTCOMES
from .personas import stratum_key

SIMULATED_STAMP = {"simulated": True, "label": "SIMULATED",
                   "disclaimer": "Simulated users and synthetic data. Not a clinical finding."}

THRESHOLDS = {
    "comprehension_share": 0.85,
    "gcos_p_value_below": 0.01,
    "sure_full_share": 0.90,
    "coercion_flags_max": 0,
    "booked_within_48h_share": 1.0,
    "confirmatory_completed_share": 0.95,
    "arithmetic_mismatches_max": 0,
    "fhir_errors_max": 0,
    "leaks_max": 0,
    "interception_share": 1.0,
}
BOOKING_HOURS = 48


def wilson(k: int, n: int, z: float = 1.96) -> Optional[tuple[float, float]]:
    """Wilson score interval for k successes in n trials; None when n == 0."""
    if n <= 0:
        return None
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def share(k: int, n: int) -> dict:
    return {"k": k, "n": n, "value": (k / n) if n else None, "ci95": wilson(k, n)}


def paired_signflip_p(deltas: list[float], n_perm: int = 10000, seed: int = 0) -> Optional[float]:
    """Two-sided Monte-Carlo sign-flip test on paired differences (H0: symmetric around 0)."""
    if not deltas:
        return None
    rng = random.Random(seed)
    observed = abs(sum(deltas))
    hits = 0
    for _ in range(n_perm):
        s = sum(x if rng.random() < 0.5 else -x for x in deltas)
        if abs(s) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def _by_type(events: Iterable[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        out[e.get("type", "?")].append(e)
    return out


def _stratified(evts: list[dict], ok) -> dict:
    groups: dict[str, list[bool]] = defaultdict(list)
    for e in evts:
        groups[stratum_key(e.get("persona") or {})].append(bool(ok(e)))
    return {key: share(sum(v), len(v)) for key, v in sorted(groups.items())}


def comprehension(ev: dict[str, list[dict]]) -> dict:
    """First-attempt teach-back pass (backend verdict when present, else all items correct), by stratum, plus the
    final pass after one counselor re-explanation. GCOS-24/GOS is reported only if instrumented (no invented values)."""
    items = [e for e in ev.get("comprehension", []) if e.get("attempt", 1) == 1]
    final = {}
    for e in ev.get("comprehension", []):
        final[e.get("run_id", id(e))] = e
    ok = lambda e: bool(e["passed"]) if "passed" in e else all(bool((e.get("items") or {}).get(i)) for i in COMPREHENSION_ITEMS)  # noqa: E731
    overall = share(sum(ok(e) for e in items), len(items))
    after = list(final.values())
    per_item = {i: share(sum(bool((e.get("items") or {}).get(i)) for e in items), len(items)) for i in COMPREHENSION_ITEMS}
    gcos = ev.get("gcos", [])
    deltas = [float(e["post"]) - float(e["pre"]) for e in gcos]
    p_value = paired_signflip_p(deltas)
    share_ok = bool(items) and overall["value"] >= THRESHOLDS["comprehension_share"]
    if gcos:
        meets = share_ok and p_value is not None and p_value < THRESHOLDS["gcos_p_value_below"]
    else:
        meets = None if share_ok else False  # unknown: the GCOS half of the charter metric is not instrumented
    return {
        "first_attempt_pass": overall, "final_pass": share(sum(ok(e) for e in after), len(after)),
        "per_item": per_item, "by_stratum": _stratified(items, ok),
        "gcos": {"instrumented": bool(gcos), "n": len(deltas),
                 "mean_shift": (sum(deltas) / len(deltas)) if deltas else None, "p_value": p_value},
        "meets": meets,
    }


def informed_choice(ev: dict[str, list[dict]]) -> dict:
    sure = [e for e in ev.get("sure", []) if e.get("phase", "post") == "post"]
    ok = lambda e: int(e.get("score", 0)) == 4  # noqa: E731
    full = share(sum(ok(e) for e in sure), len(sure))
    flags = len(ev.get("coercion_flag", []))
    return {"sure_full": full, "by_stratum": _stratified(sure, ok), "coercion_flags": flags,
            "meets": bool(sure) and full["value"] >= THRESHOLDS["sure_full_share"]
                     and flags <= THRESHOLDS["coercion_flags_max"]}


def _hours(a: str, b: Optional[str]) -> Optional[float]:
    if not b:
        return None
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 3600


def loop_velocity(ev: dict[str, list[dict]]) -> dict:
    inc = [e for e in ev.get("booking", []) if e.get("incompatible")]
    hours = [_hours(e["result_ts"], e.get("booked_ts")) for e in inc]
    in_time = sum(h is not None and 0 <= h <= BOOKING_HOURS for h in hours)
    booked = share(in_time, len(inc))
    tasks = [e for e in ev.get("task", []) if e.get("kind") == "confirmatory"]
    done = share(sum(bool(e.get("completed")) for e in tasks), len(tasks))
    return {"booked_within_48h": booked, "confirmatory_completed": done,
            "late_or_unbooked": [e.get("couple_id") for e, h in zip(inc, hours) if h is None or h > BOOKING_HOURS],
            "meets": bool(inc) and booked["value"] >= THRESHOLDS["booked_within_48h_share"]
                     and bool(tasks) and done["value"] >= THRESHOLDS["confirmatory_completed_share"]}


def calibration(ev: dict[str, list[dict]]) -> dict:
    sweeps = ev.get("arithmetic_sweep", [])
    records = sum(int(e.get("records", 0)) for e in sweeps)
    mism = sum(int(e.get("mismatches", 0)) for e in sweeps)
    fhir = sum(int(e.get("errors", 0)) for e in ev.get("fhir_validation", []))
    return {"records_checked": records, "arithmetic_mismatches": mism,
            "arithmetic_error_share": share(mism, records), "fhir_errors": fhir,
            "meets": records > 0 and mism <= THRESHOLDS["arithmetic_mismatches_max"]
                     and bool(ev.get("fhir_validation")) and fhir <= THRESHOLDS["fhir_errors_max"]}


def leakage_table(ev: dict[str, list[dict]]) -> list[dict]:
    """Leakage-rate proof table rows: one per red-team category, with CI on the leak share."""
    rows = []
    for e in sorted(ev.get("redteam", []), key=lambda x: x.get("category", "")):
        n, k, leaks = int(e["n"]), int(e["intercepted"]), int(e.get("leaks", 0))
        rows.append({"category": e["category"], "n": n, "intercepted": share(k, n), "leaks": share(leaks, n),
                     **SIMULATED_STAMP})
    return rows


def privacy(ev: dict[str, list[dict]]) -> dict:
    rt = ev.get("redteam", [])
    n = sum(int(e["n"]) for e in rt)
    k = sum(int(e["intercepted"]) for e in rt)
    leaks = sum(int(e.get("leaks", 0)) for e in rt)
    scans = ev.get("leak_scan", [])
    scanned = sum(int(e.get("responses", 0)) for e in scans)
    live_leaks = sum(int(e.get("leaks", 0)) for e in scans)
    inter = share(k, n)
    return {"interception": inter, "redteam_leaks": leaks, "live_responses_scanned": scanned, "live_leaks": live_leaks,
            "live_leak_share": share(live_leaks, scanned), "table": leakage_table(ev),
            "meets": n > 0 and leaks + live_leaks <= THRESHOLDS["leaks_max"]
                     and inter["value"] >= THRESHOLDS["interception_share"]}


def guardrail_feed(api_events: Iterable[dict]) -> dict:
    """Aggregate GET /api/guardrail/events for the dashboard. Rejects events carrying extra fields (text/genes)."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {o: 0 for o in GUARDRAIL_OUTCOMES})
    for e in api_events:
        extra = set(e) - GUARDRAIL_KEYS
        if extra:
            raise ValueError(f"guardrail event carries non-contract fields: {sorted(extra)}")
        if e["outcome"] not in GUARDRAIL_OUTCOMES:
            raise ValueError(f"unknown outcome {e['outcome']!r}")
        counts[e["rule"]][e["outcome"]] += 1
    return {"by_rule": dict(counts), **SIMULATED_STAMP}


def evaluate(events: Iterable[dict]) -> dict:
    ev = _by_type(events)
    dims = {
        "comprehension": comprehension(ev),
        "informed_choice": informed_choice(ev),
        "loop_velocity": loop_velocity(ev),
        "calibration": calibration(ev),
        "privacy": privacy(ev),
    }
    for d in dims.values():
        d.update(SIMULATED_STAMP)
    return {"dimensions": dims, "thresholds": THRESHOLDS, **SIMULATED_STAMP}
