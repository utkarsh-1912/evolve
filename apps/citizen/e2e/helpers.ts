import { expect, type Page } from "@playwright/test";

export async function signIn(page: Page, pid: string, locale = "en") {
  await page.goto(`/${locale}/sign-in`);
  await page.getByTestId(`signin-${pid}`).click();
  await expect(page).toHaveURL(new RegExp(`/${locale}/home$`)); // P3 wave 2: sign-in lands on Home
}

export async function runCompatibility(page: Page, locale = "en") {
  await page.goto(`/${locale}/compatibility`);
  const toggle = page.getByTestId("consent-toggle");
  await expect(toggle).toBeEnabled();
  // Consent may already exist in this tab (e.g. created by an earlier simulated-partner step); never toggle it off.
  if ((await toggle.getAttribute("aria-checked")) !== "true") await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("revoke")).toBeVisible();
  // The partner may already have consented earlier in this tab (sessionStorage); only simulate when needed.
  const simulate = page.getByTestId("simulate-partner");
  if (await simulate.count()) {
    await simulate.click();
    await expect(simulate).toHaveCount(0);
  }
  await page.getByTestId("run-check").click();
  await expect(page.getByTestId("result")).toBeVisible({ timeout: 10_000 });
}
