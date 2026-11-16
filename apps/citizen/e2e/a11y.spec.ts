import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { runCompatibility, signIn } from "./helpers";

// TASK-P3-UI-DS quality gate: axe 0 serious/critical on the design system and every existing route, EN + AR.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function axe(page: Page, name: string) {
  // Transient toasts (fade animation) are excluded; their static states are checked on /design-system.
  const r = await new AxeBuilder({ page }).withTags(TAGS).exclude("li[data-swipe-direction]").analyze();
  const bad = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  console.log(`axe ${name}: ${r.violations.length} total, ${bad.length} serious/critical`, bad.map((v) => `${v.id}(${v.nodes.length}) ${v.nodes[0]?.target}`));
  expect(bad, name).toEqual([]);
}

for (const locale of ["en", "ar"] as const) {
  test(`axe ${locale}: public routes + design system (both themes)`, async ({ page }) => {
    test.setTimeout(180_000); // 10 routes + style guide in two themes
    for (const path of ["", "/sign-in", "/help", "/results", "/home", "/care-plan", "/family", "/privacy", "/notifications", "/teachback"]) {
      await page.goto(`/${locale}${path}`);
      await page.waitForLoadState("networkidle");
      await axe(page, `${locale}${path || "/"}`);
    }
    await page.goto(`/${locale}/design-system`);
    await page.getByTestId("ds-root").waitFor();
    await axe(page, `${locale}/design-system clinic`);
    await page.getByTestId("ds-theme").click();
    await axe(page, `${locale}/design-system ledger`);
  });

  test(`axe ${locale}: signed-in routes (vault, compatibility result, explainer)`, async ({ page }) => {
    test.setTimeout(180_000);
    await signIn(page, "V3A", locale);
    await axe(page, `${locale}/home V3A`);
    await page.goto(`/${locale}/results`);
    await page.getByTestId("vault-calls").waitFor();
    await axe(page, `${locale}/results V3A`);
    await runCompatibility(page, locale);
    await page.goto(`/${locale}/results/explainer`);
    await page.getByTestId("explainer").waitFor();
    await axe(page, `${locale}/explainer V3A`);
    for (const path of ["/care-plan", "/family", "/privacy", "/notifications", "/teachback"]) {
      await page.goto(`/${locale}${path}`);
      await page.waitForLoadState("networkidle");
      await axe(page, `${locale}${path} V3A after check`);
    }
    await signIn(page, "V1A", locale);
    await runCompatibility(page, locale);
    await axe(page, `${locale}/compatibility V1A result`);
  });
}
