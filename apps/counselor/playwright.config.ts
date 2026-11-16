import { defineConfig, devices } from "@playwright/test";

// SIMULATED mock adapter: build with NEXT_PUBLIC_API=mock first (npm run build:mock -w evolve-counselor).
// Live backend: see playwright.live.config.ts.
const PORT = 3111;
export default defineConfig({
  testDir: "./e2e",
  testIgnore: ["**/live.spec.ts"],
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.01, animations: "disabled" } },
  use: { baseURL: `http://localhost:${PORT}`, trace: "off", reducedMotion: "reduce" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npx next start --port ${PORT}`,
    url: `http://localhost:${PORT}/en/sign-in`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
