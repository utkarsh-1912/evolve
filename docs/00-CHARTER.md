# 00 — Charter: scope, requirements, success metrics

## Problem (from source §Intro, §1)
Mandatory premarital WGS (570 genes, >840 AR conditions) finds couple-level risk in ~4.8% of couples (565/11,748). Bottlenecks: (1) 52% of Emirati P/LP variants absent from gnomAD, 30% from ClinVar; (2) naive result-sharing leaks discordant carrier status; (3) pipelines ignore consanguinity and assay residual risk. Screening only has impact if people **understand** results and **reach** counseling/care.

## Goal
Demonstrate, on **synthetic** Emirati-calibrated data, a working end-to-end prototype that: computes risk correctly, shares only what is consented, explains it non-directively in Arabic/English, and closes the loop to human care.

## Requirements (IDs are the scope boundary — guardrail G-01)
| ID | Requirement | Source § | Owner agent |
|---|---|---|---|
| R-DATA-1 | 1,000-couple synthetic cohort (source-realistic relationship mix, ≤50% consanguineous; concordance reported, not forced — DECISIONS #10) calibrated to Emirati carrier freqs (CYP21A2 10.6, HBB 9.6, MEFV 5.9, ABCA4 4.3, HBA2 1.8, SMN1 1.3, DONSON 1.0, ALDH3A2 0.6 %) | 2.1, Roadmap 1 | data-synth |
| R-DATA-2 | Five canonical vignettes (V1–V5) as fixtures | 2.4 | data-synth |
| R-DATA-3 | Novelty-gap simulation among non-founder (synthetic) P/LP variants (~52% not in gnomAD, ~30% not in ClinVar); documented founder variants never flagged — DECISIONS #12 | 2.1 | data-synth |
| R-FHIR-1 | FHIR R4 GenomicReport bundle + GA4GH Phenopacket v2 + Pedigree output, validated, zero dangling refs | 2.2, 3.1 | fhir-interop |
| R-RISK-1 | Wright R and F incl. ancestor-inbreeding term, multi-path | 2.3 | risk-engine |
| R-RISK-2 | Bayesian residual risk (concordant / discordant / concordant-negative) with assay detection rate | 2.3 | risk-engine |
| R-RISK-3 | Locked immutable risk JSON; 0.0% arithmetic error on all 1,000 couples | 4.1 A3, §5 | risk-engine |
| R-PRIV-1 | APSI: authority-signed gene sets, empty-intersection = "Compatible", only intersecting genes revealed | 3.2 | privacy-apsi |
| R-PRIV-2 | FHIR Consent (both partners, time-scoped, revocable), revocation purges couple state | 3.3, A1 | privacy-apsi |
| R-PRIV-3 | SMART-on-FHIR-v2-style scopes (patient/, user/, system/), PKCE, ≤1h tokens, AuditEvent for every access | 3.3 | privacy-apsi |
| R-PRIV-4 | Single-locus Cascade Screening Token (no index identity) | 3.2 | privacy-apsi |
| R-AGT-1 | Seven runtime agents with tool bindings per spec | 4.1 | agent-runtime |
| R-AGT-2 | BioethicsSupervisor four-rule outbound gate (numeric drift, leakage, non-coercion/judicial decoupling, UAE statutes) | 4.1 A6 | agent-runtime |
| R-AGT-3 | CounselorCopilot escalation triggers (a)–(d) + Consultation Brief | 4.1 A7 | agent-runtime |
| R-AGT-4 | CareNavigator ART/Thiqa eligibility checks (age, BMI, immediate eligibility) | 4.1 A5 | agent-runtime |
| R-UX-1 | Bilingual (AR RTL / EN) citizen app: private vault, consent, compatibility result, teach-back, care tracker | 4.1 A4, 3.4 | ui-frontend |
| R-UX-2 | Counselor console: consented couple view, pedigree, brief, tasks | 3.3, A7 | ui-frontend |
| R-UX-3 | Closed-loop state machine view (7 states) | 3.4 | ui-frontend |
| R-EVAL-1 | Five-dimension evaluation harness + dashboard (MMIC, GCOS-24/GOS, SURE/DCS, loop velocity, calibration, leakage/red-team) | §5 | qa-redteam |
| R-EVAL-2 | Red-team suite: leakage, directive advice, unlawful reproductive advice | §5 | qa-redteam |
| R-DEMO-1 | 5-minute scripted demo over V1–V5 + pitch deck | — | docs-demo |

## Explicitly OUT of scope (guardrail G-02)
Real genomic/PHI data · real Malaffi/SEHA/M42 integration (simulate behind adapters, labelled) · variant calling/bioinformatics pipeline · diagnosis or treatment advice · embryo selection / sex selection · donor-gamete options · abortion advice · marriage recommendation of any kind · payments · social/sharing features · any metric based on marriage outcomes · extra agents or extra genes beyond the doc without orchestrator approval.

## Success metrics (source §5 — used verbatim by qa-redteam)
1. ≥85% comprehension (carrier≠diagnosis, 25% recurrence, residual risk); GCOS-24/GOS delta p<0.01 (simulated cohort, stated as simulated).
2. ≥90% SURE 4/4 post-counseling; 0 coercion/directive flags.
3. 100% incompatible couples booked ≤48h; ≥95% confirmatory tasks completed.
4. 0.0% arithmetic error across 1,000 couples; 0 FHIR/Phenopacket validation errors.
5. 0.0% unauthorized leakage under red-team; 100% directive/unlawful advice interception.
**Honesty rule:** metrics 1–3 are measured on simulated users; every chart says "simulated". Do not present them as clinical findings.

## Hackathon "wow" budget (allowed polish, ranked)
1. Live APSI demo (V4: A has 2 variants, B has 1, UI shows only "Compatible").
2. Guardrail block panel (BioethicsSupervisor rejecting a drafted directive/leaky/numerically-drifting message, shown live).
3. V3 SMN1 "false reassurance prevented" explainer with locked-number overlay.
