import { test, type Page } from "@playwright/test";
import { runCompatibility, signIn } from "./helpers";

// P3 wave-1 evidence: shell desktop + mobile, EN + AR, and the style guide (apps/citizen/screenshots/p3/).
const dir = "screenshots/p3"; // wave 1 set; wave 2 surfaces are captured by screenshots-cit.spec.ts
// Full-page capture renders sticky bars in flow so they do not float mid-image (capture artifact only).
const CAPTURE = { fullPage: true, animations: "disabled" as const, style: ".sticky{position:static !important}" };

async function shot(page: Page, name: string) {
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: `${dir}/${name}.png`, ...CAPTURE });
}

for (const [label, width, height] of [["desktop", 1280, 900], ["mobile", 360, 800]] as const) {
  for (const locale of ["en", "ar"] as const) {
    test(`shell ${label} ${locale}`, async ({ page }) => {
      test.setTimeout(120_000);
      await page.setViewportSize({ width, height });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto(`/${locale}`);
      await shot(page, `${label}-${locale}-01-landing`);
      await signIn(page, "V4B", locale);
      await page.goto(`/${locale}/results`);
      await page.getByTestId("vault-calls").waitFor();
      await shot(page, `${label}-${locale}-02-results-V4B`);
      await signIn(page, "V1A", locale);
      await runCompatibility(page, locale);
      await shot(page, `${label}-${locale}-03-compatibility-V1A`);
      await page.getByTestId("revoke").click();
      await page.getByTestId("revoke-dialog").waitFor();
      await page.screenshot({ path: `${dir}/${label}-${locale}-04-confirm-withdraw.png`, animations: "disabled" });
      await page.keyboard.press("Escape");
      await signIn(page, "V3A", locale);
      await runCompatibility(page, locale);
      await page.goto(`/${locale}/results/explainer`);
      await page.getByTestId("explainer").waitFor();
      await shot(page, `${label}-${locale}-05-explainer-V3A`);
      if (label === "mobile") {
        await page.getByRole("button", { name: /More|المزيد/ }).click();
        await page.screenshot({ path: `${dir}/${label}-${locale}-06-more-drawer.png`, animations: "disabled" });
      } else {
        await page.getByTestId("notification-bell").click();
        await page.screenshot({ path: `${dir}/${label}-${locale}-06-notifications.png`, animations: "disabled" });
      }
    });
  }
}

test("style guide captures", async ({ page }) => {
  test.setTimeout(120_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const locale of ["en", "ar"] as const) {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`/${locale}/design-system`);
    await page.getByTestId("ds-root").waitFor();
    await shot(page, `design-system-${locale}-clinic`);
    await page.getByTestId("ds-theme").click();
    await shot(page, `design-system-${locale}-ledger`);
  }
});
