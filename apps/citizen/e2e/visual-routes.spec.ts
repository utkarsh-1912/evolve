import { expect, test, type Page } from "@playwright/test";
import { runCompatibility, signIn } from "./helpers";

// docs/09 §7 visual regression: 10 key routes × EN/AR × 360/1280 (mock adapter, fixed clock).
// Baselines: e2e/visual-routes.spec.ts-snapshots/ (refresh: npx playwright test visual-routes --update-snapshots).
const FIXED = new Date("2026-11-09T09:00:00Z");
const HIDE = "e2e/hide-toasts.css"; // hides transient toasts

async function snap(page: Page, name: string) {
  // Shelled pages: wait until the context strip's async chips (couple + consent status) have rendered.
  const strip = page.getByTestId("context-strip");
  if ((await strip.count()) && (await strip.getByText("…").count())) await expect(strip.getByText("…")).toHaveCount(0);
  if (await strip.count()) await expect(strip.locator("[data-status]")).toHaveCount(3);
  await page.evaluate(() => document.fonts.ready);
  await expect(page).toHaveScreenshot(name, { fullPage: true, animations: "disabled", stylePath: HIDE, maxDiffPixelRatio: 0.01 });
}

for (const width of [360, 1280]) {
  for (const locale of ["en", "ar"] as const) {
    test(`routes ${locale} @${width}`, async ({ page }) => {
      test.setTimeout(180_000);
      await page.clock.setFixedTime(FIXED);
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      const go = async (p: string, wait: string) => {
        await page.goto(`/${locale}${p}`);
        await page.getByTestId(wait).first().waitFor();
      };
      const id = `${locale}-${width}`;
      await page.goto(`/${locale}`);
      await snap(page, `01-landing-${id}.png`);
      await go("/sign-in", "signin-V1A");
      await snap(page, `02-sign-in-${id}.png`);
      await signIn(page, "V3A", locale);
      await runCompatibility(page, locale);
      await snap(page, `03-compatibility-${id}.png`);
      await go("/home", "next-step");
      await page.getByTestId("activity-list").waitFor();
      await snap(page, `04-home-${id}.png`);
      await go("/results", "vault-calls");
      await snap(page, `05-results-${id}.png`);
      await go("/results/explainer", "explainer");
      await snap(page, `06-explainer-${id}.png`);
      await go("/teachback", "teachback-question");
      await snap(page, `07-teachback-${id}.png`);
      await go("/care-plan", "care-timeline");
      await snap(page, `08-care-plan-${id}.png`);
      await go("/privacy", "audit-table");
      await page.getByTestId("audit-table").locator("tbody tr").first().waitFor();
      await snap(page, `09-privacy-${id}.png`);
      await go("/help", "promises");
      await snap(page, `10-help-${id}.png`);
    });
  }
}
