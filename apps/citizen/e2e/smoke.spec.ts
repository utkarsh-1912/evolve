import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { runCompatibility, signIn } from "./helpers";

// TASK-P2-UI smoke (R-UX-1), kept green through TASK-P3-UI-DS (selectors/flow updated, assertions unchanged). Runs on the SIMULATED mock adapter; fixtures come from services/risk_engine.

test("V4: shows Compatible and no gene text at all (APSI privacy)", async ({ page }) => {
  await signIn(page, "V4A");
  await runCompatibility(page);
  await expect(page.getByTestId("result")).toHaveAttribute("data-result", "compatible");
  await expect(page.getByTestId("result").getByText("Compatible", { exact: true }).first()).toBeVisible();
  const text = await page.locator("body").innerText();
  for (const gene of ["MEFV", "GJB2", "ABCA4"]) expect(text).not.toContain(gene);
  await expect(page.getByTestId("counselor-handoff")).toHaveCount(0);
  await expect(page.getByTestId("judicial")).toBeVisible();
  await expect(page.getByTestId("compliance-line")).toBeVisible();
});

test("V4B never sees partner A's genes, even in their own vault", async ({ page }) => {
  await signIn(page, "V4B");
  await page.goto("/en/results"); // P3 wave 2: My results moved from /vault to /results
  await expect(page.getByTestId("vault-calls")).toBeVisible();
  // P3 (A3): gene symbols sit behind "Technical details"; open every card before reading the page text.
  for (const btn of await page.getByRole("button", { name: "Technical details" }).all()) await btn.click();
  const text = await page.locator("body").innerText();
  expect(text).toContain("ABCA4");
  for (const gene of ["MEFV", "GJB2"]) expect(text).not.toContain(gene);
});

test("V1: shared gene, locked '1 in 4', counselor handoff, non-directive options", async ({ page }) => {
  await signIn(page, "V1A");
  await runCompatibility(page);
  await expect(page.getByTestId("result")).toHaveAttribute("data-result", "shared");
  await expect(page.getByTestId("shared-gene")).toHaveText("HBB");
  await expect(page.getByTestId("locked-offspring_risk_one_in")).toHaveText(/^1 in\s+4$/);
  await expect(page.getByTestId("counselor-handoff")).toBeVisible();
  await expect(page.getByTestId("option-cards").locator("li")).toHaveCount(3);
  await expect(page.getByTestId("judicial")).toBeVisible();
  await page.getByRole("button", { name: "How it was counted" }).first().click();
  await expect(page.getByTestId("provenance")).toContainText("1.1.0");
  // The digest literal was d6a70510ce0e until risk_engine changed its digest recipe (values unchanged, 2026-11);
  // assert against the record's own digest so the check stays "provenance shows this record's digest".
  const digest = (await page.getByTestId("locked-offspring_risk_one_in").getAttribute("data-locked-digest")) ?? "";
  expect(digest).toMatch(/^[0-9a-f]{64}$/);
  await expect(page.getByTestId("provenance")).toContainText(digest.slice(0, 12));
});

test("V1: revoking consent removes the shared result", async ({ page }) => {
  await signIn(page, "V1B");
  await runCompatibility(page);
  await page.getByTestId("revoke").click();
  await page.getByTestId("revoke-dialog-confirm").click(); // P3 (A6): withdrawal is confirmed in a dialog
  await expect(page.getByTestId("result")).toHaveCount(0);
  await expect(page.getByTestId("revoke-none")).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain("HBB");
});

test("V3: carrier sees residual risk '1 in 321' with detection bar and provenance", async ({ page }) => {
  await signIn(page, "V3A");
  await runCompatibility(page); // live parity: locked records exist only after the check (api.md v1.2.1)
  await page.goto("/en/results/explainer"); // P3 wave 2: explainer moved under My results
  await expect(page.getByTestId("locked-offspring_risk_one_in")).toHaveText(/^1 in\s+321$/);
  await expect(page.getByTestId("locked-reference_unrelated_one_in")).toHaveText(/1 in\s+3,800/);
  await expect(page.getByTestId("detection-bar")).toBeVisible();
  await page.getByRole("button", { name: "How it was counted" }).first().click();
  await expect(page.getByTestId("provenance")).toContainText("0.92");
  await expect(page.getByTestId("counselor-handoff")).toBeVisible();
});

test("V3B (screen-negative) sees no gene and no 'no risk' label", async ({ page }) => {
  await signIn(page, "V3B");
  await runCompatibility(page);
  const text = await page.locator("body").innerText();
  expect(text).not.toContain("SMN1");
  expect(text.toLowerCase()).not.toContain("no risk");
  await expect(page.getByText("This is not the same as zero risk.").first()).toBeVisible();
});

test("V5: compatible on APSI but routed to counselor review (no auto-clear)", async ({ page }) => {
  await signIn(page, "V5A");
  await runCompatibility(page);
  await expect(page.getByTestId("review-body")).toBeVisible();
  await expect(page.getByTestId("counselor-handoff")).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain("DONSON");
});

test("AR route renders dir=rtl", async ({ page }) => {
  await page.goto("/ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "ar");
  await expect(page.getByTestId("ar-pending")).toBeVisible();
});

test("landing: axe has no serious or critical violations", async ({ page }) => {
  await page.goto("/en");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  console.log(
    `axe: ${results.violations.length} violations total, ${bad.length} serious/critical`,
    bad.map((v) => `${v.id}: ${v.nodes.length}`),
  );
  expect(bad).toEqual([]);
});
