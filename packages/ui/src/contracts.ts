// Structural types mirroring contracts/risk_output.schema.json v1.1.0 and contracts/api.md v1.2.0.
// The design system only *renders* these; it never computes from them (P-01, P-02).

export type Scenario =
  | "concordant_positive"
  | "discordant"
  | "concordant_negative"
  | "shared_vus_roh"
  | "atypical_genotype";

export type Reason =
  | "missing_carrier_freq"
  | "missing_detection_rate"
  | "shared_vus_roh"
  | "atypical_genotype"
  | "related_concordant_negative"
  | "perfect_detection"
  | "not_in_panel"
  | null;

/** Locked RiskOutput: the ONLY numeric source for user-facing text. */
export interface RiskOutput {
  contract_version: "1.1.0";
  gene: string;
  hgnc_id: number;
  scenario: Scenario;
  status: "ok" | "needs_counselor";
  fusage: "genome_wide_context_only";
  F?: number | null;
  prior_carrier_b?: number | null;
  posterior_carrier_b?: number;
  posterior_carrier_b_one_in?: string | null;
  detection_rate?: number | null;
  offspring_risk?: number | null;
  offspring_risk_one_in?: string | null;
  relative_to_unrelated?: number | null;
  reference_unrelated_one_in?: string | null;
  escalate?: boolean;
  digest: string;
  audience: "couple" | "carrier_partner_only" | "counselor_only";
  carrier_role?: "A" | "B" | null;
  reason: Reason;
  relative_to_unrelated_display?: string | null;
}

/** Fields LockedNumber may render. */
export type LockedField =
  | "offspring_risk_one_in"
  | "posterior_carrier_b_one_in"
  | "reference_unrelated_one_in"
  | "relative_to_unrelated_display"
  | "detection_rate"
  | "offspring_risk"
  | "F";

export type LoopState =
  | "ResultIssued"
  | "PatientNotified"
  | "ComprehensionConfirmed"
  | "ConfirmatoryDone"
  | "CounselingDone"
  | "ReproReferralDone"
  | "HumanClosure";

export const LOOP_STATES: readonly LoopState[] = [
  "ResultIssued",
  "PatientNotified",
  "ComprehensionConfirmed",
  "ConfirmatoryDone",
  "CounselingDone",
  "ReproReferralDone",
  "HumanClosure",
] as const;

export type CoupleStatus = "not_linked" | "invited" | "both_consented" | "result_ready";
export type Visibility = "only_you" | "you_and_counselor" | "couple";
