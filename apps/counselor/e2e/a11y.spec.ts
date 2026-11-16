import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { FIXED_NOW, openCase, signIn, signInOnShift } from "./helpers";

// axe 0 serious/critical on every counselor route and every case tab, EN + AR (docs/09 §7).
test.describe.configure({ timeout: 120_000 });
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function axe(page: Page, name: string) {
  const r = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  const bad = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  console.log(`axe ${name}: ${r.violations.length} total, ${bad.length} serious/critical`, bad.map((v) => `${v.id}(${v.nodes.length}) ${v.nodes[0]?.target} :: ${v.nodes[0]?.failureSummary}`));
  expect(bad, name).toEqual([]);
}

for (const locale of ["en", "ar"] as const) {
  test(`axe ${locale}: sign-in, off-shift, design system`, async ({ page }) => {
    await page.clock.setFixedTime(FIXED_NOW);
    await page.goto(`/${locale}/sign-in`);
    await axe(page, `${locale}/sign-in`);
    await page.goto(`/${locale}/queue`);
    await expect(page.getByTestId("signed-out")).toBeVisible();
    await axe(page, `${locale}/queue signed-out`);
    await signIn(page, locale);
    await expect(page.getByTestId("off-shift")).toBeVisible();
    await axe(page, `${locale}/queue off-shift`);
    await page.goto(`/${locale}/design-system`);
    await page.getByTestId("design-system").waitFor();
    await axe(page, `${locale}/design-system`);
  });

  test(`axe ${locale}: queue, cases, calendar, reports`, async ({ page }) => {
    await signInOnShift(page, locale);
    await axe(page, `${locale}/queue`);
    for (const path of ["/cases", "/calendar", "/reports"]) {
      await page.goto(`/${locale}${path}`);
      await page.waitForLoadState("networkidle");
      await page.locator("main [aria-busy=true]").first().waitFor({ state: "detached" }).catch(() => {});
      await axe(page, `${locale}${path}`);
    }
  });

  for (const [couple, trigger] of [["V1", "a"], ["V4", "d"]] as const) {
    test(`axe ${locale}: every case tab ${couple} (${trigger}) + action dialogs`, async ({ page }) => {
      await signInOnShift(page, locale);
      await openCase(page, couple, trigger);
      await page.evaluate(() => window.scrollTo(0, 0));
      for (const tab of ["brief", "pedigree", "variants", "tasks", "notes", "timeline"]) {
        await page.locator(`[role=tab][id$="-trigger-${tab}"]`).click();
        await axe(page, `${locale} case ${couple} ${tab}`);
      }
      await page.locator(`[role=tab][id$="-trigger-brief"]`).click();
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.getByTestId("action-closure").click();
      await axe(page, `${locale} ${couple} closure dialog`);
      await page.keyboard.press("Escape");
      await page.getByTestId("action-schedule").click();
      await axe(page, `${locale} ${couple} schedule confirm`);
    });
  }
}
