// SIMULATED mock adapter for contracts/api.md v1.2.1 (TASK-P3-UI-CIT). Synthetic data only.
// Static responses are RECORDED from the real backend (scripts/gen_mock_fixtures.py replays V1–V5 through
// services/api in-process), so mock and live return the same shapes, templates and locked numbers.
// Dynamic state (consents, "result ready", own activity, read state, teach-back/SURE outcomes) lives in sessionStorage
// and follows the backend's rules: token scoping (P-06), 409 without both consents (P-07), records only after the check.
import fixtures from "./fixtures.json";
import type {
  ActivityEvent,
  CarePlan,
  CompatibilityResponse,
  Consent,
  FamilyToken,
  Home,
  LoopState,
  LoopStatus,
  Message,
  Notification,
  Session,
  SureResult,
  TeachbackResult,
  TeachbackStart,
  Vault,
  Vignette,
} from "../types";
import { ApiError } from "../types";

export const SIMULATED = true;

interface PartnerFx {
  couple_id: string;
  counterpart: string;
  vault: Vault;
  compatibility: CompatibilityResponse;
  messages: Message[];
  care_plan_pre: CarePlan;
  care_plan_post: CarePlan;
  notifications_pre: Notification[];
  notifications_post: Notification[];
  teachback: TeachbackStart;
  family_tokens: Record<string, FamilyToken>;
  // Recorded with lang=ar sessions (closed Arabic templates; DECISIONS #37/#48).
  compatibility_ar: CompatibilityResponse;
  messages_ar: Message[];
  teachback_ar: TeachbackStart;
}
const F = fixtures as unknown as { vignettes: Vignette[]; partners: Record<string, PartnerFx>; teachback_key: Record<string, boolean> };

const KEYS = {
  consents: "evolve.mock.consents.v2",
  activity: "evolve.mock.activity.v2",
  read: "evolve.mock.read.v2",
  ready: "evolve.mock.ready.v2",
  teachback: "evolve.mock.teachback.v2",
} as const;

function read<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function write(key: string, value: unknown) {
  if (typeof window !== "undefined") window.sessionStorage.setItem(key, JSON.stringify(value));
}

type ConsentStore = Record<string, Consent>;
const delay = (ms = 100) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString();
const tokenFor = (pid: string, lang: "en" | "ar" = "en") => `sim-token-${pid}${lang === "ar" ? ".ar" : ""}`;
const langOf = (token: string | null): "en" | "ar" => (token?.endsWith(".ar") ? "ar" : "en");

function me(token: string | null): string {
  const pid = token?.startsWith("sim-token-") ? token.slice("sim-token-".length).replace(/\.ar$/, "") : null;
  if (!pid || !F.partners[pid]) throw new ApiError(401, "unauthorized", "Sign in again (SIMULATED).", "SIM-401");
  return pid;
}
const fx = (pid: string) => F.partners[pid];
const isReady = (couple: string) => !!read<Record<string, boolean>>(KEYS.ready, {})[couple];
function setReady(couple: string, v: boolean) {
  const r = read<Record<string, boolean>>(KEYS.ready, {});
  r[couple] = v;
  write(KEYS.ready, r);
}
function active(store: ConsentStore, patient: string, counterpart: string) {
  return Object.values(store).find((c) => c.patient === patient && c.counterpart === counterpart && c.status === "active" && c.period.end > now());
}

/** Own AuditEvent, backend vocabulary (viewed/submitted/revoked), no genes, no counterpart identity. */
function audit(pid: string, action: string, object_kind: string) {
  const all = read<Record<string, ActivityEvent[]>>(KEYS.activity, {});
  const list = all[pid] ?? [];
  const last = list[0];
  if (last && last.action === action && last.object_kind === object_kind && Date.parse(now()) - Date.parse(last.ts) < 60_000) return;
  all[pid] = [{ ts: now(), actor_role: "you", action, object_kind }, ...list].slice(0, 200);
  write(KEYS.activity, all);
}

function makeConsent(patient: string, counterpart: string): Consent {
  const start = new Date();
  const end = new Date(start.getTime() + 30 * 24 * 3600 * 1000); // live backend: 30-day consent window
  return {
    resourceType: "Consent",
    id: `consent-${patient}-${start.getTime()}-sim`,
    status: "active",
    patient,
    purpose: "apsi-couple-compatibility",
    counterpart,
    period: { start: start.toISOString(), end: end.toISOString() },
    signature: "SIMULATED-signature",
  };
}

function teachbackPassed(pid: string) {
  return !!read<Record<string, boolean>>(KEYS.teachback, {})[pid];
}

