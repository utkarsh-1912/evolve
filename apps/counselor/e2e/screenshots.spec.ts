import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { openCase, openTab, signIn, signInOnShift } from "./helpers";

// Review captures for DONE-P3-UI-CNS (apps/counselor/screenshots/). SIMULATED data.
const OUT = path.join(__dirname, "..", "screenshots");
const shot = (page: Page, name: string) => page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });

test("capture: desktop EN", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await signIn(page);
  await expect(page.getByTestId("off-shift")).toBeVisible();
  await shot(page, "01-off-shift-en");
  await page.getByTestId("shift-switch").click();
  await expect(page.locator("[data-testid=case-table] tbody tr[tabindex]")).toHaveCount(5);
  await shot(page, "02-queue-en");
  await openCase(page, "V1", "a");
  await shot(page, "03-case-V1-brief-en");
  await openTab(page, /Pedigree/);
  await shot(page, "04-case-V1-pedigree-en");
  await openTab(page, /Variants/);
  await shot(page, "05-case-V1-variants-en");
  await page.goto("/en/queue");
  await openCase(page, "V3", "b");
  await openTab(page, /Variants/);
  await shot(page, "06-case-V3-variants-en");
  await openTab(page, /Tasks/);
  await shot(page, "07-case-V3-tasks-en");
  await page.goto("/en/queue");
  await openCase(page, "V5", "c");
  await openTab(page, /Pedigree/);
  await shot(page, "08-case-V5-pedigree-en");
  await openTab(page, /Variants/);
  await shot(page, "09-case-V5-variants-en");
  await page.goto("/en/queue");
  await openCase(page, "V4", "d");
  await shot(page, "10-case-V4-brief-outside-consent-en");
  await openTab(page, /Variants/);
  await shot(page, "11-case-V4-variants-outside-consent-en");
  await page.getByTestId("action-closure").click();
  await page.getByTestId("closure-summary").fill("Teach-back reviewed together; questions answered.");
  await page.getByTestId("closure-next").click();
  await expect(page.getByTestId("closure-confirm")).toBeVisible();
  await page.screenshot({ path: path.join(OUT, "12-closure-confirm-en.png") });
  await page.getByTestId("closure-confirm").getByRole("button", { name: "Cancel" }).click();
  await openTab(page, /Timeline/);
  await shot(page, "13-case-V4-timeline-en");
  await page.goto("/en/reports");
  await page.getByTestId("reports").waitFor();
  await shot(page, "14-reports-en");
  await page.goto("/en/design-system");
  await page.getByTestId("design-system").waitFor();
  await shot(page, "15-design-system-en");
});

test("capture: AR desktop + mobile", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await signInOnShift(page, "ar");
  await shot(page, "16-queue-ar");
  await openCase(page, "V1", "a");
  await page.locator('[role=tab][id$="-trigger-pedigree"]').click();
  await shot(page, "17-case-V1-pedigree-ar");
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto("/ar/queue");
  await expect(page.locator("[data-testid=case-table] tbody tr[tabindex]")).toHaveCount(5);
  await shot(page, "18-queue-ar-mobile");
});

test("capture: mobile EN", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await signInOnShift(page);
  await shot(page, "19-queue-en-mobile");
  await openCase(page, "V3", "b");
  await shot(page, "20-case-V3-en-mobile");
});
