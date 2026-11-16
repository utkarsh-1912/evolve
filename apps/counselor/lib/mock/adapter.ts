// SIMULATED mock adapter for the counselor workbench (R-UX-2). Synthetic data only.
// Static data (cases, briefs, pedigrees, locked RiskOutputs, tasks, loops) comes from fixtures.json, which
// scripts/gen_mock_fixtures.py records from the real backend. Nothing numeric is typed here (P-01, P-02).
// Behaviour mirrors services/api + runtime.enterprise.Workbench: shift gating (403 off_shift), Task targets limited
// to the consented case subjects (403 outside_consent), forward-only loop, HumanClosure only via a counselor,
// notes never visible to patients, closure closes every case of the couple.
// Fixture timestamps are re-based to "now" once per tab so SLA timers stay meaningful in a demo.
import type { Api, CaseFilters } from "../api";
import type { AppConfig, CaseRow, CaseView, FhirTask, LoopState, LoopView, Note, SummaryDraft, TaskKind, TaskStatus } from "../types";
import { ApiError, LOOP_STATES, TASK_KINDS, TASK_STATUSES, isOutside } from "../types";
import fixtures from "./fixtures.json";

interface MockCase {
  row: CaseRow;
  view: CaseView;
  loop: LoopView;
  _subjects: string[];
}

interface MockState {
  version: 1;
  cases: MockCase[];
  tokens: Record<string, { counselor_id: string; on_shift: boolean }>;
}

const KEY = "evolve.counselor.mock.v1";
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/;

function rebase<T>(value: T, offsetMs: number): T {
  if (typeof value === "string") return (ISO.test(value) ? new Date(Date.parse(value) + offsetMs).toISOString() : value) as T;
  if (Array.isArray(value)) return value.map((v) => rebase(v, offsetMs)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([k, v]) => [k, rebase(v, offsetMs)])) as T;
  }
  return value;
}

function fresh(): MockState {
  // Cases open ~2 h before "now" so the 48 h SLA timers read as a live queue.
  const offset = Date.now() - 2 * 3600_000 - Date.parse(fixtures.generated_at);
  return { version: 1, cases: rebase(fixtures.cases as unknown as MockCase[], offset), tokens: {} };
}

let memory: MockState | null = null;
function load(): MockState {
  if (typeof window === "undefined") return (memory ??= fresh());
  const raw = window.sessionStorage.getItem(KEY);
  if (raw) return JSON.parse(raw) as MockState;
  const s = fresh();
  window.sessionStorage.setItem(KEY, JSON.stringify(s));
  return s;
}
function save(s: MockState) {
  if (typeof window === "undefined") memory = s;
  else window.sessionStorage.setItem(KEY, JSON.stringify(s));
}

const now = () => new Date().toISOString();
const hex = (n: number) => Array.from(crypto.getRandomValues(new Uint8Array(n)), (b) => b.toString(16).padStart(2, "0")).join("");
const delay = <T,>(v: T) => new Promise<T>((r) => setTimeout(() => r(structuredClone(v)), 120));

function principal(s: MockState, token: string | null) {
  const p = token ? s.tokens[token] : undefined;
  if (!p) throw new ApiError(401, "invalid_token", "token invalid or expired");
  return p;
}
function onShift(s: MockState, token: string | null) {
  const p = principal(s, token);
  if (!p.on_shift) throw new ApiError(403, "off_shift", "off shift");
  return p;
}
function findCase(s: MockState, id: string): MockCase {
  const c = s.cases.find((x) => x.row.case_id === id);
  if (!c) throw new ApiError(404, "not_found", "not found");
  return c;
}
function rowOf(c: MockCase): CaseRow {
  return { ...c.row, couple_status: c.loop ? c.loop.state : "no_active_loop" };
}
function audit(c: MockCase, action: string) {
  c.view.timeline.push({ ts: now(), kind: "audit", action, outcome: "success" });
}
function advance(s: MockState, coupleId: string, to: LoopState) {
  const cases = s.cases.filter((c) => c.row.couple_id === coupleId);
  if (!cases.length) throw new ApiError(404, "not_found", "not found");
  const loop = cases[0].loop;
  const cur = LOOP_STATES.indexOf(loop.state);
  const nxt = LOOP_STATES.indexOf(to);
  if (nxt < 0 || nxt <= cur) throw new ApiError(409, "invalid_transition", "transitions are forward only");
  const entry = { ts: now(), state: to, to, actor_role: "counselor", skipped: LOOP_STATES.slice(cur + 1, nxt) };
  for (const c of cases) {
    c.loop = { ...c.loop, state: to, history: [...c.loop.history, entry] };
    c.view.timeline.push({ ts: entry.ts, kind: "loop", state: to, actor_role: "counselor" });
  }
  return cases[0].loop;
}

