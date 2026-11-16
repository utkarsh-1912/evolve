import { mkdirSync, writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { runCompatibility, signIn } from "./helpers";

// docs/09 §7 budgets, measured in the browser against `next start` (gzip on):
// - JS per route: sum of encodedBodySize (compressed transfer) of every script resource on a cold load ≤ 180 kB.
// - LCP proxy on Home and Results: mobile viewport + 4× CPU throttle. This is NOT Lighthouse (not allow-listed;
//   see handoffs/QUESTION-UI-CIT-1.md); reported as a proxy only.
const BUDGET = 180 * 1024;
const ROUTES = ["", "/sign-in", "/home", "/results", "/results/explainer", "/compatibility", "/teachback", "/care-plan", "/family", "/privacy", "/notifications", "/help", "/design-system"];

test("JS budget per route ≤ 180 kB gz + LCP proxy", async ({ browser }) => {
  test.setTimeout(240_000);
  const rows: { route: string; js_gz_kb: number }[] = [];
  const lcp: Record<string, number> = {};
  // Signed-in session for shelled routes, then measure each route in a fresh, cache-less page of the same context.
  const ctx = await browser.newContext({ viewport: { width: 412, height: 915 } });
  const setup = await ctx.newPage();
  await signIn(setup, "V3A");
  await runCompatibility(setup);
  const storage = await setup.evaluate(() => JSON.stringify(sessionStorage));
  await setup.close();
  for (const r of ROUTES) {
    const page = await ctx.newPage();
    await page.addInitScript((s) => {
      const o = JSON.parse(s) as Record<string, string>;
      for (const [k, v] of Object.entries(o)) sessionStorage.setItem(k, v);
    }, storage);
    const cdp = await ctx.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    if (r === "/home" || r === "/results") await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    await page.goto(`/en${r}`, { waitUntil: "networkidle" });
    const bytes = await page.evaluate(() =>
      (performance.getEntriesByType("resource") as PerformanceResourceTiming[])
        .filter((e) => e.initiatorType === "script" || /\.js(\?|$)/.test(e.name))
        .reduce((n, e) => n + (e.encodedBodySize || e.transferSize || 0), 0),
    );
    rows.push({ route: r || "/", js_gz_kb: Math.round((bytes / 1024) * 10) / 10 });
    if (r === "/home" || r === "/results") {
      lcp[r] = await page.evaluate(
        () =>
          new Promise<number>((resolve) => {
            new PerformanceObserver((l) => {
              const e = l.getEntries();
              resolve(Math.round(e[e.length - 1].startTime));
            }).observe({ type: "largest-contentful-paint", buffered: true });
            setTimeout(() => resolve(-1), 3000);
          }),
      );
    }
    await page.close();
  }
  await ctx.close();
  mkdirSync("test-results", { recursive: true });
  writeFileSync("test-results/budget.json", JSON.stringify({ budget_kb: 180, rows, lcp_ms_4x_cpu: lcp }, null, 2));
  console.log(JSON.stringify({ rows, lcp_ms_4x_cpu: lcp }));
  for (const row of rows) expect(row.js_gz_kb, row.route).toBeLessThanOrEqual(BUDGET / 1024);
});
