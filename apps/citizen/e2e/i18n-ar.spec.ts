import { expect, test } from "@playwright/test";
import ar from "../messages/ar.json";
import { runCompatibility, signIn } from "./helpers";

// Arabic coverage (user-reported gap, 2026-11-17): every ar.json value is Arabic, and /ar shows Arabic locked numbers.
const ARABIC = /[؀-ۿ]/;
// Allowed non-Arabic tokens: brand, codes, acronyms, gene symbols, file paths, ICU placeholders.
const ALLOW = [/évolvé/g, /SIMULATED/g, /\bPGT-M\b/g, /\bSURE\b/g, /\bQR\b/g, /\bBMI\b/g, /\bThiqa\b/g, /\bLedger\b/g, /\bClinic\b/g, /@evolve\/ui/g, /docs\/[\w./-]+/g, /§\d+/g, /\bHGNC\b/g, /\{[^}]*\}/g];
const EXACT_OK = new Set(["English", "en"]); // the language switch names the OTHER language

function leaves(o: unknown, p = ""): [string, string][] {
  if (typeof o === "string") return [[p, o]];
  if (Array.isArray(o)) return o.flatMap((v, i) => leaves(v, `${p}[${i}]`));
  if (o && typeof o === "object") return Object.entries(o).flatMap(([k, v]) => leaves(v, p ? `${p}.${k}` : k));
  return [];
}

test("every ar.json value is Arabic (allowlisted brand/code tokens only) and carries no TODO marker", () => {
  const bad: string[] = [];
  for (const [key, value] of leaves(ar)) {
    if (key === "_todo") continue;
    expect(value, key).not.toMatch(/TODO\(ar\)/);
    if (EXACT_OK.has(value)) continue;
    let rest = value;
    for (const rx of ALLOW) rest = rest.replace(rx, "");
    const hasLatinWords = /[A-Za-z]{2,}/.test(rest);
    const onlyPlaceholders = value.replace(/\{[^}]*\}/g, "").trim() === "";
    if ((!ARABIC.test(value) && !onlyPlaceholders) || hasLatinWords) bad.push(`${key}: ${value}`);
  }
  expect(bad, bad.join("\n")).toEqual([]);
});

test("/ar V3 result shows the engine's Arabic locked numbers", async ({ page }) => {
  await signIn(page, "V3A", "ar");
  await runCompatibility(page, "ar");
  await page.goto("/ar/results/explainer");
  const big = page.getByTestId("locked-offspring_risk_one_in");
  await expect(big).toHaveText(/^1 من كل\s+321$/);
  await expect(big).toHaveAttribute("lang", "ar");
  await expect(page.getByTestId("locked-reference_unrelated_one_in")).toHaveText(/1 من كل\s+3,800/);
  await expect(page.getByTestId("locked-relative_to_unrelated_display")).toHaveText("حوالي 12 ضعفاً");
  // Provenance still shows raw values.
  await page.getByRole("button", { name: ar.ui.howCounted }).first().click();
  await expect(page.getByTestId("provenance")).toContainText("0.92");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
});
