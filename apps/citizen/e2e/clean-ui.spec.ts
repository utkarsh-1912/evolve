import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { runCompatibility, signIn } from "./helpers";

// TASK-P4-UI-CLEAN Wave A (docs/09 §10): icon rail, tooltips, compact chips, one SIMULATED badge, never-icon-only list.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test("rail: collapsed by default ≤1440 px, keyboard focus shows tooltip, toggle remembered, axe clean with tooltip open", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await signIn(page, "V1A");
  const rail = page.getByTestId("sidebar");
  await expect(rail).toHaveAttribute("data-collapsed", "true");
  const results = page.getByTestId("rail-results");
  await expect(results).toHaveAttribute("aria-label", "My results");
  await results.focus();
  await expect(page.getByRole("tooltip")).toContainText("My results");
  const r = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  expect(r.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/en\/results$/);
  const toggle = page.getByTestId("rail-toggle");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(rail).toHaveAttribute("data-collapsed", "false");
  await expect(page.getByTestId("rail-results")).toContainText("My results");
  await page.reload();
  await expect(page.getByTestId("sidebar")).toHaveAttribute("data-collapsed", "false");
});

test("rail: expanded by default on wide screens", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await signIn(page, "V1A");
  await expect(page.getByTestId("sidebar")).toHaveAttribute("data-collapsed", "false");
});

test("RTL: rail sits on the right, chips and icon top bar render", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await signIn(page, "V1A", "ar");
  const box = await page.getByTestId("sidebar").boundingBox();
  expect(box && box.x > 640).toBeTruthy();
  await expect(page.getByTestId("lang-switch")).toHaveAttribute("aria-label", /English/);
});

test("context chips: short label visible, full detail on focus and for screen readers", async ({ page }) => {
  await signIn(page, "V1A");
  await runCompatibility(page);
  const chip = page.getByTestId("chip-consent");
  await expect(chip).toContainText("Consent active");
  await chip.focus();
  await expect(page.getByRole("tooltip")).toContainText("Active until");
  await expect(chip.locator(".sr-only")).toContainText("Active until");
});

test("one SIMULATED badge per surface; never-icon-only items keep their text", async ({ page }) => {
  await signIn(page, "V1A");
  for (const path of ["/home", "/results", "/care-plan", "/privacy", "/help"]) {
    await page.goto(`/en${path}`);
    await page.locator("main h1").waitFor();
    await expect(page.locator("main [data-simulated]"), path).toHaveCount(1);
  }
  await runCompatibility(page);
  await expect(page.locator("main [data-simulated]")).toHaveCount(1);
  // never icon-only (docs/09 §10)
  await expect(page.getByTestId("compliance-line")).toHaveText(/not a diagnosis/);
  await expect(page.getByTestId("judicial")).toHaveText(/regardless/);
  await expect(page.getByTestId("revoke")).toHaveText(/Withdraw/);
  await expect(page.getByTestId("counselor-handoff")).toContainText("genetic counselor");
  await expect(page.getByRole("button", { name: "How it was counted" }).first()).toBeVisible();
  await expect(page.getByRole("region", { name: "Environment" })).toContainText(/Simulated environment/i);
});
