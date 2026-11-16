import { test } from "@playwright/test";
import path from "node:path";

// Screenshot capture for DONE-P4-UI-EVAL (apps/eval-dashboard/screenshots/). Uses the REAL backend if it is up.
const OUT = path.join(__dirname, "..", "screenshots");

for (const width of [1280, 1920]) {
  for (const locale of ["en", "ar"] as const) {
    test(`capture ${locale} @${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1080 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto(`/${locale}`);
      await page.waitForTimeout(2500);
      await page.screenshot({ path: path.join(OUT, `${locale}-${width}-full.png`), fullPage: true });
      await page.screenshot({ path: path.join(OUT, `${locale}-${width}-01-top.png`) });
      if (locale === "en") {
        await page.getByTestId("probe-draft").fill("Your partner carries a gene change for thalassemia.");
        await page.getByTestId("probe-submit").click();
        await page.getByTestId("probe-result").locator("[data-testid=probe-held],[data-testid=probe-passed],[data-testid=probe-error]").first().waitFor();
        await page.waitForTimeout(2500);
        await page.locator("#probe").scrollIntoViewIfNeeded();
        await page.locator("#probe").screenshot({ path: path.join(OUT, `${locale}-${width}-02-gate-probe.png`) });
      }
    });
  }
}