// SIMULATED AI-draft mode for demos/tests (sessionStorage "evolve.counselor.mock.ai"):
// unset/"disabled" = config off (DEFAULT while the AI draft is paused, coordinator 2026-11-16) · "on" = offline stub ·
// "blocked" = gate held the draft · "unavailable" = 503 llm_unavailable.
const AI_KEY = "evolve.counselor.mock.ai";
const aiMode = () => (typeof window === "undefined" ? "" : (window.sessionStorage.getItem(AI_KEY) ?? ""));

/** Offline-stub draft (api.md v1.3.0): English, built only from the consented-scope brief; no partner IDs, no notes.
 *  Figures are the locked display strings copied verbatim (P-01); nothing is computed. */
function stubDraft(v: CaseView): string {
  const b = v.brief;
  const lines = [`Case opened under trigger (${b.trigger}).`];
  if (b.pedigree) lines.push(`Relationship: ${b.pedigree.relationship.replace(/_/g, " ")}.`);
  for (const x of b.variant_summary) {
    if (isOutside(x)) continue;
    const fig = x.offspring_risk_one_in ? ` Locked figure for each pregnancy: ${x.offspring_risk_one_in}.` : " No figure was calculated; counselor review.";
    lines.push(`${x.gene}: ${x.scenario.replace(/_/g, " ")}.${fig}`);
  }
  if (b.pedigree?.family_history.length) lines.push(`Family history recorded: ${b.pedigree.family_history.map((f) => f.finding).join("; ")}.`);
  lines.push("Points to discuss: what the result means, what options exist, and what the couple would like to do next.");
  return lines.join(" ");
}

