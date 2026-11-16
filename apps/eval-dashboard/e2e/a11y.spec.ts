import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { stubApi, stubProbe } from "./helpers";

// docs/09 §7: axe 0 serious/critical, EN + AR, including the probe "held" state and expanded disclosures.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function axe(page: Page, name: string) {
  const r = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  const bad = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  console.log(`axe ${name}: ${r.violations.length} total, ${bad.length} serious/critical`, bad.map((v) => `${v.id}(${v.nodes.length}) ${v.nodes[0]?.target}`));
  expect(bad, name).toEqual([]);
}

for (const locale of ["en", "ar"] as const) {
  test(`axe ${locale}: dashboard default, probe held, disclosures open`, async ({ page }) => {
    await stubApi(page);
    await stubProbe(page);
    await page.goto(`/${locale}`);
    await page.getByTestId("feed-event").first().waitFor();
    await axe(page, `${locale} default`);
    await page.getByTestId("probe-draft").fill("fixture draft");
    await page.getByTestId("probe-submit").click();
    await page.getByTestId("probe-held").waitFor();
    await page.getByTestId("assumptions").locator("summary").click();
    await page.getByTestId("hist-bin").first().getByRole("button").click();
    await axe(page, `${locale} probe held + provenance + assumptions`);
    await page.getByTestId("rail-probe").focus();
    await page.getByRole("tooltip").waitFor();
    await page.getByTestId("chip-pack").focus();
    await axe(page, `${locale} rail tooltip + chip tooltip`);
  });
}