function carePlanFor(pid: string): CarePlan {
  const f = fx(pid);
  const base = isReady(f.couple_id) ? f.care_plan_post : f.care_plan_pre;
  if (!teachbackPassed(pid) || !base.loop.state) return base;
  // Mirrors the backend: a passed teach-back records ComprehensionConfirmed on the loop.
  const order: LoopState[] = ["ResultIssued", "PatientNotified", "ComprehensionConfirmed"];
  if (order.indexOf(base.loop.state) >= 2) return base;
  return {
    ...base,
    loop: { state: "ComprehensionConfirmed", history: [...base.loop.history, { state: "ComprehensionConfirmed", ts: now(), actor_role: "you" }] },
  };
}

export const mockApi = {
  simulated: true as const,

  async createSession(partner_id: string, lang: "en" | "ar" = "en"): Promise<Session> {
    await delay();
    if (!F.partners[partner_id]) throw new ApiError(404, "not_found", "Unknown synthetic partner.", "SIM-404");
    audit(partner_id, "signed_in", "session");
    return { token: tokenFor(partner_id, lang), partner_id, scopes: ["patient/Observation.rs", "patient/DiagnosticReport.r", "patient/Consent.cru"], expires_in: 3600 };
  },

  async vignettes(): Promise<Vignette[]> {
    await delay();
    return F.vignettes;
  },

  async vault(token: string | null): Promise<Vault> {
    await delay();
    const pid = me(token);
    audit(pid, "viewed", "results");
    const v = fx(pid).vault;
    // Live: locked records exist only after the compatibility check has run.
    return isReady(fx(pid).couple_id) ? v : { ...v, records: [] };
  },

  async listConsents(token: string | null): Promise<Consent[]> {
    await delay(60);
    const pid = me(token);
    return Object.values(read<ConsentStore>(KEYS.consents, {})).filter((c) => c.patient === pid || c.counterpart === pid);
  },

  async grantConsent(token: string | null, counterpart: string): Promise<Consent> {
    await delay();
    const pid = me(token);
    if (counterpart !== fx(pid).counterpart) throw new ApiError(403, "forbidden", "Not your partner.", "SIM-403");
    const store = read<ConsentStore>(KEYS.consents, {});
    const c = makeConsent(pid, counterpart);
    store[c.id] = c;
    write(KEYS.consents, store);
    audit(pid, "submitted", "consent");
    return c;
  },

  async revokeConsent(token: string | null, id: string): Promise<Consent> {
    await delay();
    const pid = me(token);
    const store = read<ConsentStore>(KEYS.consents, {});
    const c = store[id];
    if (!c || c.patient !== pid) throw new ApiError(404, "not_found", "Consent not found.", "SIM-404");
    c.status = "inactive";
    write(KEYS.consents, store);
    setReady(fx(pid).couple_id, false); // revocation purges the couple workspace (P-07)
    audit(pid, "revoked", "consent");
    return c;
  },

  /** Demo-only (DECISIONS #28): the other partner consents, as if on their own device. SIMULATED. */
  async simulatePartnerConsent(couple_id: string) {
    await delay();
    const v = F.vignettes.find((x) => x.couple_id === couple_id);
    if (!v) throw new ApiError(404, "not_found", "Unknown couple.", "SIM-404");
    const store = read<ConsentStore>(KEYS.consents, {});
    let created = 0;
    for (const [p, q] of [v.partner_ids, [...v.partner_ids].reverse()] as [string, string][]) {
      if (!active(store, p, q) && active(store, q, p)) {
        const c = makeConsent(p, q);
        store[c.id] = c;
        created++;
      }
    }
    write(KEYS.consents, store);
    return { couple_id, created, simulated: true as const };
  },

  async compatibility(token: string | null, couple_id: string): Promise<CompatibilityResponse> {
    await delay(200);
    const pid = me(token);
    const f = fx(pid);
    if (f.couple_id !== couple_id) throw new ApiError(403, "forbidden", "Not your couple.", "SIM-403");
    const store = read<ConsentStore>(KEYS.consents, {});
    if (!active(store, pid, f.counterpart) || !active(store, f.counterpart, pid)) {
      throw new ApiError(409, "consent_required", "Both partners must consent first.", "SIM-409");
    }
    setReady(couple_id, true);
    audit(pid, "submitted", "compatibility");
    return langOf(token) === "ar" ? f.compatibility_ar : f.compatibility;
  },

  async messages(token: string | null): Promise<Message[]> {
    await delay();
    const pid = me(token);
    audit(pid, "viewed", "messages");
    return isReady(fx(pid).couple_id) ? (langOf(token) === "ar" ? fx(pid).messages_ar : fx(pid).messages) : [];
  },

  async loop(token: string | null, couple_id: string): Promise<LoopStatus> {
    await delay();
    const pid = me(token);
    if (fx(pid).couple_id !== couple_id) throw new ApiError(403, "forbidden", "Not your couple.", "SIM-403");
    const l = carePlanFor(pid).loop;
    return { state: (l.state ?? "ResultIssued") as LoopState, history: l.history };
  },

  /** GET /api/me/home: same next-step rules as the backend (home.next.*). */
  async home(token: string | null): Promise<Home> {
    await delay(60);
    const pid = me(token);
    const f = fx(pid);
    const store = read<ConsentStore>(KEYS.consents, {});
    const mine = active(store, pid, f.counterpart);
    const theirs = active(store, f.counterpart, pid);
    const ready = isReady(f.couple_id) && !!mine && !!theirs;
    const couple_status: Home["couple_status"] = ready ? "result_ready" : mine && theirs ? "both_consented" : mine ? "invited" : "not_linked";
    const step = (kind: string, href: string) => ({ kind, title_key: `home.next.${kind}`, href });
    const next_step = ready
      ? teachbackPassed(pid)
        ? step("care_plan", "/care-plan")
        : step("teachback", "/teachback")
      : mine && theirs
        ? step("run_check", "/compatibility")
        : mine
          ? step("wait_partner", "/compatibility")
          : theirs
            ? step("consent", "/compatibility")
            : step("invite", "/compatibility");
    audit(pid, "viewed", "home");
    const unread = (await mockApi.notifications(token)).filter((n) => !n.read).length;
    return { next_step, couple_status, consent: mine ? { status: mine.status, expires_at: mine.period.end } : null, counts: { results: f.vault.calls.length, notifications_unread: unread } };
  },

  async activity(token: string | null, limit = 20): Promise<ActivityEvent[]> {
    await delay(60);
    const pid = me(token);
    return (read<Record<string, ActivityEvent[]>>(KEYS.activity, {})[pid] ?? []).slice(0, limit);
  },

  async notifications(token: string | null): Promise<Notification[]> {
    await delay(40);
    const pid = me(token);
    const f = fx(pid);
    const readIds = new Set(read<string[]>(KEYS.read, []));
    const list = isReady(f.couple_id) ? f.notifications_post : f.notifications_pre;
    return list.map((n) => ({ ...n, read: n.read || readIds.has(n.id) }));
  },

  async markNotificationRead(token: string | null, id: string): Promise<Notification> {
    await delay(40);
    const pid = me(token);
    const f = fx(pid);
    const n = [...f.notifications_post, ...f.notifications_pre].find((x) => x.id === id);
    if (!n) throw new ApiError(404, "not_found", "Notification not found.", "SIM-404");
    write(KEYS.read, [...new Set([...read<string[]>(KEYS.read, []), id])]);
    return { ...n, read: true };
  },

  async carePlan(token: string | null): Promise<CarePlan> {
    await delay(60);
    const pid = me(token);
    audit(pid, "viewed", "care_plan");
    return carePlanFor(pid);
  },

  async teachbackStart(token: string | null): Promise<TeachbackStart> {
    await delay(60);
    return langOf(token) === "ar" ? fx(me(token)).teachback_ar : fx(me(token)).teachback;
  },

  /** Scored with the backend's answer key (recorded into the SIMULATED fixtures). Failure escalates (trigger d). */
  async submitTeachback(token: string | null, answers: boolean[]): Promise<TeachbackResult> {
    await delay();
    const pid = me(token);
    const qs = fx(pid).teachback.questions;
    const score = qs.reduce((n, q, i) => n + (answers[i] === F.teachback_key[q.id] ? 1 : 0), 0);
    const passed = answers.length === qs.length && score === qs.length;
    const tb = read<Record<string, boolean>>(KEYS.teachback, {});
    tb[pid] = passed || !!tb[pid];
    write(KEYS.teachback, tb);
    audit(pid, "submitted", "teachback");
    return { passed, score, escalated: !passed };
  },

  async submitSure(token: string | null, answers: boolean[]): Promise<SureResult> {
    await delay();
    const pid = me(token);
    if (answers.length !== 4) throw new ApiError(422, "invalid", "SURE needs exactly four yes/no answers.", "SIM-422");
    const score = answers.filter(Boolean).length;
    audit(pid, "submitted", "sure");
    return { score, escalated: score < 4 };
  },

  /** Own P/LP calls only (R-PRIV-4); token recorded from the backend's signer. */
  async familyToken(token: string | null, hgnc_id: number): Promise<FamilyToken> {
    await delay(150);
    const pid = me(token);
    const t = fx(pid).family_tokens[String(hgnc_id)];
    if (!t) throw new ApiError(403, "forbidden", "Tokens are only for your own carrier findings.", "SIM-403");
    audit(pid, "submitted", "family_token");
    return t;
  },

  async resetDemo() {
    if (typeof window !== "undefined") Object.values(KEYS).forEach((k) => window.sessionStorage.removeItem(k));
    return { reset: true };
  },
};
