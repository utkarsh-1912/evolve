import { expect, test } from "@playwright/test";
import { openCase, signInOnShift } from "./helpers";

// docs/09 §10 clean-UI rules for the counselor app (TASK-P4-UI-CLEAN Wave B).

test("rail: collapsed at 1280 with tooltips, keyboard reachable, remembered toggle", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await signInOnShift(page);
  const rail = page.getByTestId("sidebar");
  await expect(rail).toHaveAttribute("data-collapsed", "true");
  const cases = page.getByTestId("rail-cases");
  await expect(cases).toHaveAttribute("aria-label", "Cases");
  await cases.focus();
  await expect(page.getByRole("tooltip")).toContainText("Cases");
  await page.getByTestId("rail-toggle").click();
  await expect(rail).toHaveAttribute("data-collapsed", "false");
  await page.reload();
  await expect(page.getByTestId("sidebar")).toHaveAttribute("data-collapsed", "false");
});

test("top bar + chips: icon controls have names; shift state stays visible text; chip detail in sr text", async ({ page }) => {
  await signInOnShift(page);
  await expect(page.getByTestId("shift-text")).toHaveText("On shift");
  await expect(page.getByTestId("density-toggle")).toHaveAttribute("aria-label", /Compact rows/);
  await expect(page.getByTestId("lang-switch")).toHaveAttribute("aria-label", /Language/);
  await expect(page.getByTestId("chip-scopes")).toContainText("user/Task.cru");
  await expect(page.getByTestId("chip-shift")).toContainText("On shift");
});

test("one SIMULATED marker per surface; never-icon-only texts stay visible", async ({ page }) => {
  await signInOnShift(page);
  await openCase(page, "V3", "b");
  await expect(page.locator("main [data-simulated]")).toHaveCount(1);
  // Never icon-only (docs/09 §10): compliance line, environment banner, human-closure action, locked numbers + "How it was counted".
  await expect(page.getByTestId("compliance-line")).toContainText("not a diagnosis");
  await expect(page.getByRole("region", { name: "Environment" })).toContainText("Simulated environment");
  await expect(page.getByTestId("action-closure")).toHaveText("Document human closure");
  await page.getByRole("tab", { name: /Variants/ }).click();
  await expect(page.getByTestId("locked-offspring_risk_one_in")).toHaveText(/1 in\s*321/);
  await expect(page.getByRole("button", { name: "How it was counted" }).first()).toBeVisible();
  await page.getByRole("tab", { name: /Tasks/ }).click();
  await expect(page.locator("main [data-simulated]")).toHaveCount(1);
  for (const path of ["/en/calendar", "/en/reports", "/en/design-system"]) {
    await page.goto(path);
    await expect(page.locator("main [data-simulated]")).toHaveCount(1);
  }
});
