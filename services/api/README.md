# evolve API (P2 walking skeleton) — SIMULATED, synthetic data only

FastAPI modular monolith implementing `contracts/api.md` (v1.0.0 endpoints + v1.1.0 pinned bodies).
Decision support only, not a diagnosis or medical advice. Sign-in and the government adapters are SIMULATED.

## Run
From the repo root (local), or on a host that sets PORT (e.g. Render):

```
uvicorn evolve_api.main:app --app-dir services/api --host 0.0.0.0 --port ${PORT:-8000}
# or: cd services/api && python -m evolve_api   (binds HOST=0.0.0.0, PORT from env, default 8000)
```

Local default:

```
uvicorn evolve_api.main:app --app-dir services/api --port 8000
```

`evolve_api/bootstrap.py` puts `services/{agents,loop,risk_engine,privacy,fhir,synth}` on `sys.path`; no pip install of
our own packages. Dependencies: fastapi, uvicorn, httpx (TestClient), pydantic, plus what the P1 packages need.

## Quick demo (curl)
```
curl -X POST localhost:8000/api/demo/reset
curl -X POST localhost:8000/api/session -H 'content-type: application/json' -d '{"partner_id":"V1A"}'   # -> token
curl -X POST localhost:8000/api/demo/simulate-partner-consent -H 'content-type: application/json' -d '{"couple_id":"V1"}'
curl -X POST localhost:8000/api/couples/V1/compatibility -H "authorization: Bearer $TOKEN"
```

## Layout
- `evolve_api/main.py` — endpoints, token-to-partner scoping middleware (403 on any cross-partner reference),
  one AuditEvent per request, error shape `{"error": {"code", "message"}}`.
- Runtime agents, gate and orchestration: `services/agents/runtime/` (`runtime.bioethics.check` is the gate).
- Loop state machine and SIMULATED adapters: `services/loop/loopbus/`.

## Tests
```
cd services/api && python -m pytest -q
cd services/agents && python -m pytest -q
cd services/loop && python -m pytest -q
```

## Notes
- Template-first: the LLM paraphrase is off by default (DECISIONS #25); every message still passes the gate.
- Teach-back answers are booleans in the order of `runtime.templates.TEACHBACK` (the question endpoint is P3, v1.2.0).
- Keys are per process (privacy P1): restarting the server invalidates consents and tokens.

## Environment (v1.3.0, DECISIONS #62)
| var | effect |
|---|---|
| `SARVAM_API_KEY` | **PAUSED, not wired** (deployment first). When resumed: enables the counselor-side AI case-summary draft via Sarvam (`POST /api/counselor/cases/{id}/summary-draft`). Absent ⇒ deterministic offline stub. Never used for patient text (P-21; patient text stays closed templates) |
| `SARVAM_MODEL` | default `sarvam-105b` |
| `CORS_ORIGINS` | comma-separated extra origins for deployed apps; the localhost :3000/:3001/:3002 defaults are always allowed |
| `DEPLOY_TARGET` | `local` \| `vm` \| `vercel-render`, reported by `GET /api/config` |
Only synthetic, minimized, consented-scope fields are sent to Sarvam (its data-retention policy is not documented; TODO(verify) before any real data). Prompts and responses are never logged.
