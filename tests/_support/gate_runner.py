"""Shared BioethicsSupervisor corpus runner (R-EVAL-2). Black box: uses only runtime.bioethics.check / GateContext."""
from __future__ import annotations

import importlib
import json
import pathlib
from collections import defaultdict

import qa_support as qs

RULES = {"numeric_drift", "leakage", "directive", "uae_law", "missing_judicial_statement", "stigma",
         "false_reassurance", "gate_error"}


def load_cases(directory: pathlib.Path) -> list[dict]:
    cases = []
    for f in sorted(directory.glob("*.yaml")):
        text = "\n".join(l for l in f.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
        cases += json.loads(text)["cases"]
    return cases


def load_gate():
    qs.add_path("runtime")
    try:
        return importlib.import_module("runtime.bioethics"), None
    except ModuleNotFoundError as e:
        if e.name in ("runtime", "runtime.bioethics"):
            return None, f"runtime.bioethics not built yet: {e}"
        raise


def make_ctx(bio, case: dict):
    kw = qs.gate_context_kwargs(case["recipient"], case["lang"], case["kind"])
    kw.update(case.get("ctx_overrides") or {})
    GC = getattr(bio, "GateContext", None)
    if GC is None:
        return kw
    try:
        return GC(**kw)
    except TypeError:
        return kw


def _get(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def run_gate(bio, draft, ctx):
    try:
        res = bio.check(draft, ctx)
    except Exception as e:  # fail-closed per contract
        return False, set(), f"{type(e).__name__}: {e}"
    passed = _get(res, "passed")
    rules = {_get(v, "rule") for v in (_get(res, "violations") or [])}
    if not isinstance(passed, bool):
        return False, rules, "passed not bool"
    return passed, rules, None


def evaluate(bio, case: dict) -> dict:
    ctx = make_ctx(bio, case)
    draft = case["turns"][case["blocked_turn"]] if "turns" in case else case["draft"]
    passed, rules, error = run_gate(bio, draft, ctx)
    expect = case["expect"]
    if not expect:
        ok = passed and error is None
    elif expect == ["*"]:
        ok = not passed
    else:
        ok = (not passed) and bool(rules & set(expect))
    return {"id": case["id"], "category": case["category"], "lang": case["lang"], "ok": ok, "passed": passed,
            "rules": sorted(r for r in rules if r), "error": error,
            "wrong_rule": bool(expect) and expect != ["*"] and not passed and not (rules & set(expect)),
            "tags": case.get("tags", [])}


def summarize(results: list[dict], benign_category: str = "benign_control") -> dict:
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    cats = {}
    for cat, rs in sorted(by_cat.items()):
        cats[cat] = {
            "n": len(rs), "ok": sum(r["ok"] for r in rs), "pass_rate": round(sum(r["ok"] for r in rs) / len(rs), 4),
            "en": f"{sum(r['ok'] for r in rs if r['lang'] == 'en')}/{sum(r['lang'] == 'en' for r in rs)}",
            "ar": f"{sum(r['ok'] for r in rs if r['lang'] == 'ar')}/{sum(r['lang'] == 'ar' for r in rs)}",
            "wrong_rule": sum(r["wrong_rule"] for r in rs), "errors": sum(r["error"] is not None for r in rs),
            "failed_ids": [r["id"] for r in rs if not r["ok"]],
        }
    adv = [r for r in results if r["category"] != benign_category]
    ben = [r for r in results if r["category"] == benign_category]
    fp = sum(not r["ok"] for r in ben)
    return {"categories": cats,
            "adversarial": {"n": len(adv), "intercepted": sum(r["ok"] for r in adv),
                            "rate": round(sum(r["ok"] for r in adv) / max(1, len(adv)), 4)},
            "benign": {"n": len(ben), "false_positives": fp, "fp_rate": round(fp / max(1, len(ben)), 4)}}
