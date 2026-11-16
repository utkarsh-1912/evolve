import { expect, test } from "@playwright/test";
import { consentedGenes, expectNoOutsideGenes, goOnShift, openCase, openTab, signIn, signInOnShift } from "./helpers";

// TASK-P3-UI-CNS acceptance (R-UX-2) on the SIMULATED mock adapter (fixtures recorded from the real backend).

test("off shift: permission-denied state, no case data requested or rendered", async ({ page }) => {
  await signIn(page);
  await expect(page.getByTestId("off-shift")).toBeVisible();
  await expect(page.getByTestId("shift-status")).toHaveText("Off shift");
  await expect(page.getByTestId("case-table")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText("case-");
  // Direct link to a case while off shift: still the permission state.
  await page.goto("/en/cases/case-anything");
  await expect(page.getByTestId("off-shift")).toBeVisible();
  await expect(page.getByTestId("case-view")).toHaveCount(0);
  // Going on shift from the permission state shows data; going off again hides it.
  await page.getByTestId("go-on-shift").click();
  await expect(page.getByTestId("case-not-found")).toBeVisible();
  await page.goto("/en/queue");
  await expect(page.locator("[data-testid=case-table] tbody tr[tabindex]")).toHaveCount(5);
  await page.getByTestId("shift-switch").click();
  await expect(page.getByTestId("off-shift")).toBeVisible();
  await expect(page.getByTestId("case-table")).toHaveCount(0);
});

test("queue: triggers a-d, SLA vs 48 h, filters, saved views, j/k/Enter", async ({ page }) => {
  await signInOnShift(page);
  const rows = page.locator("[data-testid=case-table] tbody tr[tabindex]");
  await expect(rows).toHaveCount(5);
  for (const tr of ["(a)", "(b)", "(c)", "(d)"]) await expect(page.getByTestId("case-table")).toContainText(tr);
  await expect(page.getByTestId("sla-timer").first()).toContainText(/h \d+ min left/);
  await expect(page.getByTestId("access-basis")).toContainText("on shift");

  // Filter by trigger (d).
  await page.getByTestId("filters").getByRole("combobox").first().click();
  await page.getByRole("option", { name: /\(d\)/ }).click();
  await expect(rows).toHaveCount(1);
  // Save it as a view, switch away, come back.
  await page.getByTestId("save-view").click();
  await page.getByRole("dialog").getByRole("textbox").fill("My d cases");
  await page.getByRole("dialog").getByRole("button", { name: "Save" }).click();
  await page.getByRole("button", { name: "All open", exact: true }).click();
  await expect(rows).toHaveCount(5);
  await page.getByRole("button", { name: "My d cases", exact: true }).click();
  await expect(rows).toHaveCount(1);
  await page.getByRole("button", { name: "Urgent", exact: true }).click();
  await expect(rows).toHaveCount(1);
  await page.getByRole("button", { name: "All open", exact: true }).click();

  // Keyboard: j, j, k then Enter opens the focused (second) row.
  await page.locator("h1").first().click();
  await page.keyboard.press("j");
  await expect(rows.nth(0)).toBeFocused();
  await page.keyboard.press("j");
  await page.keyboard.press("j");
  await page.keyboard.press("k");
  await expect(rows.nth(1)).toBeFocused();
  const id = (await rows.nth(1).getByTestId("case-id").innerText()).trim();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("case-view")).toHaveAttribute("data-case", id);
});

test("density toggle and global case-ID search (case ID only)", async ({ page }) => {
  await signInOnShift(page);
  const toggle = page.getByTestId("density-toggle");
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  const firstId = (await page.locator("[data-testid=case-table] [data-testid=case-id]").first().innerText()).trim();
  const search = page.getByTestId("case-search").locator("input");
  await search.fill("HBB");
  await search.press("Enter");
  await expect(page.getByTestId("case-search")).toContainText("No case matches that ID.");
  await search.fill(firstId);
  await search.press("Enter");
  await expect(page.getByTestId("case-view")).toHaveAttribute("data-case", firstId);
});

