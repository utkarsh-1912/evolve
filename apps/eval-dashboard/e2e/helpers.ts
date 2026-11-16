import type { Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

export const evidence = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "evidence.json"), "utf-8"));
export const cohort = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "cohort.json"), "utf-8"));

/** Same formatting as lib/format.ts (one fractional digit, like evidence.md). */
export const pct = (v: number) => new Intl.NumberFormat("en", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);

// TEST FIXTURE (SIMULATED): fixed guardrail events so visual baselines are deterministic.
// Shapes follow contracts/api.md; no message text, no genes. The live spec uses the real backend instead.
export const FIXTURE_EVENTS = [
  { ts: "2026-11-09T09:00:00.000000Z", rule: "all", outcome: "passed", message_id: "msg-fixture-01" },
  { ts: "2026-11-09T09:00:01.000000Z", rule: "all", outcome: "passed", message_id: "msg-fixture-02" },
  { ts: "2026-11-09T09:00:02.000000Z", rule: "directive", outcome: "blocked", message_id: "msg-fixture-03" },
  { ts: "2026-11-09T09:00:03.000000Z", rule: "directive", outcome: "escalated", message_id: "msg-fixture-03" },
  { ts: "2026-11-09T09:00:04.000000Z", rule: "leakage,missing_judicial_statement", outcome: "blocked", message_id: "probe" },
];

const CORS = { "access-control-allow-origin": "*" };

export async function stubApi(page: Page, opts: { down?: boolean } = {}) {
  await page.route("**/api/guardrail/events", (r) => (opts.down ? r.abort("connectionrefused") : r.fulfill({ json: FIXTURE_EVENTS, headers: CORS })));
}

export async function stubProbe(page: Page) {
  await page.route("**/api/demo/gate-probe", (r) =>
    r.request().method() === "OPTIONS"
      ? r.fulfill({ status: 204, headers: { ...CORS, "access-control-allow-headers": "content-type", "access-control-allow-methods": "POST" } })
      : r.fulfill({ json: { passed: false, violations: [{ rule: "directive", detail: "fixture" }] }, headers: CORS }),
  );
}
