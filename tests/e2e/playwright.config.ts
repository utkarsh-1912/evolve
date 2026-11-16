import { defineConfig, devices } from "@playwright/test";

// Cross-app smoke (Gate 3, qa-redteam). Backend: the live API on :8000 (uvicorn evolve_api.main:app --app-dir services/api
// --port 8000) must already be running. :8010 is forwarded to :8000 because the citizen live build bakes in :8010.
export default defineConfig({
  testDir: ".",
  testMatch: ["cross_app_smoke.spec.ts"],
  timeout: 90_000,
  workers: 1,
  reporter: [["list"]],
  use: { trace: "off", reducedMotion: "reduce" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    { command: "python port_forward.py 8010 8000", url: "http://localhost:8010/api/demo/vignettes", reuseExistingServer: false, timeout: 30_000 },
    { command: "npx next start --port 3000", cwd: "../../apps/citizen", url: "http://localhost:3000/en", reuseExistingServer: false,
      timeout: 120_000, env: { NEXT_DIST_DIR: ".next-live", NEXT_PUBLIC_API: "http://localhost:8010" } },
    { command: "npx next start --port 3001", cwd: "../../apps/counselor", url: "http://localhost:3001/en/sign-in", reuseExistingServer: false,
      timeout: 120_000, env: { NEXT_DIST_DIR: "dist", NEXT_PUBLIC_API: "http://localhost:8000" } },
    { command: "npx next start --port 3002", cwd: "../../apps/eval-dashboard", url: "http://localhost:3002/en", reuseExistingServer: false,
      timeout: 120_000 },
  ],
});
