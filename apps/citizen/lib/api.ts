// Typed client for contracts/api.md v1.2.1 (R-UX-1). Default: SIMULATED mock adapter (lib/mock).
// Set NEXT_PUBLIC_API=http://localhost:8000 to use the live backend. React Query wraps this (lib/queries.ts).
// The UI never computes risk: it only passes locked RiskOutput records through to LockedNumber (P-01, P-02).
import type {
  ActivityEvent,
  CarePlan,
  CompatibilityResponse,
  Consent,
  Home,
  LoopStatus,
  Message,
  Notification,
  Session,
  SureResult,
  TeachbackResult,
  TeachbackStart,
  FamilyToken,
  Vault,
  Vignette,
} from "./types";
import { ApiError } from "./types";

export interface Api {
  simulated: boolean;
  createSession(partner_id: string): Promise<Session>;
  vignettes(): Promise<Vignette[]>;
  vault(token: string | null): Promise<Vault>;
  listConsents(token: string | null): Promise<Consent[]>;
  grantConsent(token: string | null, counterpart: string): Promise<Consent>;
  revokeConsent(token: string | null, id: string): Promise<Consent>;
  simulatePartnerConsent(couple_id: string): Promise<{ couple_id: string; created: number; simulated: true }>;
  compatibility(token: string | null, couple_id: string): Promise<CompatibilityResponse>;
  messages(token: string | null): Promise<Message[]>;
  loop(token: string | null, couple_id: string): Promise<LoopStatus>;
  home(token: string | null): Promise<Home>;
  activity(token: string | null, limit?: number): Promise<ActivityEvent[]>;
  notifications(token: string | null): Promise<Notification[]>;
  markNotificationRead(token: string | null, id: string): Promise<Notification>;
  carePlan(token: string | null): Promise<CarePlan>;
  teachbackStart(token: string | null): Promise<TeachbackStart>;
  submitTeachback(token: string | null, answers: boolean[]): Promise<TeachbackResult>;
  submitSure(token: string | null, answers: boolean[]): Promise<SureResult>;
  familyToken(token: string | null, hgnc_id: number): Promise<FamilyToken>;
  resetDemo(): Promise<unknown>;
}

const BASE = process.env.NEXT_PUBLIC_API?.replace(/\/$/, "") ?? "";

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

const liveApi: Api = {
  simulated: false,
  createSession: (partner_id) => call("POST", "/session", null, { partner_id }),
  vignettes: () => call("GET", "/demo/vignettes", null),
  vault: (t) => call("GET", "/me/vault", t),
  listConsents: (t) => call("GET", "/consents", t),
  grantConsent: (t, counterpart) => call("POST", "/consents", t, { counterpart }),
  revokeConsent: (t, id) => call("DELETE", `/consents/${encodeURIComponent(id)}`, t),
  simulatePartnerConsent: (couple_id) => call("POST", "/demo/simulate-partner-consent", null, { couple_id }),
  compatibility: (t, couple_id) => call("POST", `/couples/${encodeURIComponent(couple_id)}/compatibility`, t),
  messages: (t) => call("GET", "/me/messages", t),
  loop: (t, couple_id) => call("GET", `/loop/${encodeURIComponent(couple_id)}`, t),
  home: (t) => call("GET", "/me/home", t),
  activity: (t, limit = 20) => call("GET", `/me/activity?limit=${limit}`, t),
  notifications: (t) => call("GET", "/me/notifications", t),
  markNotificationRead: (t, id) => call("POST", `/me/notifications/${encodeURIComponent(id)}/read`, t),
  carePlan: (t) => call("GET", "/me/care-plan", t),
  teachbackStart: (t) => call("POST", "/me/teachback/start", t),
  submitTeachback: (t, answers) => call("POST", "/teachback", t, { answers }),
  submitSure: (t, answers) => call("POST", "/sure", t, { answers }),
  familyToken: (t, hgnc_id) => call("POST", "/family/tokens", t, { hgnc_id }),
  resetDemo: () => call("POST", "/demo/reset", null),
};

// The SIMULATED mock (recorded fixtures) loads lazily and only in mock builds; live builds never ship it.
type MockApi = Omit<Api, "simulated">;
let mockPromise: Promise<MockApi> | null = null;
const loadMock = () => (mockPromise ??= import("./mock/adapter").then((m) => m.mockApi as MockApi));
const lazyMockApi = new Proxy({ simulated: true } as Api, {
  get(target, prop: string) {
    if (prop === "simulated") return true;
    return (...args: unknown[]) => loadMock().then((m) => (m[prop as keyof MockApi] as (...a: unknown[]) => unknown)(...args));
  },
});

export const api: Api = BASE ? liveApi : lazyMockApi;
export const usingMock = !BASE;
