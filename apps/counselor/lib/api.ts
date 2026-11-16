// Typed client for the counselor endpoints of contracts/api.md v1.2.1 (R-UX-2).
// Backend selection: see API_BASE below (NEXT_PUBLIC_API at build).
// The UI never computes risk; locked RiskOutput records pass straight through to LockedNumber (P-01, P-02).
import { mockApi } from "./mock/adapter";
import type { AppConfig, CaseRow, CaseView, CounselorSession, FhirTask, LoopState, LoopView, Note, SummaryDraft, TaskKind, TaskStatus } from "./types";
import { ApiError } from "./types";

export interface CaseFilters {
  status?: string;
  trigger?: string;
}

export interface Api {
  simulated: boolean;
  createSession(counselor_id: string): Promise<CounselorSession>;
  setShift(token: string, on: boolean): Promise<{ counselor_id: string; on_shift: boolean }>;
  cases(token: string, filters?: CaseFilters): Promise<CaseRow[]>;
  caseView(token: string, caseId: string): Promise<CaseView>;
  loop(token: string, coupleId: string): Promise<LoopView>;
  advanceLoop(token: string, coupleId: string, to: LoopState): Promise<LoopView>;
  createTask(token: string, caseId: string, body: { kind: TaskKind; hgnc_id?: number }): Promise<FhirTask | { tasks: FhirTask[] }>;
  updateTask(token: string, caseId: string, taskId: string, status: TaskStatus): Promise<FhirTask>;
  addNote(token: string, caseId: string, text: string): Promise<Note>;
  closure(token: string, caseId: string, summary: string): Promise<{ case: CaseRow; loop: LoopView }>;
  /** v1.3.0 */
  config(): Promise<AppConfig>;
  summaryDraft(token: string, caseId: string): Promise<SummaryDraft>;
}

// API base URL, inlined at build time (both deploy targets, DECISIONS #62):
//   NEXT_PUBLIC_API=<url>  -> that backend
//   NEXT_PUBLIC_API=mock   -> SIMULATED mock adapter (e2e builds)
//   unset                  -> production build: http://localhost:8000 · `next dev`: SIMULATED mock (run_local --Mock offline mode)
const RAW = process.env.NEXT_PUBLIC_API?.trim();
export const USE_MOCK = RAW === "mock" || (!RAW && process.env.NODE_ENV !== "production");
export const API_BASE = (RAW && RAW !== "mock" ? RAW : "http://localhost:8000").replace(/\/$/, "");
const BASE = API_BASE;

async function call<T>(method: string, path: string, token: string | null, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, {
      method,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network", "Network error");
  }
  if (!res.ok) {
    let code = "error";
    let message = res.statusText;
    try {
      const j = (await res.json()) as { error?: { code: string; message: string }; detail?: string };
      code = j.error?.code ?? j.detail ?? code;
      message = j.error?.message ?? message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code, message, res.headers.get("x-request-id") ?? undefined);
  }
  return (await res.json()) as T;
}

const enc = encodeURIComponent;

const liveApi: Api = {
  simulated: false,
  createSession: async (counselor_id) => {
    const s = await call<{ token: string; scopes: string[]; expires_in: number }>("POST", "/session", null, { role: "counselor", counselor_id });
    // Shift defaults OFF on every new counselor session (DECISIONS #40 (4)).
    return { token: s.token, counselor_id, scopes: s.scopes, expires_in: s.expires_in, on_shift: false };
  },
  setShift: (t, on) => call("POST", "/counselor/shift", t, { on }),
  cases: (t, f = {}) => {
    const q = new URLSearchParams();
    if (f.status) q.set("status", f.status);
    if (f.trigger) q.set("trigger", f.trigger);
    const qs = q.toString();
    return call("GET", `/counselor/cases${qs ? `?${qs}` : ""}`, t);
  },
  caseView: (t, id) => call("GET", `/counselor/cases/${enc(id)}`, t),
  loop: (t, cid) => call("GET", `/loop/${enc(cid)}`, t),
  advanceLoop: (t, cid, to) => call("POST", `/loop/${enc(cid)}/advance`, t, { to }),
  createTask: (t, id, body) => call("POST", `/counselor/cases/${enc(id)}/tasks`, t, body),
  updateTask: (t, id, tid, status) => call("PATCH", `/counselor/cases/${enc(id)}/tasks/${enc(tid)}`, t, { status }),
  addNote: (t, id, text) => call("POST", `/counselor/cases/${enc(id)}/notes`, t, { text }),
  closure: (t, id, summary) => call("POST", `/counselor/cases/${enc(id)}/closure`, t, { summary }),
  config: () => call("GET", "/config", null),
  summaryDraft: (t, id) => call("POST", `/counselor/cases/${enc(id)}/summary-draft`, t),
};

export const api: Api = USE_MOCK ? mockApi : liveApi;
