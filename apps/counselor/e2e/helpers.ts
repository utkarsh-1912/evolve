import { expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

// Fixed clock so SLA timers and screenshots are deterministic (mock timestamps re-base to "now").
export const FIXED_NOW = new Date("2026-11-10T09:00:00Z");

const ROOT = path.join(__dirname, "..", "..", "..");
const panel = JSON.parse(fs.readFileSync(path.join(ROOT, "contracts", "gene_panel.json"), "utf-8")) as { genes: { symbol: string; hgnc_id: number }[] };
export const PANEL = panel.genes;

interface FixtureCase {
  row: { case_id: string; couple_id: string; trigger: string };
  view: { variants: ({ outside_consent: true } | { gene: string; hgnc_id: number })[] };
}
const fixtures = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "lib", "mock", "fixtures.json"), "utf-8")) as { cases: FixtureCase[] };
export const FIXTURE_CASES = fixtures.cases;

/** Genes the counselor may see for a couple's case = genes of its in-scope locked records. */
export function consentedGenes(couple: string, trigger: string): Set<string> {
  const c = FIXTURE_CASES.find((x) => x.row.couple_id === couple && x.row.trigger === trigger)!;
  return new Set(c.view.variants.filter((v): v is { gene: string; hgnc_id: number } => "gene" in v).map((v) => v.gene));
}

export async function signIn(page: Page, locale: "en" | "ar" = "en") {
  await page.clock.setFixedTime(FIXED_NOW);
  await page.goto(`/${locale}/sign-in`);
  await page.getByTestId("sign-in").click();
  await page.waitForURL(new RegExp(`/${locale}/queue`));
}

export async function goOnShift(page: Page) {
  await page.getByTestId("shift-switch").click();
  await expect(page.getByTestId("shift-status")).toHaveText(/On shift|.+/);
  await expect(page.getByTestId("shift-switch")).toHaveAttribute("data-state", "checked");
}

export async function signInOnShift(page: Page, locale: "en" | "ar" = "en") {
  await signIn(page, locale);
  await goOnShift(page);
  await expect(page.locator("[data-testid=case-table] tbody tr[tabindex]").first()).toBeVisible();
}

/** Open the case for a couple + trigger from the queue table. */
export async function openCase(page: Page, couple: string, trigger: string) {
  const c = FIXTURE_CASES.find((x) => x.row.couple_id === couple && x.row.trigger === trigger)!;
  await page.locator("[data-testid=case-table] tbody tr", { hasText: c.row.couple_id }).first().click();
  await expect(page.getByTestId("case-view")).toHaveAttribute("data-trigger", trigger);
  return c.row.case_id;
}

export async function openTab(page: Page, name: RegExp) {
  await page.getByRole("tab", { name }).click();
}

/** Nothing outside consent: no panel gene symbol other than the case's in-scope genes appears in the page. */
export async function expectNoOutsideGenes(page: Page, allowed: Set<string>, label: string) {
  const text = await page.locator("body").innerText();
  const leaked = PANEL.map((g) => g.symbol).filter((s) => !allowed.has(s) && new RegExp(`\b${s}\b`).test(text));
  const leakedIds = PANEL.filter((g) => !allowed.has(g.symbol)).filter((g) => text.includes(`HGNC:${g.hgnc_id}`)).map((g) => g.symbol);
  expect([...leaked, ...leakedIds], `${label}: genes outside consent rendered`).toEqual([]);
}
