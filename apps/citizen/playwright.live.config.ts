import { defineConfig, devices } from "@playwright/test";

// Same journeys against the LIVE backend (services/api via uvicorn on :8010, its own instance so other agents'
// servers are untouched). Build first: npm run build:live. The app runs on :3000 (an origin the backend's CORS allows).
const API = "http://localhost:8010";
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["journeys.spec.ts", "smoke.spec.ts", "security.spec.ts"],
  timeout: 60_000,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:3000", trace: "off" },
  projects: [{ name: "live-chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "python -m uvicorn evolve_api.main:app --app-dir ../../services/api --port 8010",
      url: `${API}/api/demo/vignettes`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { PYTHONDONTWRITEBYTECODE: "1" },
    },
    {
      command: "npx next start --port 3000",
      url: "http://localhost:3000/en",
      reuseExistingServer: false,
      timeout: 120_000,
      env: { NEXT_DIST_DIR: ".next-live", NEXT_PUBLIC_API: API },
    },
  ],
});
process.env.EVOLVE_LIVE = "1";
process.env.EVOLVE_API = API;
