// App-level API types for contracts/api.md v1.2.1. Contract record types live in @evolve/ui (re-exported here).
export type { RiskOutput, LockedField, LoopState, Scenario, Reason, CoupleStatus } from "@evolve/ui/contracts";
export { LOOP_STATES } from "@evolve/ui/contracts";
import type { CoupleStatus, LoopState, RiskOutput } from "@evolve/ui/contracts";

export interface ApsiResult {
  contract_version: "1.0.0";
  status: "ok" | "refused_no_consent" | "refused_invalid_signature";
  compatible: boolean | null;
  shared_hgnc_ids: number[];
  consent_ids: string[];
  audit_event_id: string;
}

export interface Consent {
  resourceType: "Consent";
  id: string;
  status: "proposed" | "active" | "inactive" | "rejected";
  patient: string;
  purpose: "apsi-couple-compatibility";
  counterpart: string;
  period: { start: string; end: string };
  signature: string;
}

export interface Message {
  id: string;
  to: string;
  lang: "en" | "ar";
  kind: "result" | "explainer" | "care" | "escalation";
  text: string;
  locked_digests: string[];
  gate: { passed: boolean; rules: string[] };
  simulated: boolean;
}

export interface Session {
  token: string;
  partner_id: string;
  scopes: string[];
  expires_in: number;
}

export interface Vignette {
  couple_id: string;
  label: string;
  partner_ids: [string, string];
}

/** Vault call (api.md v1.1.0 pinned body). `condition` is an additive key the backend also returns. */
export interface VaultCall {
  gene: string;
  hgnc_id: number;
  classification: string;
  zygosity: string | null;
  plain_en: string;
  plain_ar: string;
  confirmatory_recommended: boolean;
  /** Pinned in api.md v1.2.1 (DECISIONS #44). condition_ar may still be absent on older backends. */
  condition?: string | null;
  condition_ar?: string | null;
}

export interface Vault {
  partner_id: string;
  calls: VaultCall[];
  records: RiskOutput[];
}

export interface CompatibilityResponse {
  apsi: ApsiResult;
  records: RiskOutput[];
  messages: Message[];
  /** v1.2.1: true => do not headline "Compatible" (counselor review first). */
  review_required: boolean;
}

export interface LoopStatus {
  state: LoopState;
  history: { state: LoopState; ts?: string; at?: string; actor_role?: string; actor?: string }[];
}

/** GET /api/me/home (v1.2.0). */
export interface Home {
  next_step: { kind: string; title_key: string; href: string };
  couple_status: CoupleStatus;
  consent: { status: Consent["status"]; expires_at: string } | null;
  counts: { results: number; notifications_unread: number };
}

/** GET /api/me/activity (v1.2.0): own AuditEvents only, no genes, no counterpart identity. */
export interface ActivityEvent {
  ts: string;
  actor_role: string;
  action: string;
  object_kind: string;
}

/** GET /api/me/notifications (v1.2.0). */
export interface Notification {
  id: string;
  ts: string;
  kind: string;
  title_key: string;
  href: string;
  read: boolean;
}

/** GET /api/me/care-plan (v1.2.0). loop.state is null until a result exists. */
export interface CarePlan {
  loop: { state: LoopState | null; history: { state: LoopState; ts: string; actor_role: string }[] };
  tasks: { id: string; kind: string; status: string; due: string }[];
  appointments: { id: string; ts: string; with_role: string; status: string; simulated: true }[];
  options: { id: string; title_key: string; body_key: string }[];
  eligibility: { immediate: boolean; checks: { key: string; status: "met" | "not_met" | "needs_review"; note_key: string }[] };
}

/** POST /api/me/teachback/start. Statements are closed templates (DECISIONS #37); `key` maps to UI wording. */
export interface TeachbackStart {
  questions: { id: string; key: string; statement: string; answer_type: "boolean" }[];
  answer_format?: string;
}
export interface TeachbackResult {
  passed: boolean;
  score: number;
  escalated: boolean;
}
export interface SureResult {
  score: number;
  escalated: boolean;
}

/** POST /api/family/tokens: single-locus cascade token, no index identity (R-PRIV-4). */
export interface FamilyToken {
  token: { hgnc_id: number; variant_digest: string; issued_at: string; expiry: string; signature: string };
  qr_payload: string;
  expires_at: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public reference?: string,
  ) {
    super(message);
  }
}
