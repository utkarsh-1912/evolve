# évolvé: web deployment (two targets, one switch)

DECISIONS #62 · env contract: contracts/api.md v1.3.0 (`SARVAM_API_KEY`, `SARVAM_MODEL`, `CORS_ORIGINS`, `DEPLOY_TARGET`). The deployed demo is still a **SIMULATED environment with synthetic data only**. It is decision support, not a diagnosis.

**You** create the accounts (VM provider or Render + Vercel, Sarvam) and paste keys into dashboards or a local `.env` file. **Never put a real key in the repo.** `deploy/.gitignore` ignores `.env` files, the Docker build contexts exclude them, and `scripts/guardrail_check.py` scans for secrets.

## Pick a target
| | `vm` | `vercel-render` |
|---|---|---|
| What | one Linux VM: Docker Compose + Caddy (automatic HTTPS) | backend on Render, the 3 apps on Vercel |
| Cost/ops | you run one VM | free tiers; nothing to run yourself |
| State | the backend stays up; restart = reset | **free Render instances sleep after ~15 min idle and restart with empty memory** |
| URLs | `app.` / `counselor.` / `eval.` / `api.` + your domain | `*.vercel.app` + `*.onrender.com` (or custom domains) |

One entry point for both:
```
powershell -ExecutionPolicy Bypass -File scripts\deploy\deploy.ps1 -Target vm|vercel-render [-EnvFile <file>] [-DryRun]
scripts/deploy/deploy.sh --target vm|vercel-render [--env-file <file>] [--dry-run]
```
The script validates the env file before doing anything:
- required keys are present
- `DEPLOY_TARGET` matches the target
- URLs use https and have no trailing slash
- `CORS_ORIGINS` equals exactly the three app URLs
- the VM subdomains match `APP_DOMAIN`
- no placeholder domains remain (outside a dry run)

Secrets are never printed. Then:
- **vm:** runs `docker compose config`, then builds and starts the stack.
- **vercel-render:** prints the dashboard steps with your values filled in. It never runs a cloud CLI.