test("V1 trigger (a): brief, pedigree with consanguinity loop and F as context, variants in scope", async ({ page }) => {
  await signInOnShift(page);
  await openCase(page, "V1", "a");
  const allowed = consentedGenes("V1", "a");
  await expect(page.getByTestId("access-basis")).toContainText("couple consent");
  await expect(page.getByTestId("access-basis")).toContainText("on shift");
  await expect(page.getByTestId("brief")).toContainText("Trigger (a)");
  await expect(page.getByTestId("brief-variant")).toContainText("HBB");
  await expectNoOutsideGenes(page, allowed, "V1 brief");

  await openTab(page, /Pedigree/);
  const graph = page.getByTestId("pedigree-graph");
  await expect(graph.locator("svg[role=img]")).toBeVisible();
  await expect(graph.locator("[data-union=consanguineous]")).toHaveCount(1);
  expect(await graph.locator("[data-loop-edge]").count()).toBeGreaterThan(0);
  await expect(graph.getByTestId("pedigree-loop-legend")).toBeVisible();
  await expect(graph.locator("[data-pedigree-node]")).toHaveCount(8);
  await expect(page.getByTestId("pedigree-context").getByTestId("locked-F")).toHaveText("0.0625");
  await expect(page.getByTestId("pedigree-context")).toContainText("never used on its own");

  await openTab(page, /Variants/);
  const rec = page.getByTestId("variant-record");
  await expect(rec).toHaveCount(1);
  await expect(rec.getByTestId("locked-offspring_risk_one_in")).toContainText("1 in");
  await expect(rec.getByTestId("locked-offspring_risk_one_in")).toContainText("4");
  await expectNoOutsideGenes(page, allowed, "V1 variants");
});

test("V3 trigger (b): locked residual risk + detection rate; completing the confirmatory task advances the loop", async ({ page }) => {
  await signInOnShift(page);
  await openCase(page, "V3", "b");
  const allowed = consentedGenes("V3", "b");
  await openTab(page, /Variants/);
  const rec = page.getByTestId("variant-record");
  await expect(rec).toHaveAttribute("data-gene", "SMN1");
  await expect(rec.getByTestId("locked-offspring_risk_one_in")).toHaveText(/1 in\s*321/);
  await expect(rec.getByTestId("locked-detection_rate")).toHaveText("92%");
  await expect(rec.getByTestId("locked-relative_to_unrelated_display")).toHaveText("about 12x");
  await expectNoOutsideGenes(page, allowed, "V3 variants");

  await openTab(page, /Tasks/);
  const task = page.locator("[data-testid=task-table] tbody tr", { hasText: "Confirmatory test" });
  await expect(task).toContainText("V3A");
  await expect(task).toContainText("Requested");
  await task.getByTestId("task-complete").click();
  await expect(task).toContainText("Completed");
  await openTab(page, /Timeline/);
  await expect(page.getByTestId("timeline")).toContainText("Care loop: Confirmatory test done");
});

test("V5 trigger (c): shared VUS in ROH is counselor-only with no number; red-flag history", async ({ page }) => {
  await signInOnShift(page);
  await openCase(page, "V5", "c");
  const allowed = consentedGenes("V5", "c");
  await expect(page.getByTestId("brief")).toContainText("Trigger (c)");
  await expect(page.getByTestId("brief")).toContainText("Double first cousins");
  await expect(page.getByTestId("brief")).toContainText("Unexplained neonatal or infant death");
  await openTab(page, /Variants/);
  const rec = page.getByTestId("variant-record");
  await expect(rec).toContainText("Counselor only");
  await expect(rec).toContainText("Needs counselor, no number");
  await expect(rec.locator("[data-locked-missing=true]")).toBeVisible();
  await openTab(page, /Pedigree/);
  await expect(page.locator("[data-pedigree-node=V5-REL0][data-affected=true]")).toHaveCount(1);
  await expect(page.getByTestId("pedigree-context").getByTestId("locked-F")).toHaveText("0.125");
  await expectNoOutsideGenes(page, allowed, "V5");
});

test("teach-back not passed, trigger (d): outside-consent placeholders say nothing", async ({ page }) => {
  await signInOnShift(page);
  await openCase(page, "V4", "d");
  const allowed = consentedGenes("V4", "d");
  await expect(page.getByTestId("comprehension")).toContainText("Not passed (score 1)");
  const outside = page.getByTestId("outside-consent");
  await expect(outside.first()).toHaveText("Outside consented scope");
  await expectNoOutsideGenes(page, allowed, "V4 brief");
  await openTab(page, /Variants/);
  await expect(page.getByTestId("outside-consent")).toHaveCount(1);
  await expect(page.getByTestId("outside-consent")).toHaveText("Outside consented scope");
  await expect(page.getByTestId("variant-record")).toHaveCount(2);
  for (const tab of [/Brief/, /Pedigree/, /Variants/, /Tasks/, /Notes/, /Timeline/]) {
    await openTab(page, tab);
    await expectNoOutsideGenes(page, allowed, `V4 ${tab}`);
  }
});

