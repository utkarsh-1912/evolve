#!/usr/bin/env bash
# run_local.sh - no-Docker fallback for the évolvé demo (R-DEMO-1). SIMULATED, synthetic data only.
# Starts the backend (uvicorn) and the citizen, counselor and eval dev servers, waits for
# health, then runs reset_demo.sh. It never installs anything: missing dependencies are reported.
#
#   scripts/demo/run_local.sh                 # backend + citizen :3000 + counselor :3001 + eval :3002
#   scripts/demo/run_local.sh --mock          # OFFLINE: web apps on their SIMULATED mock adapters, no backend
#   scripts/demo/run_local.sh --no-web        # backend only
#   scripts/demo/run_local.sh --stop          # stop everything this script started
#   options: --api-port N (8000). Web ports are fixed: the backend CORS allow-list names 3000/3001/3002.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
TMPBASE="${TMPDIR:-${TEMP:-/tmp}}"
PIDFILE="$TMPBASE/evolve-demo-pids.txt"
LOGDIR="$TMPBASE/evolve-demo-logs"
API_PORT=8000; MOCK=0; NOWEB=0; STOP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --api-port) API_PORT="$2"; shift 2 ;;
    --mock) MOCK=1; shift ;;
    --no-web) NOWEB=1; shift ;;
    --stop) STOP=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

stop_demo() {
  [ -f "$PIDFILE" ] || { echo "Nothing to stop (no $PIDFILE)."; return 0; }
  while read -r pid; do
    [ -n "$pid" ] || continue
    if command -v taskkill >/dev/null 2>&1 && [ -n "${WINDIR:-}" ]; then
      # Git Bash on Windows: kill the Windows process tree (npm/uvicorn children included).
      wpid="$(cat /proc/$pid/winpid 2>/dev/null || echo "$pid")"
      taskkill //PID "$wpid" //T //F >/dev/null 2>&1 || kill "$pid" 2>/dev/null
    else
      pkill -TERM -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null
    fi
    echo "stopped pid $pid"
  done < "$PIDFILE"
  rm -f "$PIDFILE"
}
[ "$STOP" = "1" ] && { stop_demo; exit 0; }

wait_url() {  # url seconds
  local i=0
  while [ "$i" -lt "$2" ]; do
    curl -s -o /dev/null -m 5 "$1" && return 0
    i=$((i + 1)); sleep 1
  done
  return 1
}

PY=""
for c in python python3 py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import json' >/dev/null 2>&1; then PY="$c"; break; fi
done

mkdir -p "$LOGDIR"
[ -f "$PIDFILE" ] && { echo "A previous run is recorded in $PIDFILE - stopping it first."; stop_demo; }
API="http://localhost:$API_PORT"

# ---- prerequisites (report, never install)
missing=""
if [ "$MOCK" = "0" ]; then
  if [ -z "$PY" ] || ! "$PY" -c 'import fastapi, uvicorn, pydantic, cryptography, jsonschema' >/dev/null 2>&1; then
    missing="$missing\n  - Python + packages (fastapi uvicorn pydantic cryptography jsonschema; see scripts/allowed_deps.txt)"
  fi
fi
if [ "$NOWEB" = "0" ] && [ ! -d "$ROOT/node_modules" ]; then
  missing="$missing\n  - node_modules at the repo root (run 'npm ci' at the repo root once, before the demo day)"
fi
if [ -n "$missing" ]; then printf "Missing prerequisites:%b\n" "$missing" >&2; exit 1; fi

# ---- backend
if [ "$MOCK" = "0" ]; then
  echo "Starting backend on $API ..."
  (cd "$ROOT" && exec "$PY" -m uvicorn evolve_api.main:app --app-dir services/api --port "$API_PORT") \
    >"$LOGDIR/api.log" 2>&1 &
  echo $! >> "$PIDFILE"
  if ! wait_url "$API/api/demo/vignettes" 60; then
    echo "Backend did not become healthy in 60 s. Log: $LOGDIR/api.log" >&2; stop_demo; exit 1
  fi
  echo "Backend healthy."
fi

# ---- web apps (each app's own `dev` script pins its port: citizen 3000, counselor 3001, eval 3002)
if [ "$NOWEB" = "0" ]; then
  if [ "$MOCK" = "1" ]; then
    unset NEXT_PUBLIC_API
    echo "OFFLINE MODE: citizen and counselor use their SIMULATED mock adapters. No backend calls."
  else
    export NEXT_PUBLIC_API="$API"
  fi
  export NEXT_TELEMETRY_DISABLED=1
  for spec in citizen:apps/citizen:3000 counselor:apps/counselor:3001 eval:apps/eval-dashboard:3002; do
    name="${spec%%:*}"; rest="${spec#*:}"; dir="${rest%%:*}"; port="${rest##*:}"
    echo "Starting $name on http://localhost:$port ..."
    (cd "$ROOT/$dir" && exec npm run dev) >"$LOGDIR/$name.log" 2>&1 &
    echo $! >> "$PIDFILE"
  done
  for spec in citizen:3000 counselor:3001 eval:3002; do
    if wait_url "http://localhost:${spec##*:}/en" 240; then echo "${spec%%:*} up."
    else echo "${spec%%:*} did not answer in 240 s. Log: $LOGDIR/${spec%%:*}.log" >&2; fi
  done
fi

# ---- reset + warm
if [ "$MOCK" = "0" ]; then
  if [ "$NOWEB" = "1" ]; then "$HERE/reset_demo.sh" --api "$API" --no-warm
  else "$HERE/reset_demo.sh" --api "$API"; fi
fi
echo
echo "Running. PIDs in $PIDFILE, logs in $LOGDIR. Stop with: scripts/demo/run_local.sh --stop"
