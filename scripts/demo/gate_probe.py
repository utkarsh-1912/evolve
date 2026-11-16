#!/usr/bin/env python3
"""Live guardrail-block probe for the évolvé demo (R-DEMO-1, R-AGT-2). SIMULATED, synthetic data only.

Sends hand-written bad drafts to POST /api/demo/gate-probe (BioethicsSupervisor only; nothing is delivered
to anyone) and prints which rule stopped each one. This is the terminal fallback for the
{{PENDING: gate-probe panel UI}} beat in docs/demo/DEMO-SCRIPT.md.

    python scripts/demo/gate_probe.py [--api http://localhost:8000] [--only directive|numeric|leakage|donor|control]

The drafts are deliberately wrong. They exist to be blocked. Stdlib only.
Exit 0 when every "must block" draft is blocked by the expected rule.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

JUDICIAL = "The marriage health certificate is issued regardless of your genetic results."

# (key, recipient, draft, expected rule or None for the positive control)
PROBES = [
    ("directive", "V1A",
     "Given this result, you should cancel the marriage. " + JUDICIAL, "directive"),
    ("numeric", "V3A",
     "For your couple, the chance is about 1 in 50, compared with 1 in 3,800 for an unrelated couple. " + JUDICIAL,
     "numeric_drift"),
    ("leakage", "V4B",
     "Your partner carries a MEFV variant for Familial Mediterranean Fever. " + JUDICIAL, "leakage"),
    ("donor", "V2A",
     "You could consider using donor eggs to avoid the condition. " + JUDICIAL, "uae_law"),
    ("control", "V3A",
     "For your couple, the chance is about 1 in 321, compared with 1 in 3,800 for an unrelated couple. " + JUDICIAL,
     None),
]


def post(api: str, body: dict) -> dict:
    req = urllib.request.Request(api.rstrip("/") + "/api/demo/gate-probe", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.environ.get("EVOLVE_API", "http://localhost:8000"))
    ap.add_argument("--only", choices=[p[0] for p in PROBES])
    args = ap.parse_args()

    print("== BioethicsSupervisor gate probe (SIMULATED; drafts are never delivered)")
    ok = True
    for key, to, draft, expect in PROBES:
        if args.only and key != args.only:
            continue
        try:
            res = post(args.api, {"recipient_partner_id": to, "draft": draft, "lang": "en"})
        except (urllib.error.URLError, OSError) as e:
            print(f"FAIL: backend not reachable at {args.api} ({e})")
            return 1
        rules = sorted({v["rule"] for v in res.get("violations", [])})
        print(f"\n[{key}] to {to}")
        print(f"  draft : {draft}")
        if expect is None:
            if res.get("passed"):
                print("  gate  : PASSED (locked numbers match; this one may be sent)")
            else:
                print(f"  gate  : blocked {rules} - expected once V3 compatibility has run in this session "
                      "(the locked records exist only after the check)")
            continue
        verdict = "BLOCKED" if not res.get("passed") else "PASSED (unexpected)"
        print(f"  gate  : {verdict} by {rules}")
        if res.get("passed") or expect not in rules:
            ok = False
            print(f"  WARN  : expected rule {expect!r}")
    print("\n== " + ("all must-block drafts were blocked" if ok else "SOME DRAFTS WERE NOT BLOCKED AS EXPECTED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
