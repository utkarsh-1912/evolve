import { test } from "@playwright/test";
import { runCompatibility, signIn } from "./helpers";

// Captures the demo-critical screens (docs/03 §10) into apps/citizen/screenshots/ (re-rendered in the P3 shell). Mock adapter, SIMULATED.
const dir = "screenshots";
// Full-page capture: render the sticky footer chip in flow so it does not float mid-image.
const CAPTURE_CSS = ".sticky{position:static !important}";
test.use({ viewport: { width: 1280, height: 900 } });

test("capture screens", async ({ page }) => {
  test.setTimeout(120_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/en");
  await page.screenshot({ path: `${dir}/01-landing.png`, fullPage: true, style: CAPTURE_CSS });
  await page.goto("/en/sign-in");
  await page.getByTestId("signin-V1A").waitFor();
  await page.screenshot({ path: `${dir}/02-sign-in.png`, fullPage: true, style: CAPTURE_CSS });

  await signIn(page, "V4A");
  await page.goto("/en/results");
  await page.getByTestId("vault-calls").waitFor();
  await page.screenshot({ path: `${dir}/03-vault-V4A.png`, fullPage: true, style: CAPTURE_CSS });
  await runCompatibility(page);
  await page.screenshot({ path: `${dir}/04-compatibility-V4-compatible.png`, fullPage: true, style: CAPTURE_CSS });

  await signIn(page, "V1A");
  await runCompatibility(page);
  await page.getByRole("button", { name: "How it was counted" }).first().click();
  await page.screenshot({ path: `${dir}/05-result-V1-counselor-handoff.png`, fullPage: true, style: CAPTURE_CSS });

  await signIn(page, "V3A");
  await runCompatibility(page);
  await page.goto("/en/results/explainer");
  await page.getByRole("button", { name: "How it was counted" }).first().click();
  await page.screenshot({ path: `${dir}/06-residual-risk-V3.png`, fullPage: true, style: CAPTURE_CSS });

  await page.goto("/en/help");
  await page.screenshot({ path: `${dir}/07-people-calculator-assistant.png`, fullPage: true, style: CAPTURE_CSS });

  await page.goto("/ar");
  await page.screenshot({ path: `${dir}/08-landing-ar-rtl.png`, fullPage: true, style: CAPTURE_CSS });

  await page.setViewportSize({ width: 360, height: 800 });
  await signIn(page, "V1B");
  await runCompatibility(page);
  await page.screenshot({ path: `${dir}/09-result-V1-360px.png`, fullPage: true, style: CAPTURE_CSS });
});
