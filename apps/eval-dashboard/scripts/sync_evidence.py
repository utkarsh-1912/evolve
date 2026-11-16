#!/usr/bin/env python3
"""Copy the evidence pack into the eval dashboard and derive the cohort views (R-EVAL-1, TASK-P4-UI-EVAL).

Nothing on the dashboard is typed by hand:
  * data/evidence.json  = byte-for-byte copy of services/eval/out/evidence.json (qa-redteam's pack).
  * data/cohort.json    = per-couple category + residual-risk bins, produced by running
                          services/risk_engine `assess_couple` over services/synth/out/cohort.json
                          (the same seed-42 synthetic cohort the pack's calibration used) and V1-V5.

This script does NO arithmetic on probabilities (P-02). It only:
  - copies locked RiskOutput records verbatim,
  - groups records whose locked `offspring_risk` value is identical (exact equality),
  - orders groups with the locked values' own ordering (comparison only),
  - counts records and couples.
Gene symbols and partner IDs are NOT written to data/cohort.json (P-12 style hygiene: the dashboard
shows aggregates; couples are anonymous indices).

Usage: python apps/eval-dashboard/scripts/sync_evidence.py   (also runs as `npm run sync` / prebuild)
Labelled SIMULATED: synthetic data only, not clinical findings.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import shutil
import sys

APP = pathlib.Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
EVIDENCE = ROOT / "services" / "eval" / "out" / "evidence.json"
COHORT = ROOT / "services" / "synth" / "out" / "cohort.json"
VIGNETTES = ["V1", "V2", "V3", "V4", "V5"]
OUT = APP / "data"

sys.path.insert(0, str(ROOT / "services" / "risk_engine"))
from risk_engine import assess_couple  # noqa: E402

# Couple category, highest-attention first. Pure set logic on locked scenario/status labels.
CATEGORIES = ["concordant_positive", "discordant_needs_counselor", "discordant_computed", "no_shared_finding"]


def category(records: list[dict]) -> str:
    scen = {r["scenario"] for r in records}
    if "concordant_positive" in scen or any(r["audience"] == "couple" for r in records):
        return "concordant_positive"
    if any(r["status"] == "needs_counselor" for r in records):
        return "discordant_needs_counselor"
    if records:
        return "discordant_computed"
    return "no_shared_finding"


def public_record(r: dict) -> dict:
    """Locked record without gene identity (bins are about values, not genes)."""
    keep = {k: v for k, v in r.items() if k not in ("gene", "hgnc_id", "carrier_role")}
    keep["gene"] = ""
    keep["hgnc_id"] = 0
    return keep


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    shutil.copyfile(EVIDENCE, OUT / "evidence.json")

    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    couples = cohort["couples"]

    cells: list[dict] = []
    bins: dict[float, dict] = {}
    not_computed = 0
    records_total = 0
    for i, c in enumerate(couples):
        recs = assess_couple(c)
        records_total += len(recs)
        related = c["relationship"]["type"] != "unrelated"
        cells.append({"i": i, "c": CATEGORIES.index(category(recs)), "r": related})
        for r in recs:
            v = r.get("offspring_risk")
            if v is None:
                not_computed += 1
                continue
            b = bins.setdefault(v, {"record": public_record(r), "count": 0, "scenarios": set(), "vignettes": []})
            b["count"] += 1
            b["scenarios"].add(r["scenario"])

    vignette_marks = []
    for v in VIGNETTES:
        doc = json.loads((ROOT / "tests" / "golden" / "cohort" / f"{v}.json").read_text(encoding="utf-8"))
        for r in assess_couple(doc["couples"][0]):
            val = r.get("offspring_risk")
            if val is None:
                vignette_marks.append({"vignette": v, "computed": False, "digest": r["digest"]})
                continue
            vignette_marks.append({"vignette": v, "computed": True, "digest": r["digest"]})
            if val in bins:
                if v not in bins[val]["vignettes"]:
                    bins[val]["vignettes"].append(v)
            else:  # vignette value not present in the cohort: own bar with count 0 (cohort), still marked
                bins[val] = {"record": public_record(r), "count": 0, "scenarios": {r["scenario"]}, "vignettes": [v]}

    ordered = [bins[k] for k in sorted(bins)]  # ordering by the locked value itself; no arithmetic
    hist = [{"record": b["record"], "count": b["count"], "scenarios": sorted(b["scenarios"]), "vignettes": b["vignettes"]}
            for b in ordered]

    counts = {name: 0 for name in CATEGORIES}
    related_counts = {name: 0 for name in CATEGORIES}
    for cell in cells:
        counts[CATEGORIES[cell["c"]]] += 1
        if cell["r"]:
            related_counts[CATEGORIES[cell["c"]]] += 1
    # grid is grouped by category (stable within a category, cohort order)
    grid = sorted(cells, key=lambda x: (x["c"], x["i"]))

    out = {
        "_label": "SIMULATED. Synthetic data only. Generated by apps/eval-dashboard/scripts/sync_evidence.py from "
                  "services/risk_engine.assess_couple over services/synth/out/cohort.json and tests/golden/cohort/V1..V5. "
                  "Do not edit by hand.",
        "simulated": True,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "sources": {
            "evidence_sha256": sha256(EVIDENCE),
            "cohort_sha256": sha256(COHORT),
            "cohort_seed": cohort.get("seed"),
            "cohort_contract_version": cohort.get("contract_version"),
        },
        "couples": len(couples),
        "records": records_total,
        "records_not_computed": not_computed,
        "categories": CATEGORIES,
        "category_counts": counts,
        "category_related_counts": related_counts,
        "grid": [[cell["c"], 1 if cell["r"] else 0] for cell in grid],
        "histogram": hist,
        "vignette_marks": vignette_marks,
    }
    (OUT / "cohort.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sync_evidence: evidence.json copied ({out['sources']['evidence_sha256'][:12]}), "
          f"{len(couples)} couples, {records_total} records, {len(hist)} bins, {not_computed} not computed")


if __name__ == "__main__":
    main()
