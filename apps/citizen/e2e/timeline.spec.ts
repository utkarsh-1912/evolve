import { expect, test } from "@playwright/test";

// DECISIONS #50 item 4 (P-04): a loop state that was jumped over renders as "Skipped", never as completed.
for (const locale of ["en", "ar"] as const) {
  test(`CareTimeline marks jumped-over states as Skipped (${locale})`, async ({ page }) => {
    await page.goto(`/${locale}/design-system`);
    const tl = page.getByTestId("ds-timeline-skipped");
    await expect(tl).toBeVisible();
    const skipped = tl.locator('li[data-status="skipped"]');
    await expect(skipped).toHaveCount(1);
    await expect(skipped).toContainText("Confirmatory test done");
    await expect(skipped.getByTestId("timeline-skipped")).toHaveText("Skipped");
    await expect(skipped).not.toContainText("Completed");
    await expect(tl.locator('li[data-status="complete"]')).toHaveCount(3);
    await expect(tl.locator('li[data-status="current"]')).toContainText("Counseling done");
  });
}
