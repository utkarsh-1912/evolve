#!/usr/bin/env bash
# deploy.sh - one entry point for both deployment targets (DECISIONS #62). SIMULATED environment, synthetic data.
#   scripts/deploy/deploy.sh --target vm|vercel-render [--env-file FILE] [--dry-run]
# vm: validate env, `docker compose config`, then (unless --dry-run) build + start. vercel-render: validate + print
# the dashboard steps; never runs a cloud CLI or creates accounts. Secrets are never printed.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"
TARGET=""; ENVF=""; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --env-file) ENVF="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$TARGET" in vm|vercel-render) ;; *) echo "FAIL: --target vm|vercel-render is required" >&2; exit 2 ;; esac
[ -n "$ENVF" ] || ENVF="$ROOT/deploy/$TARGET/.env"
[ -f "$ENVF" ] || { echo "FAIL: env file not found: $ENVF (copy deploy/$TARGET/env.example to deploy/$TARGET/.env)" >&2; exit 1; }

get() {  # value of KEY in the env file (last wins), whitespace-trimmed
  grep -E "^[[:space:]]*$1=" "$ENVF" | tail -n 1 | cut -d= -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr -d '\r'
}
ERR=0; fail() { echo "FAIL: $*" >&2; ERR=1; }; warn() { echo "WARN: $*"; }

REQ="DEPLOY_TARGET API_URL CITIZEN_URL COUNSELOR_URL EVAL_URL CORS_ORIGINS"
[ "$TARGET" = vm ] && REQ="$REQ APP_DOMAIN ACME_EMAIL"
for k in $REQ; do [ -n "$(get "$k")" ] || fail "missing $k"; done
DT="$(get DEPLOY_TARGET)"; [ -z "$DT" ] || [ "$DT" = "$TARGET" ] || fail "DEPLOY_TARGET=$DT does not match --target $TARGET"
for k in API_URL CITIZEN_URL COUNSELOR_URL EVAL_URL; do
  v="$(get "$k")"; [ -z "$v" ] && continue
  case "$v" in https://*) ;; *) fail "$k must start with https://" ;; esac
  case "$v" in */) fail "$k must not end with /" ;; esac
done
CORS="$(get CORS_ORIGINS | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$' | sort | tr '\n' ',')"
APPS="$(printf '%s\n%s\n%s\n' "$(get CITIZEN_URL)" "$(get COUNSELOR_URL)" "$(get EVAL_URL)" | sort | tr '\n' ',')"
[ "$CORS" = "$APPS" ] || fail "CORS_ORIGINS must list exactly CITIZEN_URL, COUNSELOR_URL and EVAL_URL"
if [ "$TARGET" = vm ] && [ -n "$(get APP_DOMAIN)" ]; then
  d="$(get APP_DOMAIN)"
  [ "$(get CITIZEN_URL)" = "https://app.$d" ] || fail "CITIZEN_URL should be https://app.$d"
  [ "$(get COUNSELOR_URL)" = "https://counselor.$d" ] || fail "COUNSELOR_URL should be https://counselor.$d"
  [ "$(get EVAL_URL)" = "https://eval.$d" ] || fail "EVAL_URL should be https://eval.$d"
  [ "$(get API_URL)" = "https://api.$d" ] || fail "API_URL should be https://api.$d"
fi
if grep -Eq 'example\.(org|com)' "$ENVF"; then
  if [ "$DRY" = 1 ]; then warn "placeholder example.* values (fine for a dry run, not for a real deploy)"
  else fail "placeholder example.* values: fill in your real domain/URLs"; fi
fi
if [ -n "$(get SARVAM_API_KEY)" ]; then echo "SARVAM_API_KEY: set (not printed)"; else warn "SARVAM_API_KEY empty -> offline stub"; fi
echo "== evolve deploy: target=$TARGET env=$ENVF dry_run=$DRY"
[ "$ERR" = 0 ] || exit 1
echo "env file OK"

if [ "$TARGET" = vm ]; then
  command -v docker >/dev/null || { echo "FAIL: docker not found" >&2; exit 1; }
  docker compose --env-file "$ENVF" -f "$ROOT/deploy/vm/docker-compose.yml" config --quiet || { echo "FAIL: compose config invalid" >&2; exit 1; }
  echo "compose config OK"
  echo "Before starting: DNS for app., counselor., eval., api.$(get APP_DOMAIN) -> this VM; ports 80/443 open; eval data synced."
  if [ "$DRY" = 1 ]; then
    echo "DRY RUN: would now run: docker compose --env-file \"$ENVF\" -f deploy/vm/docker-compose.yml up -d --build"; exit 0
  fi
  docker info >/dev/null 2>&1 || { echo "FAIL: Docker daemon is not running" >&2; exit 1; }
  docker compose --env-file "$ENVF" -f "$ROOT/deploy/vm/docker-compose.yml" up -d --build || exit 1
  echo "Started. Reset log: docker compose -f deploy/vm/docker-compose.yml logs reset"
  echo "URLs: $(get CITIZEN_URL)/en $(get COUNSELOR_URL)/en $(get EVAL_URL)/en $(get API_URL)/api/demo/vignettes"
  echo "Then run the smoke checklist in docs/demo/DEPLOY.md."
  exit 0
fi

API="$(get API_URL)"
cat <<EOF

== Render (backend)
  1. dashboard.render.com -> New -> Blueprint -> this repo; Blueprint path: deploy/vercel-render/render.yaml
  2. Environment: CORS_ORIGINS = $(get CORS_ORIGINS)
                  SARVAM_API_KEY = <paste in the dashboard; leave unset for the offline stub>
  3. Deploy; check $API/api/demo/vignettes returns 5 vignettes.

== Vercel (3 projects; settings in deploy/vercel-render/vercel-projects.md), NEXT_PUBLIC_API = $API
  citizen:   Root apps/citizen;        Install 'cd ../.. && npm ci'; Build 'cd ../.. && npm run build --ignore-scripts -w evolve-citizen'
  counselor: Root apps/counselor;      Install 'cd ../.. && npm ci'; Build 'cd ../.. && npm run build --ignore-scripts -w evolve-counselor'
  eval:      Root apps/eval-dashboard; Install 'cd ../.. && npm ci'; Build 'cd ../.. && npm run build --ignore-scripts -w evolve-eval-dashboard'

== After all four are live
  - If a Vercel URL differs from the env file, update CORS_ORIGINS on Render and redeploy the backend.
  - Render free instances sleep and lose in-memory state. Before each demo: python deploy/vm/reset_on_start.py $API
  - Then run the smoke checklist in docs/demo/DEPLOY.md.
EOF
