import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

// Arabic completeness (DONE-AR-UI-EVAL): every ar.json value contains Arabic script, except allowlisted tokens;
// placeholders are identical to en.json; key sets match. Pure file check (no page needed).
const MSG = path.join(__dirname, "..", "messages");
const en = JSON.parse(fs.readFileSync(path.join(MSG, "en.json"), "utf-8"));
const ar = JSON.parse(fs.readFileSync(path.join(MSG, "ar.json"), "utf-8"));

/** Values that are tokens by design (see messages/AR-REVIEW.md). */
const ALLOW = new Set(["chrome.switchTo", "chrome.switchToLang", "chrome.logoAlt"]);
const ARABIC = /[؀-ۿ]/;

function flat(o: unknown, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  if (o && typeof o === "object") {
    for (const [k, v] of Object.entries(o as Record<string, unknown>)) Object.assign(out, flat(v, prefix ? `${prefix}.${k}` : k));
  } else out[prefix] = String(o);
  return out;
}
const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort();

test("ar.json: same keys as en.json, Arabic script in every value, identical placeholders", () => {
  const E = flat(en);
  const A = flat(ar);
  expect(Object.keys(A).sort()).toEqual(Object.keys(E).sort());
  const notArabic = Object.entries(A).filter(([k, v]) => !ALLOW.has(k) && !ARABIC.test(v)).map(([k]) => k);
  expect(notArabic, "values without Arabic script").toEqual([]);
  const mismatched = Object.keys(E).filter((k) => JSON.stringify(placeholders(E[k])) !== JSON.stringify(placeholders(A[k])));
  expect(mismatched, "placeholder mismatch").toEqual([]);
});

test("ar.json: SIMULATED stays a visible token; honesty texts present", () => {
  expect(ar.chrome.envLabel).toContain("SIMULATED");
  expect(ar.chrome.simulated).toContain("SIMULATED");
  expect(ar.ui.simulated).toContain("SIMULATED");
  expect(ar.simreal.simulated).toContain("SIMULATED");
  expect(ar.chrome.compliance).toContain("بغض النظر");
  expect(ar.chrome.compliance).toContain("ليست تشخيصاً");
  expect(ar.dim.notMet).toBe("لم يتحقق الهدف");
  expect(ar.gate.no).toBe("لا");
});

test("ar page renders Arabic copy, RTL, with the banner and the not-met verdicts", async ({ page }) => {
  await page.route("**/api/guardrail/events", (r) => r.abort("connectionrefused"));
  await page.goto("/ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("region", { name: "Environment" })).toContainText("SIMULATED");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(ar.header.title);
  await expect(page.getByTestId("verdict-comprehension")).toContainText(ar.dim.notMet);
  await expect(page.getByTestId("compliance-line")).toHaveText(ar.chrome.compliance);
});
