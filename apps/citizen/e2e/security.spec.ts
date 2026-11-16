import { expect, test } from "@playwright/test";
import { runCompatibility, signIn } from "./helpers";

// docs/09 §7 + DECISIONS #44 Q3: per-request CSP nonce, no inline-script allowance, zero CSP violations in a journey.
test("CSP: nonce per request, no 'unsafe-inline' scripts, no violations during a V1 journey", async ({ page }) => {
  const violations: string[] = [];
  page.on("console", (m) => {
    if (/Content Security Policy|Refused to (execute|load|apply)/i.test(m.text())) violations.push(m.text());
  });
  const r1 = await page.goto("/en");
  const r2 = await page.request.get("/en");
  const csp1 = r1?.headers()["content-security-policy"] ?? "";
  const csp2 = r2.headers()["content-security-policy"] ?? "";
  const script = csp1.split(";").find((d) => d.trim().startsWith("script-src")) ?? "";
  expect(script).toMatch(/'nonce-[A-Za-z0-9+/=]+'/);
  expect(script).not.toContain("'unsafe-inline'");
  expect(csp1).toContain("frame-ancestors 'none'");
  expect(csp1.match(/nonce-([^']+)/)?.[1]).not.toEqual(csp2.match(/nonce-([^']+)/)?.[1]);
  expect(r1?.headers()["x-frame-options"]).toBe("DENY");
  expect(r1?.headers()["referrer-policy"]).toBe("no-referrer");
  await signIn(page, "V1A");
  await runCompatibility(page);
  await page.goto("/en/care-plan");
  await page.getByTestId("care-options").waitFor();
  expect(violations, violations.join("\n")).toEqual([]);
});
