import { defineConfig, devices } from "@playwright/test";

// Live verification against the real backend (contracts/api.md v1.2.1):
//   1) uvicorn evolve_api.main:app --app-dir services/api --port 8000
//   2) NEXT_PUBLIC_API=http://localhost:8000 NEXT_DIST_DIR=dist npx next build
//   3) npx playwright test -c playwright.live.config.ts
// Port 3001 is the counselor origin the backend's CORS allows (DECISIONS #38).
const PORT = 3001;
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["**/live.spec.ts"],
  timeout: 60_000,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: `http://localhost:${PORT}`, trace: "off", reducedMotion: "reduce" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npx next start --port ${PORT}`,
    url: `http://localhost:${PORT}/en/sign-in`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: { NEXT_DIST_DIR: "dist", NEXT_PUBLIC_API: "http://localhost:8000" },
  },
});
