#!/usr/bin/env bash
# reset_demo.sh - reseed the évolvé demo, pre-stage V3, warm the pages, print partner IDs, counselor login
# and URLs (R-DEMO-1). SIMULATED environment, synthetic data only. Needs: bash, curl, python.
#
#   scripts/demo/reset_demo.sh [--api URL] [--web URL] [--counselor URL] [--eval URL] [--no-warm] [--no-stage]
set -u

API="${EVOLVE_API:-http://localhost:8000}"
WEB="http://localhost:3000"; CNS="http://localhost:3001"; EVL="http://localhost:3002"
WARM=1; STAGE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --api) API="$2"; shift 2 ;;
    --web) WEB="$2"; shift 2 ;;
    --counselor) CNS="$2"; shift 2 ;;
    --eval) EVL="$2"; shift 2 ;;
    --no-warm) WARM=0; shift ;;
    --no-stage) STAGE=0; shift ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
# Pick a Python that actually runs (on Windows `python3` can be the Microsoft Store stub).
PY=""
for c in python python3 py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import json' >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "FAIL: no working python found (needed to parse JSON)" >&2; exit 1; }
jget() { "$PY" -c "import sys,json; print(json.load(sys.stdin)$1)"; }
post() {  # path [json-body] [token]
  local body="${2:-}"; [ -n "$body" ] || body='{}'
  if [ -n "${3:-}" ]; then
    curl -sS -m 30 -X POST "$API$1" -H 'content-type: application/json' -H "authorization: Bearer $3" -d "$body"
  else
    curl -sS -m 30 -X POST "$API$1" -H 'content-type: application/json' -d "$body"
  fi
}

echo "== evolve demo reset (SIMULATED, synthetic data only)"
echo "   api=$API"
RESET="$(post /api/demo/reset)" || { echo "FAIL: backend not reachable at $API" >&2; exit 1; }
echo "   reset -> $RESET"
[ "$(echo "$RESET" | jget '.get("status")')" = "ok" ] || { echo "FAIL: reset did not return status ok" >&2; exit 1; }

# Pre-stage V3: its locked records (explainer, gate-probe control) exist only after the couple check has run.
if [ "$STAGE" = "1" ]; then
  T="$(post /api/session '{"partner_id":"V3A"}' | jget '["token"]')" \
    && post /api/consents '{"counterpart":"V3B"}' "$T" >/dev/null \
    && post /api/demo/simulate-partner-consent '{"couple_id":"V3"}' >/dev/null \
    && C="$(post /api/couples/V3/compatibility '{}' "$T" | jget '["apsi"]["compatible"]')" \
    && echo "   staged V3 (SIMULATED partner consent): compatible=$C, records for V3A ready" \
    || echo "WARN: could not pre-stage V3. Run the V3 check by hand."
fi

echo
echo "== Partner IDs per vignette (SIMULATED sign-in: $WEB/en/sign-in)"
curl -sS -m 10 "$API/api/demo/vignettes" | "$PY" -c '
import sys, json
beat = {
  "V1": "LIVE  1:30  shared finding -> counselor handoff (trigger a). Sign in as A.",
  "V2": "SPARE       discordant complex locus -> confirmatory test for the carrier.",
  "V3": "LIVE  2:20  negative is not zero -> explainer. PRE-STAGED: sign in as A, open the explainer.",
  "V4": "LIVE  0:40  privacy test -> Compatible, nothing else revealed. Sign in as A, then B.",
  "V5": "SPARE       shared VUS in ROH -> held for counselor review, no Compatible headline.",
}
rows = json.load(sys.stdin)
for r in rows:
    cid = r["couple_id"]
    a, b = (r["partner_ids"] + ["?", "?"])[:2]
    print("  %-3s A=%-5s B=%-5s %s" % (cid, a, b, r["label"]))
    print("        " + beat.get(cid, ""))
if len(rows) != 5:
    print("WARN: expected 5 vignettes, got %d" % len(rows))
'
echo
echo "== Counselor login (SIMULATED): $CNS/en/sign-in -> 'Sign in (simulated)' -> switch 'On shift' ON"
echo "   (shift defaults to OFF; case data is hidden until you go on shift - DECISIONS #40)"

if [ "$WARM" = "1" ]; then
  echo
  echo "== Warming pages (first compile of each route in next dev is slow)"
  warm() {
    code="$(curl -s -o /dev/null -m 120 -w '%{http_code}' "$1")"
    if [ "$code" = "000" ]; then echo "   skip  $1 (not reachable)"; else echo "   $code   $1"; fi
  }
  for p in /en /en/sign-in /en/home /en/results /en/results/explainer /en/compatibility /en/care-plan /ar/home; do warm "$WEB$p"; done
  for p in /en/sign-in /en/queue; do warm "$CNS$p"; done
  warm "$EVL/en"
fi

echo
echo "== URLs"
echo "   citizen    $WEB/en"
echo "   counselor  $CNS/en"
echo "   eval       $EVL/en   (gate-probe panel + guardrail feed)"
echo "   api        $API/api/demo/vignettes"
echo "Follow docs/demo/DEMO-SCRIPT.md. Terminal fallback for the gate probe: python scripts/demo/gate_probe.py --api $API"
