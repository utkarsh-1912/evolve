# Vercel project settings (one project per app, same repo)

Create three Vercel projects from the same Git repo. Settings per project (Project → Settings → General / Build / Environment Variables):

| Setting | citizen | counselor | eval |
|---|---|---|---|
| Framework preset | Next.js | Next.js | Next.js |
| Root Directory | `apps/citizen` | `apps/counselor` | `apps/eval-dashboard` |
| Include files outside root directory | **On** (the apps import `packages/ui` and `design/`) | On | On |
| Install Command | `cd ../.. && npm ci` | `cd ../.. && npm ci` | `cd ../.. && npm ci` |
| Build Command | `cd ../.. && npm run build --ignore-scripts -w evolve-citizen` | `cd ../.. && npm run build --ignore-scripts -w evolve-counselor` | `cd ../.. && npm run build --ignore-scripts -w evolve-eval-dashboard` |
| Output Directory | default (`.next`) | default | default |
| Node.js version | 22.x | 22.x | 22.x |
| Env `NEXT_PUBLIC_API` (Production) | Render URL, e.g. `https://evolve-api.onrender.com` | same | same |
| Env `NEXT_TELEMETRY_DISABLED` | `1` | `1` | `1` |

Notes:
- `NEXT_PUBLIC_API` is inlined at build time. Changing it needs a redeploy.
- `--ignore-scripts` skips the eval dashboard's python `prebuild`. Vercel ships the committed `apps/eval-dashboard/data/*.json`, so run `npm run sync -w evolve-eval-dashboard` locally and commit/push before deploying.
- After the three projects exist, put their production origins in Render's `CORS_ORIGINS` and redeploy the backend.
- These settings have NOT been tried on Vercel by the build agents: TODO(verify) on the first deploy.
