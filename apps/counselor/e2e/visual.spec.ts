import { expect, test } from "@playwright/test";
import { FIXED_NOW, openCase, openTab, signInOnShift } from "./helpers";

// Visual regression (docs/09 §7): the counselor style guide at 360/1280 EN/AR, plus the V1 pedigree and V3 variants.
for (const locale of ["en", "ar"] as const) {
  for (const width of [360, 1280]) {
    test(`design-system ${locale} ${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.clock.setFixedTime(FIXED_NOW);
      await page.goto(`/${locale}/design-system`);
      await page.getByTestId("design-system").waitFor();
      await expect(page.getByTestId("design-system")).toHaveScreenshot(`ds-${locale}-${width}.png`);
    });
  }
}

test("case V1 pedigree + V3 variants (EN 1280)", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await signInOnShift(page);
  await openCase(page, "V1", "a");
  await openTab(page, /Pedigree/);
  await expect(page.getByTestId("pedigree-graph")).toHaveScreenshot("case-V1-pedigree.png");
  await page.goto("/en/queue");
  await openCase(page, "V3", "b");
  await openTab(page, /Variants/);
  await expect(page.getByTestId("variants-list")).toHaveScreenshot("case-V3-variants.png");
});
