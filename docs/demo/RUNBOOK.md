# évolvé demo: one-page runbook (R-DEMO-1)

## The day before
- [ ] `npm ci` at the repo root has been run once (the scripts never install anything).
- [ ] `python scripts/guardrail_check.py` → `guardrail_check: OK`.
- [ ] The eval dashboard shows pack build 2026-11-16 (held-out v1 retired 89.6%, v2 62.4%). If not: `npm run sync -w evolve-eval-dashboard`.
- [ ] One full human run-through of docs/demo/DEMO-SCRIPT.md, timed. Automated rehearsals were not done (lean P5); human rehearsal is the team's job.
- [ ] Fallback screenshots are at hand: `apps/citizen/screenshots/p3/cit/`, `apps/counselor/screenshots/`, `apps/eval-dashboard/screenshots/`.

## 30 minutes before
- [ ] Laptop on mains power. Notifications and Focus assist off. Fonts already cached (open each app once).
- [ ] `powershell -ExecutionPolicy Bypass -File scripts\demo\run_local.ps1`. Wait for "Running." (about 3 min). The output shows the partner IDs, the counselor login and the URLs.
- [ ] Ports: backend 8000 (otherwise use `-ApiPort 8020`); web 3000/3001/3002 must be free (CORS).
- [ ] Browser at 100% zoom, a 1280 or 1920 window, tabs T1–T6 open as in the script's Setup. Counselor is **On shift**.
- [ ] Check: T4 (V3A) explainer shows "1 in 321"; the gate probe (T6) holds row 1.
- [ ] Right before going on: `scripts\demo\reset_demo.ps1 -NoWarm`. It also re-stages V3. Then refresh the tabs and sign in again.

## If something fails
| Symptom | Do this |
|---|---|
| Backend down or 5xx | `run_local.ps1 -Stop`, then `run_local.ps1 -Mock` (SIMULATED mock adapters, recorded from the real backend). Describe the gate probe instead of running it. |
| "Unauthorized" or consent errors after a restart | Keys are per process. Reset, then sign in again in every tab. |
| Port clash at start | The script refuses and names the port. Free it, or use `-ApiPort 8020`. |
| Projector cuts content | Switch to a 1280 px window. The layouts are tested at 1280 and 1920. |
| Counselor queue empty | Off shift (turn on **On shift**), or the V1 check hasn't run yet. |
| V3 explainer says "Run your compatibility check first" | Re-run `reset_demo.ps1` (it stages V3), then refresh. |
| A locked number looks different | Stop. Do not improvise. Report it after the demo. |

## Afterwards
- [ ] `scripts\demo\run_local.ps1 -Stop`.
