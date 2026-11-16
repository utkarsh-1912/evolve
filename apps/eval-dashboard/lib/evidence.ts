// Typed view of the evidence pack (services/eval/out/evidence.json, qa-redteam) and of the cohort views
// derived by scripts/sync_evidence.py. Both JSON files are generated: never edit them, never type numbers here.
import type { RiskOutput } from "@evolve/ui";
import evidenceJson from "@/data/evidence.json";
import cohortJson from "@/data/cohort.json";

export interface Share {
  k: number;
  n: number;
  value: number;
  ci95: [number, number];
}

export interface RedteamSet {
  adversarial: { n: number; intercepted: number; rate: number };
  benign: { n: number; false_positives: number; fp_rate: number };
  categories: Record<string, { n: number; ok: number; pass_rate: number; en: string; ar: string; wrong_rule: number }>;
}

export interface HoldoutSet {
  name: string;
  measured: string;
  catch: number;
  fp: number;
  meets_target: boolean;
}

export interface SuiteResult {
  tests: number;
  passed: number;
  failed: number;
  errors: number;
  skipped: number;
  status: "green" | "red";
  junit_mtime: string;
}

export interface PrivacyRow {
  category: string;
  n: number;
  intercepted: Share;
  leaks: Share;
}

export interface Evidence {
  simulated: boolean;
  label: string;
  disclaimer: string;
  build: { utc: string; contracts_sha256: string };
  contract_versions: Record<string, string | null>;
  persona_runs: {
    n: number;
    per_stratum: number;
    strata: number;
    seed: number;
    harness_problems: unknown[];
    model_assumptions: Record<string, unknown>;
  };
  dimensions: {
    comprehension: {
      first_attempt_pass: Share;
      final_pass: Share;
      per_item: Record<string, Share>;
      by_stratum: Record<string, Share>;
      gcos: { instrumented: boolean; n: number; mean_shift: number | null; p_value: number | null };
      meets: boolean;
      simulated: boolean;
    };
    informed_choice: { sure_full: Share; by_stratum: Record<string, Share>; coercion_flags: number; meets: boolean; simulated: boolean };
    loop_velocity: { booked_within_48h: Share; confirmatory_completed: Share; late_or_unbooked: unknown[]; meets: boolean; simulated: boolean };
    calibration: { records_checked: number; arithmetic_mismatches: number; arithmetic_error_share: Share; fhir_errors: number; meets: boolean; simulated: boolean };
    privacy: {
      interception: Share;
      redteam_leaks: number;
      live_responses_scanned: number;
      live_leaks: number;
      live_leak_share: Share;
      table: PrivacyRow[];
      meets: boolean;
      simulated: boolean;
    };
  };
  thresholds: {
    comprehension_share: number;
    gcos_p_value_below: number;
    sure_full_share: number;
    coercion_flags_max: number;
    booked_within_48h_share: number;
    confirmatory_completed_share: number;
    arithmetic_mismatches_max: number;
    fhir_errors_max: number;
    leaks_max: number;
    interception_share: number;
  };
  calibration_detail: {
    couples: number;
    records: number;
    numeric_records: number;
    mismatches: number;
    fhir_counts: Record<string, number>;
    cohort_seed: number;
  };
  /** Keyed by set name; keys changed between packs (v1/holdout -> regression_corpus/holdout_current). */
  redteam: Record<string, RedteamSet>;
  g2: {
    decision: string;
    /** Current shape (pack 2026-11-15+): one entry per held-out set, retired and current (REQUEST-DD-1). */
    c_holdout_sets?: HoldoutSet[];
    target?: { catch_min: number; fp_max: number };
    two_sets_meet_target?: boolean;
    holdout_pass_marker_exists?: boolean;
    llm_paraphrase_may_be_enabled?: boolean;
    blocks_g2?: boolean;
    /** Legacy shape (pack 2026-11-09): a single held-out set. Read only as a fallback. */
    c_holdout?: {
      catch: number;
      fp: number;
      target: { catch_min: number; fp_max: number };
      meets_target: boolean;
      blocks_g2: boolean;
      llm_paraphrase_may_be_enabled: boolean;
      note: string;
    };
  };
  guardrail_feed: { by_rule: Record<string, { blocked: number; rewritten: number; escalated: number; passed: number }> };
  tests: Record<string, SuiteResult>;
  guardrail_check: { ok: boolean; violations: unknown[] };
  simulated_vs_real: { item: string; source: string; simulated: boolean | null }[];
  /** Added 2026-11-16 (NOTE-EVIDENCE-SCHEMA); null/absent in older packs. */
  gate3?: { source: string; date: string; passed: boolean; p0: number; suites: { app: string; config: string; passed: number; failed: number }[]; not_covered: string[] } | null;
}

export interface HistogramBin {
  record: RiskOutput;
  count: number;
  scenarios: string[];
  vignettes: string[];
}

export type CohortCategory = "concordant_positive" | "discordant_needs_counselor" | "discordant_computed" | "no_shared_finding";

export interface CohortViews {
  simulated: boolean;
  generated_utc: string;
  sources: { evidence_sha256: string; cohort_sha256: string; cohort_seed: number; cohort_contract_version: string };
  couples: number;
  records: number;
  records_not_computed: number;
  categories: CohortCategory[];
  category_counts: Record<CohortCategory, number>;
  category_related_counts: Record<CohortCategory, number>;
  /** [category index, related 0/1] per couple, grouped by category. */
  grid: [number, number][];
  histogram: HistogramBin[];
}

export const evidence = evidenceJson as unknown as Evidence;
export const cohort = cohortJson as unknown as CohortViews;

/** Held-out sets as the pack reports them; falls back to the legacy single-set shape. */
export function holdoutSets(): HoldoutSet[] {
  const g = evidence.g2;
  if (g.c_holdout_sets) return g.c_holdout_sets;
  if (g.c_holdout) return [{ name: "holdout", measured: "", catch: g.c_holdout.catch, fp: g.c_holdout.fp, meets_target: g.c_holdout.meets_target }];
  return [];
}

export function gateTarget(): { catch_min: number; fp_max: number } | null {
  return evidence.g2.target ?? evidence.g2.c_holdout?.target ?? null;
}
