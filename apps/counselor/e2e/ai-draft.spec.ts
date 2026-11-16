import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { openCase, signInOnShift } from "./helpers";

// AI draft summary (api.md v1.3.0, DECISIONS #62), on the SIMULATED mock (offline stub).
// Mode hook: sessionStorage "evolve.counselor.mock.ai" = "on" | "blocked" | "unavailable" | "disabled" (unset = off; paused).
async function withMode(page: Page, mode: string) {
  await page.addInitScript((m) => window.sessionStorage.setItem("evolve.counselor.mock.ai", m), mode);
}

async function axeClean(page: Page, name: string) {
  const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  const bad = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  console.log(`axe ${name}: ${r.violations.length} total, ${bad.length} serious/critical`);
  expect(bad, name).toEqual([]);
}

test("draft: labelled, provider/model/time, locked figure verbatim, no partner IDs; copy to notes is not auto-saved", async ({ page }) => {
  await withMode(page, "on");
  await signInOnShift(page);
  await openCase(page, "V1", "a");
  await page.getByTestId("ai-draft-generate").click();
  await expect(page.getByTestId("ai-draft-label")).toHaveText("AI draft (offline stub): review before use · not shown to the patient");
  await expect(page.getByTestId("ai-draft-meta")).toContainText("Provider: offline stub · model offline-stub");
  await expect(page.getByTestId("ai-draft-meta").locator("time")).toHaveCount(1);
  const text = page.getByTestId("ai-draft-text");
  await expect(text).toContainText("1 in 4");
  await expect(text).not.toContainText(/V1A|V1B/);
  await axeClean(page, "ai draft shown");
  await page.getByTestId("ai-draft-copy").click();
  await expect(page.getByRole("tab", { name: /Notes/ })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("note-form").getByRole("textbox")).toHaveValue(/Case opened under trigger \(a\)/);
  await expect(page.getByTestId("note-list")).toHaveCount(0); // the counselor decides whether to save
});

test("blocked by the gate: violations shown, no draft text", async ({ page }) => {
  await withMode(page, "blocked");
  await signInOnShift(page);
  await openCase(page, "V3", "b");
  await page.getByTestId("ai-draft-generate").click();
  await expect(page.getByTestId("ai-draft-blocked")).toContainText("The safety gate held this draft");
  await expect(page.getByTestId("ai-draft-blocked")).toContainText("false_reassurance");
  await expect(page.getByTestId("ai-draft-text")).toHaveCount(0);
  await expect(page.getByTestId("ai-draft-copy")).toHaveCount(0);
  await expect(page.getByTestId("ai-draft-label")).toBeVisible();
  await axeClean(page, "ai draft blocked");
});

test("503: 'AI draft unavailable' and the rest of the case stays usable", async ({ page }) => {
  await withMode(page, "unavailable");
  await signInOnShift(page);
  await openCase(page, "V5", "c");
  await page.getByTestId("ai-draft-generate").click();
  await expect(page.getByTestId("ai-draft-unavailable")).toContainText("AI draft unavailable");
  await page.getByRole("tab", { name: /Variants/ }).click();
  await expect(page.getByTestId("variant-record")).toBeVisible();
  await expect(page.getByTestId("case-actions")).toBeVisible();
  await axeClean(page, "ai draft unavailable");
});

test("hidden when /api/config says ai_draft_enabled is false", async ({ page }) => {
  await withMode(page, "disabled");
  await signInOnShift(page);
  await openCase(page, "V1", "a");
  await expect(page.getByTestId("brief")).toBeVisible();
  await expect(page.getByTestId("ai-draft")).toHaveCount(0);
  await expect(page.getByTestId("ai-draft-generate")).toHaveCount(0);
});
