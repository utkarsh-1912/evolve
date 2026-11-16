import { expect, test } from "@playwright/test";
import { stubApi } from "./helpers";

// Visual regression at laptop (1280) and projector (1920) widths, EN + AR. Live feed stubbed with the fixture.
// Baselines: e2e/visual.spec.ts-snapshots/ (refresh: npx playwright test visual --update-snapshots).
for (const width of [1280, 1920]) {
  for (const locale of ["en", "ar"] as const) {
    test(`dashboard ${locale} @${width}`, async ({ page }) => {
      await stubApi(page);
      await page.setViewportSize({ width, height: 1080 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto(`/${locale}`);
      await page.getByTestId("feed-event").first().waitFor();
      await page.evaluate(() => document.fonts.ready);
      await expect(page).toHaveScreenshot(`dashboard-${locale}-${width}.png`, {
        fullPage: true,
        animations: "disabled",
        maxDiffPixelRatio: 0.01,
        // context chips and cohort caption carry the sync timestamp, which changes on every build
        mask: [page.getByTestId("context-strip"), page.getByTestId("cohort-caption")],
      });
    });
  }
}
