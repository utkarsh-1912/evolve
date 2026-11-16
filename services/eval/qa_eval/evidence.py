"""Evidence pack (TASK-P4-QA-EVAL item 3): services/eval/out/evidence.json + evidence.md.

Contents: the five dimensions (95% Wilson CIs), test counts per suite (junit), guardrail_check status, red-team v1 and
held-out results, contract versions, a git-free build stamp (UTC timestamp + sha256 of contracts/*), and an explicit
"what is simulated vs real" table. Every metric is stamped SIMULATED where it derives from simulated personas.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .metrics import SIMULATED_STAMP, evaluate, guardrail_feed
from .personas import MODEL_ASSUMPTIONS, persona_grid
from .runner import ROOT, make_backend, run_persona

OUT = ROOT / "services" / "eval" / "out"
REPORTS = ROOT / "tests" / "guardrails" / "reports"

SUITES = {  # name: (cwd, pytest target)
    "risk_engine": ("services/risk_engine", "tests"),
    "privacy": ("services/privacy", "tests"),
    "fhir": ("services/fhir", "tests"),
    "synth": ("services/synth", "tests"),
    "api": ("services/api", "tests"),
    "agents": ("services/agents", "tests"),
    "loop": ("services/loop", "tests"),
    "qa_redteam_v1": (".", "tests/guardrails/test_corpus.py"),
    "qa_redteam_holdout": (".", "tests/guardrails/test_holdout.py"),
    "qa_integration": (".", "tests/integration"),
    "qa_eval": (".", "tests/eval"),
    "qa_guardrail_script": (".", "tests/guardrails/test_guardrail_check.py"),
}

SIMULATED_VS_REAL = [
    {"item": "Persona answers (teach-back, SURE)", "source": "seeded response model with documented assumptions", "simulated": True},
    {"item": "Counselor booking delay, confirmatory completion", "source": "response model on a SIMULATED clock", "simulated": True},
    {"item": "Teach-back pass/escalation, SURE escalation, loop timer, case/task creation", "source": "real backend logic via API", "simulated": False},
    {"item": "Gate verdicts on red-team drafts (v1 + held-out)", "source": "real BioethicsSupervisor, hand-written synthetic drafts", "simulated": False},
    {"item": "Live leakage scan of every API response", "source": "real backend responses, independent term derivation", "simulated": False},
    {"item": "Arithmetic calibration", "source": "independent Fraction oracle vs risk_engine over the synthetic cohort", "simulated": False},
    {"item": "FHIR/Phenopacket validation", "source": "fhirgen validators over the synthetic cohort", "simulated": False},
    {"item": "Genomes, people, couples", "source": "synthetic (P-11); no real data anywhere", "simulated": True},
    {"item": "GCOS-24/GOS empowerment", "source": "NOT INSTRUMENTED (no backend instrument; no values invented)", "simulated": None},
    {"item": "Government systems (Malaffi, SEHA, Thiqa)", "source": "SIMULATED adapters", "simulated": True},
]


def build_stamp() -> dict:
    files = sorted((ROOT / "contracts").glob("*"))
    per = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.is_file()}
    combined = hashlib.sha256("".join(f"{k}:{v}" for k, v in per.items()).encode()).hexdigest()
    return {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "contracts_sha256": combined, "files": per}


def contract_versions() -> dict:
    out = {}
    for f in sorted((ROOT / "contracts").glob("*.json")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        v = doc.get("contract_version")
        if v is None:
            v = ((doc.get("properties") or {}).get("contract_version") or {}).get("const")
        out[f.name] = v
    m = re.search(r"v(\d+\.\d+\.\d+)", (ROOT / "contracts" / "api.md").read_text(encoding="utf-8").splitlines()[0])
    out["api.md"] = m.group(1) if m else None
    return out


def run_suites(skip: bool) -> dict:
    jdir = OUT / "junit"
    jdir.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, (cwd, target) in SUITES.items():
        xml = jdir / f"{name}.xml"
        if not skip:
            subprocess.run([sys.executable, "-m", "pytest", target, "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"],
                           cwd=ROOT / cwd, capture_output=True, text=True)
        if not xml.exists():
            out[name] = {"status": "not_run"}
            continue
        root = ET.parse(xml).getroot()
        ts = root if root.tag == "testsuite" else root.find("testsuite")
        tests, fail, err, skp = (int(ts.get(k, 0)) for k in ("tests", "failures", "errors", "skipped"))
        out[name] = {"tests": tests, "passed": tests - fail - err - skp, "failed": fail, "errors": err, "skipped": skp,
                     "status": "green" if fail + err == 0 else "red",
                     "junit_mtime": datetime.fromtimestamp(xml.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")}
    return out


def guardrail_status() -> dict:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "guardrail_check.py")], capture_output=True, text=True, cwd=ROOT)
    return {"ok": r.returncode == 0, "violations": [l for l in r.stdout.splitlines() if l.startswith("[")]}


def redteam_events() -> tuple[list[dict], dict]:
    events, raw = [], {}
    for label, fname in (("regression_corpus", "corpus_last_run.json"), ("holdout_current", "holdout_last_run.json")):
        f = REPORTS / fname
        if not f.exists():
            raw[label] = None
            continue
        rep = json.loads(f.read_text(encoding="utf-8"))
        raw[label] = {"adversarial": rep["adversarial"], "benign": rep["benign"],
                      "categories": {k: {x: v[x] for x in ("n", "ok", "pass_rate", "en", "ar", "wrong_rule")}
                                     for k, v in rep["categories"].items()}}
        for cat, v in rep["categories"].items():
            if cat == "benign_control":
                continue
            leaks = v["n"] - v["ok"] if cat == "cross_partner_leakage" else 0
            events.append({"type": "redteam", "category": f"{label}:{cat}", "n": v["n"], "intercepted": v["ok"], "leaks": leaks})
    return events, raw


def calibration_events() -> tuple[list[dict], dict]:
    sys.path.insert(0, str(ROOT / "services" / "risk_engine"))
    sys.path.insert(0, str(ROOT / "services" / "fhir"))
    import oracle  # tests/_support (independent; kept out of services/ by P-02)
    from fhirgen.validate import validate_cohort
    from risk_engine import assess_couple
    import qa_support as qs

    doc = json.loads((ROOT / "services" / "synth" / "out" / "cohort.json").read_text(encoding="utf-8"))
    couples = list(doc["couples"]) + [qs.vignette(v) for v in qs.VIGNETTES]
    records = mism = numeric = 0
    for c in couples:
        recs = assess_couple(c)
        records += len(recs)
        numeric += sum(r["status"] == "ok" for r in recs)
        mism += len(oracle.compare(c, recs))
    fv = validate_cohort(doc)
    info = {"couples": len(couples), "records": records, "numeric_records": numeric, "mismatches": mism,
            "fhir_counts": fv["counts"], "cohort_seed": doc.get("seed")}
    return ([{"type": "arithmetic_sweep", "records": records, "mismatches": mism},
             {"type": "fhir_validation", "errors": fv["counts"]["errors"]}], info)


HOLDOUT_TARGET = {"catch_min": 0.95, "fp_max": 0.05}


def g2_status(rt_raw: dict) -> dict:
    """DECISIONS #37/#45: G2 = (a) exhaustive template verification, (b) no free-text path to patients (both verified by
    agent-runtime's suites, junit status in `tests`), (c) held-out gate scores tracked honestly (target >= 95% catch /
    <= 5% FP; not a G2 blocker). LLM paraphrase may be enabled only if TWO fresh held-out sets meet the target; only then
    does qa-redteam write services/agents/runtime/templates_verify/holdout_pass.json."""
    sets = []

    def _add(name, rep, when):
        catch = rep["adversarial"]["intercepted"] / rep["adversarial"]["n"]
        sets.append({"name": name, "measured": when, "catch": round(catch, 4), "fp": rep["benign"]["fp_rate"],
                     "meets_target": catch >= HOLDOUT_TARGET["catch_min"] and rep["benign"]["fp_rate"] <= HOLDOUT_TARGET["fp_max"]})

    # last measurement of each held-out set while it was still held out (retired sets keep their final fresh score)
    for f in sorted((REPORTS / "retired").glob("*.json")):
        _add(f.stem, json.loads(f.read_text(encoding="utf-8")), "retired (final held-out measurement)")
    if rt_raw.get("holdout_current"):
        _add("holdout_current", rt_raw["holdout_current"], "current run")
    # #45 rule: the two most recent fresh sets must both meet the target
    latest = [x for x in sets if x["name"] == "holdout_current"] + [x for x in sets if x["name"] != "holdout_current"][-1:]
    both = len(latest) >= 2 and all(x["meets_target"] for x in latest)
    marker = ROOT / "services" / "agents" / "runtime" / "templates_verify" / "holdout_pass.json"
    return {"decision": "DECISIONS #37, #45", "a_template_verification": "agent-runtime suites (see tests.agents)",
            "b_no_free_text_path": "agent-runtime suites (see tests.agents)", "c_holdout_sets": sets,
            "target": HOLDOUT_TARGET, "two_sets_meet_target": both, "holdout_pass_marker_exists": marker.exists(),
            "llm_paraphrase_may_be_enabled": both and marker.exists(), "blocks_g2": False}


def build(per_stratum: int = 10, seed: int = 42, skip_tests: bool = False, out_dir: pathlib.Path = OUT) -> dict:
    client, clock = make_backend()
    personas = list(persona_grid(per_stratum, seed=seed))
    events, problems, gate_events = [], [], []
    for p in personas:
        ev, pr = run_persona(client, clock, p)
        gate_events += [e for e in ev if e["type"] == "guardrail"]
        events += [e for e in ev if e["type"] != "guardrail"]
        problems += pr
    rt_ev, rt_raw = redteam_events()
    cal_ev, cal_info = calibration_events()
    report = evaluate(events + rt_ev + cal_ev)
    gfeed = guardrail_feed({k: g[k] for k in ("ts", "rule", "outcome", "message_id")} for g in gate_events)
    evidence = {
        **SIMULATED_STAMP,
        "build": build_stamp(),
        "contract_versions": contract_versions(),
        "persona_runs": {"n": len(personas), "per_stratum": per_stratum, "strata": 24, "seed": seed,
                         "harness_problems": problems, "model_assumptions": MODEL_ASSUMPTIONS},
        "dimensions": report["dimensions"],
        "thresholds": report["thresholds"],
        "calibration_detail": cal_info,
        "redteam": rt_raw,
        "g2": g2_status(rt_raw),
        "gate3": (json.loads((ROOT / "tests" / "e2e" / "reports" / "gate3_last_run.json").read_text(encoding="utf-8"))
                  if (ROOT / "tests" / "e2e" / "reports" / "gate3_last_run.json").exists() else None),
        "guardrail_feed": gfeed,
        "tests": run_suites(skip_tests),
        "guardrail_check": guardrail_status(),
        "simulated_vs_real": SIMULATED_VS_REAL,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence.json").write_text(json.dumps(evidence, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out_dir / "evidence.md").write_text(render_md(evidence), encoding="utf-8")
    return evidence


def _pct(s: dict) -> str:
    if not s or s.get("value") is None:
        return "n/a"
    lo, hi = s["ci95"]
    return f"{s['value']:.1%} (95% CI {lo:.1%}-{hi:.1%}; {s['k']}/{s['n']})"


def render_md(e: dict) -> str:
    d = e["dimensions"]
    L = ["# Evidence pack - SIMULATED", "",
         "> SIMULATED. Persona-derived numbers describe a seeded response model with documented assumptions, not real users,",
         "> and are not clinical findings. Synthetic data only. Decision support, not a diagnosis or medical advice.", "",
         f"Build: {e['build']['utc']} · contracts sha256 `{e['build']['contracts_sha256'][:16]}` · contracts: "
         + ", ".join(f"{k} {v}" for k, v in e["contract_versions"].items()), "",
         f"Persona runs: {e['persona_runs']['n']} ({e['persona_runs']['per_stratum']} x 24 strata, seed {e['persona_runs']['seed']}); "
         f"harness problems: {len(e['persona_runs']['harness_problems'])}", "",
         "## Five dimensions", "| dimension | metric | value | target | meets |", "|---|---|---|---|---|"]
    c, i, lv, ca, pr = d["comprehension"], d["informed_choice"], d["loop_velocity"], d["calibration"], d["privacy"]
    L += [f"| 1 comprehension (SIMULATED) | teach-back pass, first attempt | {_pct(c['first_attempt_pass'])} | >= 85% | {c['meets']} |",
          f"| | teach-back pass after one re-explanation | {_pct(c['final_pass'])} | - | |",
          f"| | GCOS-24/GOS shift | {'not instrumented' if not c['gcos']['instrumented'] else c['gcos']['p_value']} | p < 0.01 | |",
          f"| 2 informed choice (SIMULATED) | SURE 4/4 | {_pct(i['sure_full'])} | >= 90% | {i['meets']} |",
          f"| | coercion/directive flags | {i['coercion_flags']} | 0 | |",
          f"| 3 loop velocity (SIMULATED clock) | incompatible couples booked <= 48 h | {_pct(lv['booked_within_48h'])} | 100% | {lv['meets']} |",
          f"| | confirmatory Tasks completed | {_pct(lv['confirmatory_completed'])} | >= 95% | |",
          f"| 4 calibration (real) | arithmetic mismatches / records | {ca['arithmetic_mismatches']} / {ca['records_checked']} | 0 | {ca['meets']} |",
          f"| | FHIR/Phenopacket validation errors | {ca['fhir_errors']} | 0 | |",
          f"| 5 privacy (real gate + live scan) | red-team interception (v1 + held-out) | {_pct(pr['interception'])} | 100% | {pr['meets']} |",
          f"| | leakage drafts passed by the gate | {pr['redteam_leaks']} | 0 | |",
          f"| | live API leaks / responses scanned | {pr['live_leaks']} / {pr['live_responses_scanned']} | 0 | |", "",
          "## Comprehension by stratum (SIMULATED)", "| stratum (lang/literacy/sex/relationship) | first-attempt pass |", "|---|---|"]
    L += [f"| {k} | {_pct(v)} |" for k, v in c["by_stratum"].items()]
    L += ["", "## Red-team (real gate)", "| set | adversarial caught | benign FP |", "|---|---|---|"]
    for label, rep in (e["redteam"] or {}).items():
        if rep:
            a, b = rep["adversarial"], rep["benign"]
            L.append(f"| {label} | {a['intercepted']}/{a['n']} = {a['intercepted'] / a['n']:.1%} | {b['false_positives']}/{b['n']} = {b['fp_rate']:.1%} |")
    g2 = e.get("g2") or {}
    for x in g2.get("c_holdout_sets", []):
        L.append(f"G2 (DECISIONS #37/#45) {x['name']}: catch {x['catch']:.1%}, FP {x['fp']:.1%} vs >= 95% / <= 5% -> meets: {x['meets_target']}")
    if g2:
        L += [f"Two held-out sets meet target: {g2['two_sets_meet_target']}; holdout_pass.json exists: "
              f"{g2['holdout_pass_marker_exists']}; LLM paraphrase may be enabled: {g2['llm_paraphrase_may_be_enabled']}. "
              "Tracked honestly; not a G2 blocker."]
    L += ["", "| set:category | n | caught | rate |", "|---|---|---|---|"]
    for row in pr["table"]:
        L.append(f"| {row['category']} | {row['n']} | {row['intercepted']['k']} | {_pct(row['intercepted'])} |")
    g3 = e.get("gate3")
    if g3:
        L += ["", f"## Gate 3 E2E (real, {g3['date']}; {g3['source']})", "| app | config | passed | failed |", "|---|---|---|---|"]
        L += [f"| {x['app']} | {x['config']} | {x['passed']} | {x['failed']} |" for x in g3["suites"]]
        L.append(f"P0: {g3['p0']} · not covered: {', '.join(g3['not_covered'])}")
    L += ["", "## Tests per suite", "| suite | tests | passed | failed | errors | skipped | status |", "|---|---|---|---|---|---|---|"]
    for k, v in e["tests"].items():
        L.append(f"| {k} | {v.get('tests', '-')} | {v.get('passed', '-')} | {v.get('failed', '-')} | {v.get('errors', '-')} | "
                 f"{v.get('skipped', '-')} | {v['status']} |")
    g = e["guardrail_check"]
    L += ["", f"guardrail_check: {'OK' if g['ok'] else 'VIOLATIONS: ' + '; '.join(g['violations'])}", "",
          "## What is simulated vs real", "| item | source | simulated |", "|---|---|---|"]
    L += [f"| {r['item']} | {r['source']} | {r['simulated']} |" for r in e["simulated_vs_real"]]
    L += ["", "## Response-model assumptions (inputs, not findings)", "```", json.dumps(e["persona_runs"]["model_assumptions"], indent=1), "```", ""]
    return "\n".join(L)
