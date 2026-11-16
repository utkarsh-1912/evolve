import { expect, test, type APIRequestContext } from "@playwright/test";
import { PANEL } from "./helpers";

// Live verification against the real backend (playwright.live.config.ts). Seeds V1–V5 through the API exactly like
// the demo, plus a failed teach-back for V4A (trigger d), then drives the workbench UI. Nothing is mocked.
const API = "http://localhost:8000/api";

async function session(request: APIRequestContext, body: object) {
  const r = await request.post(`${API}/session`, { data: body });
  expect(r.ok()).toBeTruthy();
  return { Authorization: `Bearer ${(await r.json()).token}` };
}

test.beforeAll(async ({ request }) => {
  expect((await request.post(`${API}/demo/reset`)).ok()).toBeTruthy();
  const vig = (await (await request.get(`${API}/demo/vignettes`)).json()) as { couple_id: string; partner_ids: [string, string] }[];
  for (const v of vig) {
    const [a, b] = v.partner_ids;
    const ha = await session(request, { partner_id: a });
    const hb = await session(request, { partner_id: b });
    await request.post(`${API}/consents`, { data: { counterpart: b }, headers: ha });
    await request.post(`${API}/consents`, { data: { counterpart: a }, headers: hb });
    expect((await request.post(`${API}/couples/${v.couple_id}/compatibility`, { headers: ha })).ok()).toBeTruthy();
  }
  const h4 = await session(request, { partner_id: "V4A" });
  await request.post(`${API}/me/teachback/start`, { headers: h4 });
  await request.post(`${API}/teachback`, { data: { answers: [false, false, false, false] }, headers: h4 });
});

test("live: backend refuses case data off shift (403 off_shift)", async ({ request }) => {
  const hc = await session(request, { role: "counselor" });
  const r = await request.get(`${API}/counselor/cases`, { headers: hc });
  expect(r.status()).toBe(403);
  expect((await r.json()).error.code).toBe("off_shift");
});

test("live: workbench end to end (queue a–d, V1 pedigree + F, V4 placeholders, note, closure)", async ({ page, request }) => {
  await page.goto("/en/sign-in");
  await page.getByTestId("sign-in").click();
  await page.waitForURL(/\/en\/queue/);
  await expect(page.getByTestId("off-shift")).toBeVisible();
  await page.getByTestId("shift-switch").click();
  const rows = page.locator("[data-testid=case-table] tbody tr[tabindex]");
  await expect(rows).toHaveCount(5);
  for (const tr of ["(a)", "(b)", "(c)", "(d)"]) await expect(page.getByTestId("case-table")).toContainText(tr);

  // V1 (a)
  await page.locator("[data-testid=case-table] tbody tr", { hasText: "(a)" }).click();
  await expect(page.getByTestId("case-view")).toHaveAttribute("data-trigger", "a");
  await expect(page.getByTestId("access-basis")).toContainText("couple consent");
  await page.getByRole("tab", { name: /Pedigree/ }).click();
  await expect(page.locator("[data-union=consanguineous]")).toHaveCount(1);
  await expect(page.getByTestId("locked-F")).toHaveText("0.0625");
  await page.getByRole("tab", { name: /Variants/ }).click();
  await expect(page.getByTestId("variant-record")).toHaveAttribute("data-gene", "HBB");
  const v1case = await page.getByTestId("case-view").getAttribute("data-case");

  // V4 (d): placeholders say nothing; no gene outside the in-scope records appears anywhere.
  await page.goto("/en/queue");
  await page.locator("[data-testid=case-table] tbody tr", { hasText: "(d)" }).click();
  await expect(page.getByTestId("comprehension")).toContainText("Not passed");
  await page.getByRole("tab", { name: /Variants/ }).click();
  await expect(page.getByTestId("outside-consent")).toHaveText("Outside consented scope");
  const allowed = new Set(await page.getByTestId("variant-record").evaluateAll((els) => els.map((e) => e.getAttribute("data-gene") ?? "")));
  const text = await page.locator("body").innerText();
  expect(PANEL.map((g) => g.symbol).filter((s) => !allowed.has(s) && new RegExp(`\\b${s}\\b`).test(text))).toEqual([]);

  // V1: note + human closure through the real API.
  await page.goto(`/en/cases/${v1case}`);
  await page.getByRole("tab", { name: /Notes/ }).click();
  await page.getByTestId("note-form").getByRole("textbox").fill("Live check note.");
  await page.getByTestId("note-add").click();
  await expect(page.getByTestId("note-list")).toContainText("Live check note.");
  await page.getByTestId("action-closure").click();
  await page.getByTestId("closure-summary").fill("Live closure.");
  await page.getByTestId("closure-next").click();
  await page.getByTestId("closure-confirm-confirm").click();
  await expect(page.getByTestId("case-closed")).toBeVisible();

  const hc = await session(request, { role: "counselor" });
  const loop = await (await request.get(`${API}/loop/V1`, { headers: hc })).json();
  expect(loop.state).toBe("HumanClosure");
});
