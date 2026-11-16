// Counselor API types for contracts/api.md v1.2.1 (P3 counselor endpoints; DONE-P3-AR shapes).
// Contract record types (RiskOutput, LoopState) live in @evolve/ui and are re-exported here.
export type { RiskOutput, LockedField, LoopState, Scenario, Reason } from "@evolve/ui";
export { LOOP_STATES } from "@evolve/ui";
import type { LoopState, RiskOutput } from "@evolve/ui";
import type { PedigreeEdge, PedigreeNode } from "@evolve/ui";

export type Trigger = "a" | "b" | "c" | "d" | "gate";
export const TRIGGERS: readonly Trigger[] = ["a", "b", "c", "d", "gate"] as const;
export type Priority = "urgent" | "high" | "normal";
export type CaseStatus = "open" | "closed";
/** Loop state, or a backend marker when the couple has no active loop. */
export type CoupleStatus = LoopState | "no_active_loop" | "consent_revoked_or_pending";

export interface CaseRow {
  case_id: string;
  couple_id: string;
  trigger: Trigger;
  priority: Priority;
  opened_at: string;
  sla_due_at: string;
  couple_status: CoupleStatus;
  assigned_to: string | null;
  /** Additive key (DONE-P3-AR deviations). */
  status: CaseStatus;
}

/** A variant outside the consented scope: a placeholder that says nothing (docs/09 §4.2). */
export interface OutsideConsent {
  outside_consent: true;
}
export type ScopedVariant = RiskOutput | OutsideConsent;
export const isOutside = (v: ScopedVariant | BriefVariant): v is OutsideConsent => "outside_consent" in v && v.outside_consent === true;

/** Brief variant summary: a subset of the RiskOutput fields (display strings only). */
export type BriefVariant =
  | OutsideConsent
  | (Pick<RiskOutput, "gene" | "hgnc_id" | "scenario" | "status" | "audience" | "carrier_role" | "reason" | "digest"> & {
      offspring_risk_one_in: string | null;
      posterior_carrier_b_one_in: string | null;
      reference_unrelated_one_in: string | null;
      relative_to_unrelated_display: string | null;
      escalate: boolean;
    });

export interface Brief {
  case_id: string;
  couple_id: string;
  trigger: Trigger;
  created_at: string;
  consent_revoked_data_purged: boolean;
  pedigree: {
    relationship: string;
    wright_paths: number;
    F: number | null;
    fusage: "genome_wide_context_only";
    family_history: { finding: string; hpo?: string }[];
  } | null;
  variant_summary: BriefVariant[];
  pending_tasks: { for: string; status: string; intent: string; code: string; description: string }[];
  couple_questions: string[];
  comprehension: Record<string, { teachback: { score: number; passed: boolean } | null; sure: { score: number; escalated?: boolean } | null }>;
  note: string;
}

export interface Pedigree {
  nodes: PedigreeNode[];
  edges: PedigreeEdge[];
  F: number | null;
  fusage: "genome_wide_context_only";
  relationship: string;
}

export type TaskKind = "confirmatory_test" | "appointment" | "follow_up" | "referral" | "sure_check";
export const TASK_KINDS: readonly TaskKind[] = ["confirmatory_test", "appointment", "follow_up", "referral", "sure_check"] as const;
export type TaskStatus = "requested" | "accepted" | "in-progress" | "completed" | "cancelled";
export const TASK_STATUSES: readonly TaskStatus[] = ["requested", "accepted", "in-progress", "completed", "cancelled"] as const;

/** FHIR-shaped Task (R4 subset) as returned to the counselor. */
export interface FhirTask {
  resourceType: "Task";
  id: string;
  status: TaskStatus;
  intent: string;
  code: { text: TaskKind | string };
  description_key: string;
  for: { reference: string };
  authoredOn: string;
  lastModified?: string;
  restriction?: { period?: { end?: string } };
  owner?: { display: string };
  meta?: { tag?: { system: string; code: string }[] };
  focus?: { display: string };
}

export interface Note {
  id: string;
  ts: string;
  author: string;
  kind: "note" | "closure";
  text: string;
  visible_to_patient: false;
}

export type TimelineEntry =
  | { ts: string; kind: "loop"; state: LoopState; actor_role: string }
  | { ts: string; kind: "audit"; action: string; outcome: string };

export interface AccessBasis {
  couple_consent: boolean;
  on_shift: boolean;
}

export interface CaseView {
  case: CaseRow;
  brief: Brief;
  pedigree: Pedigree | null;
  variants: ScopedVariant[];
  tasks: FhirTask[];
  notes: Note[];
  timeline: TimelineEntry[];
  access_basis: AccessBasis;
  simulated: boolean;
}

export interface LoopView {
  state: LoopState;
  history: { ts: string; state: LoopState; to?: string; actor_role: string; skipped?: LoopState[] }[];
  states?: LoopState[];
  timer?: { required: boolean; deadline: string | null; booked_at: string | null; overdue: boolean; simulated: true };
}

export interface CounselorSession {
  token: string;
  counselor_id: string;
  scopes: string[];
  expires_in: number;
  on_shift: boolean;
}

/** api.md v1.3.0 (DECISIONS #62): counselor-only AI draft. Never stored on the case, never sent to a patient. */
export interface GateViolation {
  rule: string;
  detail: string;
}
export interface SummaryDraft {
  /** Absent/null when the gate blocked the draft: the violations are returned instead of text. */
  draft: string | null;
  provider: "sarvam" | "offline-stub" | string;
  model: string;
  generated_at: string;
  ai_generated: true;
  gate: { passed: boolean; violations: GateViolation[] };
  input_fields: string[];
}
export interface AppConfig {
  ai_draft_enabled: boolean;
  provider: string;
  environment: "local" | "vm" | "vercel-render" | string;
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
