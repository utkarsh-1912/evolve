import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { runCompatibility, signIn } from "./helpers";

// TASK-P3-UI-CIT acceptance: V1–V5 journeys, EN + AR, through all citizen surfaces.
// Runs unchanged against the SIMULATED mock (playwright.config.ts) and the live backend (playwright.live.config.ts).
const LIVE = !!process.env.EVOLVE_LIVE;
const API = process.env.EVOLVE_API ?? "http://localhost:8000";

test.beforeEach(async ({ request }) => {
  if (LIVE) expect((await request.post(`${API}/api/demo/reset`)).ok()).toBeTruthy();
});

type Expect = {
  partner: string;
  other: string;
  headline: "shared" | "compatible" | "review";
  handoff: boolean;
  explainer?: string; // locked display string the carrier must see on the explainer
  neverSee: string[]; // the other partner's genes: must never appear anywhere for this partner (P-06)
  family: boolean;
};
const JOURNEYS: Expect[] = [
  { partner: "V1A", other: "V1B", headline: "shared", handoff: true, neverSee: [], family: true },
  { partner: "V2A", other: "V2B", headline: "compatible", handoff: true, explainer: "1 in 426", neverSee: [], family: true },
  { partner: "V3B", other: "V3A", headline: "compatible", handoff: false, neverSee: ["SMN1"], family: false },
  { partner: "V4A", other: "V4B", headline: "compatible", handoff: false, neverSee: ["ABCA4"], family: true },
  { partner: "V5B", other: "V5A", headline: "review", handoff: true, neverSee: [], family: false },
];
const TEACHBACK_CORRECT = [false, true, true, true];
const BACKEND_JUDICIAL = "sent to the Abu Dhabi Judicial Department";

async function bodyText(page: Page) {
  return page.locator("main").innerText();
}

for (const locale of ["en", "ar"] as const) {
  for (const j of JOURNEYS) {
    test(`${locale} ${j.partner}: home → results → compatibility → explainer → teach-back → care plan + SURE → family → privacy → notifications`, async ({ page }) => {
      test.setTimeout(120_000);
      const seen: string[] = [];
      const collect = async () => seen.push(await bodyText(page));

      // Home
      await signIn(page, j.partner, locale);
      await expect(page.getByTestId("next-step")).toBeVisible();
      await expect(page.getByTestId("next-step-cta")).toHaveAttribute("href", `/${locale}/compatibility`);
      await collect();

      // My results (open every finding's technical details before reading text)
      await page.goto(`/${locale}/results`);
      await expect(page.getByTestId("vault-calls").or(page.getByTestId("vault-none"))).toBeVisible();
      for (const btn of await page.getByRole("button", { name: "Technical details" }).all()) await btn.click();
      await collect();

      // Compatibility
      await runCompatibility(page, locale);
      const result = page.getByTestId("result");
      if (j.headline === "shared") {
        await expect(result).toHaveAttribute("data-result", "shared");
        await expect(page.getByTestId("locked-offspring_risk_one_in")).toHaveText(/^1 in\s+4$/);
      } else if (j.headline === "review") {
        await expect(result).toHaveAttribute("data-result", "review");
        await expect(result.getByText("Compatible", { exact: true })).toHaveCount(0); // api.md v1.2.1
      } else {
        await expect(result).toHaveAttribute("data-result", "compatible");
      }
      await expect(page.getByTestId("counselor-handoff")).toHaveCount(j.handoff ? 1 : 0);
      await expect(page.getByTestId("judicial")).toBeVisible();
      await expect(page.getByTestId("counselor-rail")).toBeVisible();
      await expect(page.getByTestId("message-thread")).toBeVisible();
      // Certificate sentence once per page: the callout shows it; message bodies do not repeat the backend sentence.
      expect(await bodyText(page)).not.toContain(BACKEND_JUDICIAL);
      await collect();

      // Explainer (carrier only)
      await page.goto(`/${locale}/results/explainer`);
      if (j.explainer) {
        await expect(page.getByTestId("locked-offspring_risk_one_in")).toHaveText(new RegExp(`^${j.explainer.replace(/ /g, "\\s+")}$`));
        await expect(page.getByTestId("detection-bar")).toBeVisible();
      } else {
        await expect(page.getByTestId("results-none")).toBeVisible();
      }
      await collect();

      // Teach-back: one statement per screen, then kind feedback
      await page.goto(`/${locale}/teachback`);
      for (let i = 0; i < TEACHBACK_CORRECT.length; i++) {
        await expect(page.getByTestId("teachback-statement")).toBeVisible();
        await page.getByRole("radio", { name: TEACHBACK_CORRECT[i] ? "True" : "False" }).click();
        await page.getByTestId(i === TEACHBACK_CORRECT.length - 1 ? "teachback-submit" : "teachback-next").click();
      }
      await expect(page.getByTestId("teachback-done")).toHaveAttribute("data-passed", "true");
      expect((await bodyText(page)).toLowerCase()).not.toMatch(/\bfail/);

      // Care plan: timeline, equal-weight options, eligibility, SURE
      await page.goto(`/${locale}/care-plan`);
      await expect(page.getByTestId("care-timeline")).toBeVisible();
      await expect(page.getByTestId("care-options").locator("li").first()).toBeVisible();
      await expect(page.getByTestId("eligibility")).toBeVisible();
      expect((await bodyText(page)).toLowerCase()).not.toMatch(/recommended option|donor/);
      for (const name of ["Yes", "Yes", "Yes", "Yes"].map((x, k) => ({ x, k }))) {
        await page.locator(`input[name="sure-${name.k}"]`).first().check({ force: true });
      }
      await page.getByTestId("sure-submit").click();
      await expect(page.getByTestId("sure-done")).toBeVisible();
      await collect();

      // Family token (own P/LP only)
      await page.goto(`/${locale}/family`);
      if (j.family) {
        await page.getByTestId("family-create").click();
        await expect(page.getByTestId("qr-code")).toBeVisible();
      } else {
        await expect(page.getByTestId("family-none")).toBeVisible();
      }
      await collect();

      // Privacy: consent rows + own access history
      await page.goto(`/${locale}/privacy`);
      await expect(page.getByTestId("consent-table").locator("tbody tr").first()).toBeVisible();
      await expect(page.getByTestId("audit-table").locator("tbody tr").first()).toBeVisible();
      await collect();

      // Notifications
      await page.goto(`/${locale}/notifications`);
      await expect(page.getByTestId("notification-list")).toBeVisible();
      await collect();

      // P-06 across every surface this partner visited
      for (const gene of j.neverSee) for (const text of seen) expect(text).not.toContain(gene);
    });
  }
}

test("family QR decodes to the exact token payload (OpenCV)", async ({ page }) => {
  await signIn(page, "V1A");
  await runCompatibility(page);
  await page.goto("/en/family");
  await page.getByTestId("family-create").click();
  const payload = (await page.getByTestId("family-payload").innerText()).trim();
  const dir = path.join("test-results", "qr");
  mkdirSync(dir, { recursive: true });
  const png = path.join(dir, "family-qr.png");
  const txt = path.join(dir, "family-qr.txt");
  await page.getByTestId("qr-code").screenshot({ path: png });
  writeFileSync(txt, payload, "utf-8");
  const out = execFileSync("python", ["scripts/verify_qr.py", png, txt], { encoding: "utf-8" });
  expect(out).toContain("OK");
});
