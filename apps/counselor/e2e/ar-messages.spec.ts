import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { openCase, signInOnShift } from "./helpers";

// Real Arabic for the counselor app (supersedes DECISIONS #50(3)). Every AR value contains Arabic script, except the
// allowlisted brand/instrument/locale tokens; key sets and {placeholders} match EN exactly.
const MSG = path.join(__dirname, "..", "messages");
const en = JSON.parse(fs.readFileSync(path.join(MSG, "en.json"), "utf-8"));
const ar = JSON.parse(fs.readFileSync(path.join(MSG, "ar.json"), "utf-8"));
const ALLOW = new Set(["English", "en", "SURE", "Sarvam"]);
const ARABIC = /[؀-ۿ]/;
const slots = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

function flatten(o: Record<string, unknown>, p = ""): Record<string, string> {
  return Object.fromEntries(
    Object.entries(o).flatMap(([k, v]) => (v && typeof v === "object" ? Object.entries(flatten(v as Record<string, unknown>, `${p}${k}.`)) : [[`${p}${k}`, String(v)]])),
  );
}
const EN = flatten(en);
const AR = flatten(ar);

test("ar.json: same keys as en.json", () => {
  expect(Object.keys(AR).sort()).toEqual(Object.keys(EN).sort());
});

test("ar.json: every value contains Arabic script (allowlist: brand/code tokens)", () => {
  const bad = Object.entries(AR).filter(([, v]) => !ARABIC.test(v) && !ALLOW.has(v)).map(([k, v]) => `${k}=${v}`);
  expect(bad).toEqual([]);
});

test("ar.json: placeholders identical to EN; no Arabic-Indic digits", () => {
  const mismatch = Object.keys(EN).filter((k) => JSON.stringify(slots(EN[k])) !== JSON.stringify(slots(AR[k] ?? "")));
  expect(mismatch).toEqual([]);
  expect(Object.entries(AR).filter(([, v]) => /[٠-٩]/.test(v)).map(([k]) => k)).toEqual([]);
});

test("AR UI: shell and case view in Arabic; AI draft labelled in Arabic, draft text stays English", async ({ page }) => {
  await page.addInitScript(() => window.sessionStorage.setItem("evolve.counselor.mock.ai", "on"));
  await signInOnShift(page, "ar");
  await expect(page.getByTestId("compliance-line")).toContainText("ليست تشخيصاً");
  await expect(page.getByTestId("shift-text")).toHaveText("في المناوبة");
  await openCase(page, "V1", "a");
  await expect(page.getByRole("tab", { name: "شجرة العائلة" })).toBeVisible();
  await page.getByTestId("ai-draft-generate").click();
  await expect(page.getByTestId("ai-draft-label")).toHaveText("مسودة بالذكاء الاصطناعي (نموذج بديل دون اتصال): تُراجَع قبل الاستخدام · لا تُعرض على المريض");
  await expect(page.getByTestId("ai-draft-text")).toContainText("Case opened under trigger (a).");
  await expect(page.getByTestId("ai-draft-text")).toHaveAttribute("lang", "en");
});
