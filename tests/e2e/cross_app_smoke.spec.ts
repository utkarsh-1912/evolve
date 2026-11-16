import { expect, test } from "@playwright/test";

// Gate 3 cross-app smoke (qa-redteam). Real backend, nothing mocked; synthetic vignettes only.
// reset -> V1 citizen result shows the shared gene + "1 in 4" -> case in the counselor queue as trigger (a)
// -> the eval dashboard's gate-probe holds a leaky draft.
const API = "http://localhost:8000/api";

test("cross-app: V1 shared result -> counselor (a) -> gate-probe holds leak", async ({ browser, request }) => {
  expect((await request.post(`${API}/demo/reset`)).ok()).toBeTruthy();

  // Citizen (V1A)
  const citizen = await (await browser.newContext()).newPage();
  await citizen.goto("http://localhost:3000/en/sign-in");
  await citizen.getByTestId("signin-V1A").click();
  await expect(citizen).toHaveURL(/\/en\/home$/);
  await citizen.goto("http://localhost:3000/en/compatibility");
  const toggle = citizen.getByTestId("consent-toggle");
  await expect(toggle).toBeEnabled();
  if ((await toggle.getAttribute("aria-checked")) !== "true") await toggle.click();
  const simulate = citizen.getByTestId("simulate-partner");
  if (await simulate.count()) {
    await simulate.click();
    await expect(simulate).toHaveCount(0);
  }
  await citizen.getByTestId("run-check").click();
  const result = citizen.getByTestId("result");
  await expect(result).toBeVisible({ timeout: 15_000 });
  await expect(result).toHaveAttribute("data-result", "shared");
  await expect(citizen.getByTestId("locked-offspring_risk_one_in")).toHaveText(/^1 in\s+4$/);
  await expect(citizen.locator("main")).toContainText("HBB");
  await expect(citizen.getByTestId("judicial")).toBeVisible();

  // Counselor
  const counselor = await (await browser.newContext()).newPage();
  await counselor.goto("http://localhost:3001/en/sign-in");
  await counselor.getByTestId("sign-in").click();
  await counselor.waitForURL(/\/en\/queue/);
  await counselor.getByTestId("shift-switch").click();
  const caseRow = counselor.locator("[data-testid=case-table] tbody tr", { hasText: "(a)" });
  await expect(caseRow).toHaveCount(1, { timeout: 15_000 });
  await caseRow.click();
  await expect(counselor.getByTestId("case-view")).toHaveAttribute("data-trigger", "a");
  await counselor.getByRole("tab", { name: /Variants/ }).click();
  await expect(counselor.getByTestId("variant-record")).toHaveAttribute("data-gene", "HBB");

  // Eval dashboard gate-probe: partner A's private gene drafted to partner B (P-06)
  const evalPage = await (await browser.newContext()).newPage();
  await evalPage.goto("http://localhost:3002/en#probe");
  await evalPage.getByTestId("probe-draft").fill("Your partner carries a MEFV variant.");
  await evalPage.getByRole("combobox", { name: "Recipient (synthetic partner)" }).click();
  await evalPage.getByRole("option", { name: /^V4B/ }).click();
  await evalPage.getByTestId("probe-submit").click();
  await expect(evalPage.getByTestId("probe-held")).toBeVisible({ timeout: 15_000 });
  await expect(evalPage.getByTestId("probe-rules").locator('[data-rule="leakage"]').first()).toBeVisible();
});
