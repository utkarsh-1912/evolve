import { expect, test } from "@playwright/test";
import { cohort, evidence, pct, stubApi } from "./helpers";

// R-EVAL-1 honesty checks: every headline metric matches the evidence pack, including the unmet ones.
test.beforeEach(async ({ page }) => {
  await stubApi(page);
  await page.goto("/en");
});

test("five dimensions show the pack's values, CIs and verdicts", async ({ page }) => {
  const d = evidence.dimensions;
  await expect(page.getByTestId("value-comprehension")).toContainText(pct(d.comprehension.first_attempt_pass.value));
  await expect(page.getByTestId("value-comprehension")).toContainText(pct(d.comprehension.first_attempt_pass.ci95[0]));
  await expect(page.getByTestId("value-sure")).toContainText(pct(d.informed_choice.sure_full.value));
  await expect(page.getByTestId("value-booked")).toContainText(pct(d.loop_velocity.booked_within_48h.value));
  await expect(page.getByTestId("value-calibration")).toContainText(String(d.calibration.arithmetic_mismatches));
  await expect(page.getByTestId("value-interception")).toContainText(pct(d.privacy.interception.value));
  for (const k of ["comprehension", "informed_choice", "loop_velocity", "calibration", "privacy"]) {
    await expect(page.getByTestId(`verdict-${k}`)).toHaveAttribute("data-meets", String(d[k].meets));
  }
  // Clean UI (docs/09 §10.4): exactly one SIMULATED badge on the surface; the global banner stays as text.
  await expect(page.locator("main [data-simulated]")).toHaveCount(1);
  await expect(page.getByRole("region", { name: "Environment" })).toContainText("Simulated environment");
  await expect(page.getByTestId("gcos")).toContainText("Not instrumented");
  await expect(page.getByTestId("redteam-leaks")).toContainText(String(d.privacy.redteam_leaks));
});

test("held-out sets are shown as measured, with the closed-template statement (REQUEST-DD-1)", async ({ page }) => {
  const g = evidence.g2;
  const sets = g.c_holdout_sets ?? [{ name: "holdout", catch: g.c_holdout.catch, fp: g.c_holdout.fp, meets_target: g.c_holdout.meets_target }];
  const rows = page.getByTestId("holdout-set");
  await expect(rows).toHaveCount(sets.length);
  for (let i = 0; i < sets.length; i++) {
    await expect(rows.nth(i).getByTestId("set-catch")).toHaveText(pct(sets[i].catch));
    await expect(rows.nth(i).getByTestId("set-fp")).toHaveText(pct(sets[i].fp));
    await expect(rows.nth(i)).toHaveAttribute("data-meets", String(sets[i].meets_target));
  }
  await expect(page.getByTestId("redteam-sets").locator("tbody tr")).toHaveCount(Object.keys(evidence.redteam).length);
  await expect(page.getByTestId("closed-templates")).toContainText("pre-approved templates");
  await expect(page.getByTestId("closed-templates")).toContainText("not a G2 blocker");
  if (evidence.gate3) {
    await expect(page.getByTestId("gate3").locator("tbody tr")).toHaveCount(evidence.gate3.suites.length);
    for (const nc of evidence.gate3.not_covered) await expect(page.getByTestId("gate3-not-covered")).toContainText(nc);
  }
});

test("never icon-only: safety texts, risk numbers and primary actions keep visible text (docs/09 §10)", async ({ page }) => {
  await expect(page.getByTestId("compliance-line")).toBeVisible();
  await expect(page.getByTestId("probe-submit")).toHaveText(/\S/);
  await expect(page.getByTestId("hist-bin").first().getByRole("button")).toContainText("How it was counted");
  await expect(page.getByTestId("hist-bin").first().locator("[data-locked-field]")).toHaveText(/1 in/);
  await expect(page.getByTestId("simreal-table")).toBeVisible();
  await expect(page.getByTestId("leak-honest")).toBeVisible();
});

test("rail: section links, keyboard toggle, tooltip on focus when collapsed", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.reload();
  const toggle = page.getByTestId("rail-toggle");
  await expect(page.getByTestId("sidebar")).toHaveAttribute("data-collapsed", "true");
  await page.getByTestId("rail-gate").focus();
  await expect(page.getByRole("tooltip")).toContainText("Safety gate");
  await page.getByTestId("rail-gate").press("Enter");
  await expect(page).toHaveURL(/#gate$/);
  await toggle.focus();
  await toggle.press("Enter");
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByTestId("rail-cohort")).toContainText("Cohort");
});

test("simulated-vs-real table, test matrix, leakage counter and cohort come from the pack", async ({ page }) => {
  await expect(page.getByTestId("simreal-table").locator("tbody tr")).toHaveCount(evidence.simulated_vs_real.length);
  await expect(page.getByTestId("test-matrix").locator("tbody tr")).toHaveCount(Object.keys(evidence.tests).length);
  const red = Object.values(evidence.tests as Record<string, { status: string }>).filter((s) => s.status === "red").length;
  await expect(page.getByTestId("test-matrix").locator('tr[data-status="red"]')).toHaveCount(red);
  await expect(page.getByTestId("leak-counter")).toHaveText(String(evidence.dimensions.privacy.live_leaks));
  await expect(page.getByTestId("leak-proof").locator("tbody tr")).toHaveCount(evidence.dimensions.privacy.table.length);
  await expect(page.getByTestId("cohort-grid").locator("circle")).toHaveCount(cohort.couples);
  await expect(page.getByTestId("hist-bin")).toHaveCount(cohort.histogram.length);
  const cal = evidence.calibration_detail;
  await expect(page.getByTestId("calibration-note")).toContainText("not possible with synthetic data");
  await expect(page.getByTestId("calibration-note")).toContainText(`${cal.mismatches} mismatches over ${cal.records} records`);
  // every histogram label is a LockedNumber bound to the engine record's digest
  const digests = await page
    .getByTestId("hist-bin")
    .locator("[data-locked-digest]")
    .evaluateAll((els) => els.map((e) => e.getAttribute("data-locked-digest")));
  expect(digests).toEqual(cohort.histogram.map((b: { record: { digest: string } }) => b.record.digest));
});

test("no marriage-outcome metric; compliance line present", async ({ page }) => {
  const text = (await page.locator("body").innerText()).toLowerCase();
  expect(text).not.toMatch(/cancel+ed marriage|marriages? cancel|marriage[- ]outcome (rate|metric|count)|divorce/);
  await expect(page.getByTestId("compliance-line")).toContainText("not a diagnosis");
  await expect(page.getByTestId("compliance-line")).toContainText("issued regardless");
});

test("feed shows an honest paused state when the backend is down", async ({ page }) => {
  await page.unroute("**/api/guardrail/events");
  await stubApi(page, { down: true });
  await page.reload();
  await expect(page.getByTestId("feed-offline")).toBeVisible({ timeout: 15_000 });
});
