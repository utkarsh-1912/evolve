import { expect, test } from "@playwright/test";

// Visual regression target (docs/09 §2/§7): the living style guide at 360 and 1280, EN + AR.
// Baselines live in e2e/visual.spec.ts-snapshots/ (create/refresh with: npx playwright test visual --update-snapshots).
for (const width of [360, 1280]) {
  for (const locale of ["en", "ar"] as const) {
    test(`design-system ${locale} @${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto(`/${locale}/design-system`);
      await page.getByTestId("ds-root").waitFor();
      await page.evaluate(() => document.fonts.ready);
      await expect(page).toHaveScreenshot(`design-system-${locale}-${width}.png`, {
        fullPage: true,
        animations: "disabled",
        maxDiffPixelRatio: 0.01,
      });
    });
  }
}