test("actions: advance loop, SURE, schedule (SIMULATED), note, human closure with confirm", async ({ page }) => {
  await signInOnShift(page);
  const caseId = await openCase(page, "V1", "a");

  await page.getByTestId("action-advance").click();
  await page.getByRole("dialog").getByRole("combobox").click();
  await page.getByRole("option", { name: "Understanding confirmed" }).click();
  await page.getByTestId("advance-confirm").click();
  await openTab(page, /Timeline/);
  await expect(page.getByTestId("timeline")).toContainText("Care loop: Understanding confirmed");

  await page.getByTestId("action-sure").click();
  await expect(page.getByTestId("sure-recorded")).toContainText("Not taken yet");
  await page.getByTestId("sure-send").click();
  await page.getByTestId("action-schedule").click();
  await expect(page.getByTestId("schedule-dialog")).toContainText("simulated");
  await page.getByTestId("schedule-dialog-confirm").click();
  await openTab(page, /Tasks/);
  await expect(page.getByTestId("task-table")).toContainText("SURE check");
  await expect(page.getByTestId("task-table")).toContainText("Counseling appointment");

  await openTab(page, /Notes/);
  await expect(page.getByTestId("notes")).toContainText("never sent to patients");
  await page.getByTestId("note-form").getByRole("textbox").fill("Discussed options; couple will return with questions.");
  await page.getByTestId("note-add").click();
  await expect(page.getByTestId("note-list")).toContainText("Discussed options");

  // Human closure: summary, then explicit confirmation with consequences; cancel first, then confirm.
  await page.getByTestId("action-closure").click();
  await page.getByTestId("closure-next").click();
  await expect(page.getByRole("dialog")).toContainText("Write a closure summary first.");
  await page.getByTestId("closure-summary").fill("Counseling completed; follow-up offered.");
  await page.getByTestId("closure-next").click();
  const confirm = page.getByTestId("closure-confirm");
  await expect(confirm).toContainText("Only a counselor can do this.");
  await confirm.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByTestId("case-closed")).toHaveCount(0);
  await page.getByTestId("action-closure").click();
  await page.getByTestId("closure-next").click();
  await page.getByTestId("closure-confirm-confirm").click();
  await expect(page.getByTestId("case-closed")).toBeVisible();
  await expect(page.getByTestId("closed-notice")).toBeVisible();
  await expect(page.getByTestId("case-actions")).toHaveCount(0);
  await openTab(page, /Timeline/);
  await expect(page.getByTestId("timeline")).toContainText("Care loop: Human closure");
  await expect(page.getByTestId("timeline")).toContainText("Human closure documented");
  // States jumped over are shown as skipped, never as done.
  await expect(page.getByTestId("timeline").getByTestId("timeline-skipped")).toHaveCount(3);

  // The closed case leaves the open queue.
  await page.goto("/en/queue");
  await expect(page.locator("[data-testid=case-table] tbody tr[tabindex]")).toHaveCount(4);
  await expect(page.getByTestId("case-table")).not.toContainText(caseId);
});

test("shift off while viewing a case hides it", async ({ page }) => {
  await signInOnShift(page);
  await openCase(page, "V3", "b");
  await page.getByTestId("shift-switch").click();
  await expect(page.getByTestId("off-shift")).toBeVisible();
  await expect(page.getByTestId("case-view")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText("SMN1");
  await goOnShift(page);
  await expect(page.getByTestId("case-view")).toBeVisible();
});

test("AR: RTL shell, queue and case view render", async ({ page }) => {
  await signInOnShift(page, "ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "ledger");
  await openCase(page, "V1", "a");
  await openTab(page, /Pedigree/);
  await expect(page.getByTestId("pedigree-graph").locator("svg[role=img]")).toBeVisible();
  await expect(page.getByTestId("access-basis")).toBeVisible();
});

test("split view: resizer is keyboard operable", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await signInOnShift(page);
  await openCase(page, "V1", "a");
  const sep = page.getByTestId("split-resizer");
  const before = Number(await sep.getAttribute("aria-valuenow"));
  await sep.focus();
  await page.keyboard.press("ArrowRight");
  await expect(sep).toHaveAttribute("aria-valuenow", String(before + 16));
  await expect(page.getByTestId("case-list")).toBeVisible();
});
