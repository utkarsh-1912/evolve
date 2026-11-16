import { expect, test } from "@playwright/test";

// Gate probe against the REAL backend (BioethicsSupervisor is never mocked in integration tests, AGENTS.md §5).
// Requires: uvicorn evolve_api.main:app --app-dir services/api --port 8000
const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

test.beforeAll(async ({ request }) => {
  const r = await request.get(`${API}/api/guardrail/events`).catch(() => null);
  test.skip(!r || !r.ok(), `backend not reachable at ${API}`);
});

test("leaky draft to V4B is held, rules shown, matching event highlighted in the feed", async ({ page }) => {
  await page.goto("/en#probe");
  await page.getByTestId("probe-draft").fill("Your partner carries a gene change for thalassemia.");
  await page.getByRole("combobox", { name: "Recipient (synthetic partner)" }).click();
  await page.getByRole("option", { name: /^V4B/ }).click();
  await page.getByTestId("probe-submit").click();
  await expect(page.getByTestId("probe-held")).toBeVisible();
  await expect(page.getByTestId("probe-held")).toContainText("Held, not sent");
  await expect(page.getByTestId("probe-rules").locator('[data-rule="leakage"]')).toBeVisible();
  await expect(page.getByTestId("feed-probe-event")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("feed-probe-event")).toHaveAttribute("data-outcome", "blocked");
  await expect(page.getByTestId("probe-event")).toContainText("blocked");
});

test("a second probe highlights its own event, not the previous one", async ({ page }) => {
  await page.goto("/en#probe");
  await page.getByTestId("probe-draft").fill("A genetic counselor reviews every result and can talk it through with you.");
  await page.getByTestId("probe-submit").click();
  await expect(page.getByTestId("probe-passed").or(page.getByTestId("probe-held"))).toBeVisible();
  await expect(page.getByTestId("feed-probe-event")).toBeVisible({ timeout: 10_000 });
  const passed = await page.getByTestId("probe-passed").isVisible();
  await expect(page.getByTestId("feed-probe-event")).toHaveAttribute("data-outcome", passed ? "passed" : "blocked");
});