## Before either target
1. The backend must read `CORS_ORIGINS` and `SARVAM_*` from the environment (api.md v1.3.0, agent-runtime). Check that `GET /api/config` exists locally. If the backend still has the hard-coded localhost CORS list, the deployed apps will be blocked by CORS.
2. Sync the eval dashboard data and commit it: `npm run sync -w evolve-eval-dashboard`. Both targets build with `--ignore-scripts`, which skips the eval app's python `prebuild`, and they ship the committed `apps/eval-dashboard/data/*.json`.
3. Optional: get a Sarvam API key (counselor-side AI draft only, English, synthetic input; DECISIONS #62). Without a key, the offline stub is used. Sarvam's data-retention policy is unverified, so never send real data to it (TODO(verify)).

## Target `vm`
1. Create a Linux VM (2 vCPU / 4 GB RAM is enough for the Next builds) with Docker Engine + Compose v2. Open ports 80 and 443.
2. DNS: point `app.`, `counselor.`, `eval.` and `api.<your-domain>` (A/AAAA) at the VM's IP.
3. On the VM, copy the repo and run `cp deploy/vm/env.example deploy/vm/.env`. Then edit `.env`:
   - `APP_DOMAIN`, `ACME_EMAIL`
   - the four URLs and `CORS_ORIGINS` (same domain)
   - optionally `SARVAM_API_KEY`
4. Dry run: `scripts/deploy/deploy.sh --target vm --dry-run`.
5. Deploy: `scripts/deploy/deploy.sh --target vm`. This builds 4 images (about 10 min on the first build) and starts:
   - api, citizen, counselor and eval, each with a healthcheck and `restart: unless-stopped`
   - Caddy, which obtains certificates on first request
   - a one-shot `reset` job that reseeds V1–V5 and pre-stages V3
6. Check the reset: `docker compose -f deploy/vm/docker-compose.yml logs reset` should show `reset: {... "status": "ok" ...}` and `staged V3`.
7. Reset before each demo: `docker compose --env-file deploy/vm/.env -f deploy/vm/docker-compose.yml up reset`, or `python deploy/vm/reset_on_start.py https://api.<domain>`.
8. Update: pull, then run the deploy script again (`--build`). Changing `APP_DOMAIN` needs a rebuild, because `NEXT_PUBLIC_API` is baked in at build time.

## Target `vercel-render`
1. **Render (backend):**
   1. In dashboard.render.com: New → Blueprint → connect the repo → Blueprint path `deploy/vercel-render/render.yaml`.
   2. If your account only reads `./render.yaml`, create a **Web Service** by hand using the file's values:
      - runtime Python, `PYTHON_VERSION=3.13.1`
      - build: `pip install …` (pinned list in render.yaml)
      - start: `uvicorn evolve_api.main:app --app-dir services/api --host 0.0.0.0 --port $PORT`
      - health check path `/api/demo/vignettes`
   3. Set `CORS_ORIGINS` after step 2, and `SARVAM_API_KEY` (secret, optional).
   4. Deploy. `https://<service>.onrender.com/api/demo/vignettes` must list 5 vignettes.
2. **Vercel (3 projects):** create one project per app from the same repo with the settings in `deploy/vercel-render/vercel-projects.md`:
   - root directory `apps/<app>`, include files outside the root
   - install `cd ../.. && npm ci`
   - build `cd ../.. && npm run build --ignore-scripts -w <workspace>`
   - env `NEXT_PUBLIC_API=<Render URL>`
3. Put the three Vercel production URLs into `deploy/vercel-render/.env` (copied from `env.example`) and into Render's `CORS_ORIGINS`, then redeploy the backend.
4. Validate and print the checklist: `scripts/deploy/deploy.sh --target vercel-render`.
5. **Sleep and state:**
   - A free Render instance sleeps after about 15 minutes idle. The first request then takes up to about a minute.
   - On wake the process restarts with **empty in-memory state**: consents, sessions and per-process keys are gone, and the vignettes are reseeded at start-up.
   - Browser tabs signed in before the restart will get 401/409. Sign in again.
   - **Right before each demo**, wake and reset in one step: `python deploy/vm/reset_on_start.py https://<service>.onrender.com`. It retries for about 60 s while the instance wakes, then reseeds and pre-stages V3.
   - A paid instance avoids the sleep.

## Post-deploy smoke checklist (both targets, about 5 min)
- [ ] `<API_URL>/api/demo/vignettes` → 5 vignettes (V1–V5).
- [ ] `<API_URL>/api/config` → `environment` equals your target; `ai_draft_enabled` matches whether a key is set.
- [ ] Reset ran (`staged V3`).
- [ ] Citizen `<CITIZEN_URL>/en`:
  - [ ] padlock, "Simulated environment" banner, decision-support footer
  - [ ] sign in as **V4A** → Compatibility → consent → Simulate partner agreeing → Run the private check → **"Compatible"**, no gene name
  - [ ] the browser devtools console shows no CORS or CSP errors
- [ ] V1A: same flow → "1 in 4", counselor handoff, certificate line.
- [ ] V3A: `/en/results/explainer` → "1 in 321" vs "1 in 3,800".
- [ ] Counselor `<COUNSELOR_URL>/en`: sign in (simulated) → On shift → queue shows V1 (a) and V3 (b) → open V1 → "Viewing under: couple consent ✔ · on shift ✔". The AI draft is labelled AI-generated, or the offline stub is used.
- [ ] Eval `<EVAL_URL>/en`:
  - [ ] the guardrail feed reads Live
  - [ ] Gate probe: leaky draft to V4B → **"Held, not sent"**, rule `leakage`
- [ ] AR: switch to العربية → right-to-left layout.
- [ ] No real key appears anywhere in the repo: `python scripts/guardrail_check.py` → OK.

## What was verified by the build agent (not by a real deployment)
- **Done:**
  - `docker compose config` on `deploy/vm/docker-compose.yml` with `env.example` (valid; values interpolated)
  - the deploy scripts' dry-run and failure paths, for both targets
  - `guardrail_check` OK
- **Not done:**
  - Docker image builds (the daemon was off on the build machine)
  - any Render or Vercel deployment (no accounts, by design)
  - Caddy certificate issuance

  Treat the Vercel/Render settings as TODO(verify) on first use.