export const mockApi: Api = {
  simulated: true,
  async createSession(counselor_id) {
    const s = load();
    const token = `sim-${hex(16)}`;
    s.tokens[token] = { counselor_id, on_shift: false };
    save(s);
    return delay({ token, counselor_id, scopes: ["user/DiagnosticReport.rs", "user/Task.cru"], expires_in: 3600, on_shift: false });
  },
  async setShift(token, on) {
    const s = load();
    const p = principal(s, token);
    p.on_shift = on;
    save(s);
    return delay({ counselor_id: p.counselor_id, on_shift: on });
  },
  async cases(token, f: CaseFilters = {}) {
    const s = load();
    onShift(s, token);
    let rows = s.cases.map(rowOf);
    if (f.status) rows = rows.filter((r) => r.status === f.status);
    if (f.trigger) rows = rows.filter((r) => r.trigger === f.trigger);
    rows.sort((a, b) => a.sla_due_at.localeCompare(b.sla_due_at) || a.case_id.localeCompare(b.case_id));
    return delay(rows);
  },
  async caseView(token, id) {
    const s = load();
    const p = onShift(s, token);
    const c = findCase(s, id);
    if (!c.row.assigned_to) c.row.assigned_to = p.counselor_id;
    save(s);
    const view: CaseView = {
      ...c.view,
      case: rowOf(c),
      timeline: [...c.view.timeline].sort((a, b) => a.ts.localeCompare(b.ts)),
      access_basis: { ...c.view.access_basis, on_shift: true },
    };
    return delay(view);
  },
  async loop(token, coupleId) {
    const s = load();
    principal(s, token);
    const c = s.cases.find((x) => x.row.couple_id === coupleId);
    if (!c) throw new ApiError(404, "not_found", "not found");
    return delay(c.loop);
  },
  async advanceLoop(token, coupleId, to) {
    const s = load();
    principal(s, token);
    const loop = advance(s, coupleId, to);
    save(s);
    return delay(loop);
  },
  async createTask(token, id, body: { kind: TaskKind; hgnc_id?: number }) {
    const s = load();
    onShift(s, token);
    const c = findCase(s, id);
    if (!TASK_KINDS.includes(body.kind)) throw new ApiError(422, "invalid_request", "request body or parameters are invalid");
    if (!c._subjects.length) throw new ApiError(403, "outside_consent", "outside consent");
    const authored = new Date();
    const made: FhirTask[] = c._subjects.map((pid) => ({
      resourceType: "Task",
      id: `task-${hex(6)}`,
      status: "requested",
      intent: "order",
      code: { text: body.kind },
      description_key: `task.${body.kind}`,
      for: { reference: `Patient/${pid}` },
      authoredOn: authored.toISOString(),
      restriction: { period: { end: new Date(authored.getTime() + 14 * 86400_000).toISOString() } },
      owner: { display: "genetic counselor" },
      meta: { tag: [{ system: "urn:evolve:demo", code: "SIMULATED" }] },
      ...(body.hgnc_id ? { focus: { display: `HGNC:${body.hgnc_id}` } } : {}),
    }));
    for (const x of s.cases.filter((k) => k.row.couple_id === c.row.couple_id)) x.view.tasks.push(...made);
    save(s);
    return delay(made.length === 1 ? made[0] : { tasks: made });
  },
  async updateTask(token, id, taskId, status: TaskStatus) {
    const s = load();
    onShift(s, token);
    const c = findCase(s, id);
    if (!TASK_STATUSES.includes(status)) throw new ApiError(422, "invalid_request", "request body or parameters are invalid");
    const t = c.view.tasks.find((x) => x.id === taskId);
    if (!t) throw new ApiError(404, "not_found", "not found");
    const stamp = now();
    for (const x of s.cases.filter((k) => k.row.couple_id === c.row.couple_id)) {
      const tt = x.view.tasks.find((y) => y.id === taskId);
      if (tt) Object.assign(tt, { status, lastModified: stamp });
    }
    audit(c, "task.update");
    if (status === "completed") {
      const target = ({ confirmatory_test: "ConfirmatoryDone", appointment: "CounselingDone", referral: "ReproReferralDone" } as Record<string, LoopState>)[
        t.code.text
      ];
      const same = c.view.tasks.filter((x) => x.code.text === t.code.text && x.status !== "cancelled");
      if (target && same.every((x) => x.status === "completed")) {
        try {
          advance(s, c.row.couple_id, target);
        } catch {
          /* already at or past this state (backend behaviour) */
        }
      }
    }
    save(s);
    return delay({ ...t, status, lastModified: stamp });
  },
  async addNote(token, id, text) {
    const s = load();
    const p = onShift(s, token);
    const c = findCase(s, id);
    if (!text.trim() || text.length > 5000) throw new ApiError(422, "invalid_request", "request body or parameters are invalid");
    const n: Note = { id: `note-${hex(6)}`, ts: now(), author: p.counselor_id, kind: "note", text, visible_to_patient: false };
    c.view.notes.push(n);
    audit(c, "note.create");
    save(s);
    return delay(n);
  },
  async closure(token, id, summary) {
    const s = load();
    const p = onShift(s, token);
    const c = findCase(s, id);
    if (!summary.trim() || summary.length > 5000) throw new ApiError(422, "invalid_request", "request body or parameters are invalid");
    if (!c.loop) throw new ApiError(409, "no_active_loop", "no active loop");
    if (c.loop.state !== "HumanClosure") advance(s, c.row.couple_id, "HumanClosure");
    c.view.notes.push({ id: `note-${hex(6)}`, ts: now(), author: p.counselor_id, kind: "closure", text: summary, visible_to_patient: false });
    audit(c, "note.create");
    for (const x of s.cases.filter((k) => k.row.couple_id === c.row.couple_id)) x.row.status = "closed";
    audit(c, "case.closure");
    save(s);
    return delay({ case: rowOf(c), loop: c.loop });
  },
  async config(): Promise<AppConfig> {
    return delay({ ai_draft_enabled: ["on", "blocked", "unavailable"].includes(aiMode()), provider: "offline-stub", environment: "local" });
  },
  async summaryDraft(token: string, id: string): Promise<SummaryDraft> {
    const s = load();
    onShift(s, token);
    const c = findCase(s, id);
    const mode = aiMode();
    if (mode === "unavailable") throw new ApiError(503, "llm_unavailable", "AI provider unavailable");
    const base = { provider: "offline-stub", model: "offline-stub", generated_at: now(), ai_generated: true as const, input_fields: ["trigger", "pedigree", "variant_summary"] };
    if (mode === "blocked") {
      return delay({ ...base, draft: null, gate: { passed: false, violations: [{ rule: "false_reassurance", detail: "absolute safety claim in draft" }] } });
    }
    return delay({ ...base, draft: stubDraft(c.view), gate: { passed: true, violations: [] } });
  },
};

/** Test/demo helper: forget mock state (SIMULATED reset). */
export function resetMock() {
  if (typeof window !== "undefined") window.sessionStorage.removeItem(KEY);
  memory = null;
}
