import { defineConfig, devices } from "@playwright/test";

// Build first (npm run build). The live spec needs the backend on :8000
// (uvicorn evolve_api.main:app --app-dir services/api --port 8000); other specs stub the two live endpoints.
// Port 3002: the backend CORS allow-list is :3000/:3001/:3002 (DECISIONS #38), so the live spec must run there.
const PORT = 3002;
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: `http://localhost:${PORT}`, trace: "off" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npx next start --port ${PORT}`,
    url: `http://localhost:${PORT}/en`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
