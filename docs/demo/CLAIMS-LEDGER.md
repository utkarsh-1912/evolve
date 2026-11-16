# évolvé: claims ledger (R-DEMO-1, G5)

Every number and factual claim used in README.md, docs/demo/DEMO-SCRIPT.md, PITCH-OUTLINE.md and JUDGE-QA.md, with a source **inside this repo**.

Abbreviations:
- `src §x` = docs/source/architecture-source.txt
- `pack:` = a field in `apps/eval-dashboard/data/evidence.json`. This is the evidence pack, build 2026-11-16T02:09:47Z, a byte-identical copy of `services/eval/out/evidence.json`, which is a generated output.
- `D#n` = docs/DECISIONS.md entry n.

A claim not in this table should not be said.

## Problem and context (source document)
| Claim | Source |
|---|---|
| 570 genes, >840 autosomal recessive conditions, 30X WGS | src Intro |
| 565 of 11,748 couples incompatible, ≈4.8% (4.81%) | src Intro; src §1 |
| 13.1% (143/1,094) in the NEJM cohort, an enriched early cohort, not comparable with 4.8% | src §1 |
| 52% of Emirati P/LP variants absent from gnomAD; 30% absent from ClinVar | src Intro; src §2.1 |
| Up to 78% carry ≥1 recessive variant; 4.8%–13.1% of couples share one | src §3.2 |
| Certificate issued and sent to the Judicial Department regardless of result | src §1; src §3.4 |
| A single LLM can hallucinate probabilities, leak across partners and drift directive | src §4 |
| Escalation triggers (a)–(d) | src §4.1 Agent 7 |
| Statutes: Fed. Law 11/2008, Fed. Law 7/2019, Art. 16 Medical Liability Law, Cabinet Res. 44/2024. Always framed as "designed to comply with, pending legal review" | src §4.1 Agent 6; docs/01 P-16, P-20 |
| Carrier frequencies (CYP21A2 10.6% … ALDH3A2 0.6%) | src §2.1 table; contracts/gene_panel.json |
| Success targets: ≥85% comprehension, ≥90% SURE 4/4, 100% booked ≤48 h, ≥95% confirmatory, 0.0% arithmetic error, 0.0% leakage, 100% interception | src §5; docs/00 |

## Risk numbers (locked, deterministic)
| Claim | Source |
|---|---|
| V1 HBB "1 in 4"; V2 CYP21A2 "1 in 426" (posterior 1 in 106); V3 SMN1 "1 in 321" vs "1 in 3,800", "about 12x", residual carrier "1 in 80.2" | src §2.4; docs/07 §3; tests/golden/risk_vectors.json; services/risk_engine/tests/test_assess.py |
| Detection rate 92% (0.92), inferred from the source outputs, TODO(verify) | D#1; contracts/gene_panel.json |
| F = 0.0625 (first cousins), genome-wide context only | docs/07 §1; tests/golden/risk_vectors.json; docs/01 P-03 |
| 0 arithmetic mismatches / 629 records over 1,000 couples + V1–V5 (two independent oracles) | pack `dimensions.calibration`; tests/_support/oracle.py; tests/integration/test_cross_package.py; services/risk_engine/tests/test_cohort_sweep.py |
| 0 FHIR/Phenopacket errors (our harness, 1,000 couples) | pack `dimensions.calibration`; services/fhir/tests/test_fhirgen.py |
| HL7 validator CLI: 8 remaining errors, all tx.fhir.org timeouts (inconclusive) | D#42 |
| Cohort concordance 3.40% (CI 2.44–4.71%), 8-gene floor | D#22 |
| Cohort grid: 34 same-gene · 325 one carrier, counselor · 124 one carrier, calculated · 517 no finding | apps/eval-dashboard/data/cohort.json |

## Safety gate and red team
| Claim | Source |
|---|---|
| Patient text = closed set of pre-approved templates; LLM paraphrase hard-off | D#37, D#49 |
| Template closure: 25,692 template × record combinations, 0 failures (EN + AR, full cohort) | D#45, D#51; services/agents/tests/test_templates_closure.py |
| 17 "no free-text path to patients" tests pass | D#45, D#51; services/agents/tests/test_templates_no_free_text.py |
| G2 PASSED as redefined | D#51 |
| Held-out v2 (current, unseen): 113/181 = 62.4% caught, 2/43 = 4.7% FP | pack `g2.c_holdout_sets[holdout_current]`; tests/guardrails/reports/holdout_last_run.json |
| Held-out v1: round 1 65.3% / 15.9% FP → final 89.6% / 2.3% FP (retired) | tests/guardrails/reports/retired/holdout_v1_round1and2_final.json; pack `g2`; D#37, D#49 |
| Target ≥95% / ≤5% on two fresh sets NOT met; LLM mode stays off | pack `g2` (`two_sets_meet_target=false`, `llm_paraphrase_may_be_enabled=false`); D#49 |
| Regression corpus 433/433 adversarial, 0/93 FP | pack `redteam` (regression_corpus); tests/guardrails/reports/corpus_last_run.json; D#51 |
| Red-team interception across v1 + held-out: 88.9% (546/614); 15 leakage drafts passed the gate | pack `dimensions.privacy` |
| Live API leakage scan: 0 leaks / 2,491 responses | pack `dimensions.privacy` |
| Demo probes: directive → `directive`; "1 in 50" → `numeric_drift`; MEFV draft to V4B → `leakage`; donor → `uae_law`; "1 in 321" control passes after V3 is staged | scripts/demo/gate_probe.py (re-run 2026-11-16); apps/eval-dashboard/e2e/; tests/e2e/cross_app_smoke.spec.ts |

## Simulated metrics (always said with "SIMULATED")
| Claim | Source |
|---|---|
| Teach-back first attempt 62.1% (149/240), target ≥85%, not met; 92.1% after one re-explanation | pack `dimensions.comprehension` |
| SURE 4/4 87.1% (209/240), target ≥90%, not met; 0 coercion flags | pack `dimensions.informed_choice` |
| 100% (39/39) booked ≤48 h; 98.9% (91/92) confirmatory Tasks completed | pack `dimensions.loop_velocity` (SIMULATED clock) |
| These verdicts are artifacts of fixed response-model assumptions | pack `simulated_vs_real`, `persona_runs.model_assumptions`; D#43 |
| GCOS-24/GOS: not instrumented, no value invented | pack `dimensions.comprehension`; D#43 |
| 240 persona runs (10 × 24 strata, seed 42) | pack `persona_runs` |

## Tests
| Claim | Source |
|---|---|
| risk_engine 85 · privacy 44 · fhir 49 · synth 21 · loop 8 · integration 28 · eval 20 · guardrail-script 3, all passing | pack `tests`; D#61 |
| api 32 passed + 8 skipped (paused AI-draft tests) | D#64 |
| agents 369 passed (default run) + the slow full-cohort closure run separately | D#61 |
| Held-out suite red on purpose (158/230); tracked, not a blocker | pack `tests.qa_redteam_holdout`; D#49 |
| Gate 3 E2E passed, 0 P0: citizen live 21 · counselor 27 + 2 live · eval 17 · cross-app smoke 1 | tests/e2e/reports/gate3_last_run.json; D#57 |
| axe: 0 serious on every route EN + AR (citizen); 48 checks (counselor); 0 (eval) | D#50, D#57, D#59; apps/*/e2e/a11y.spec.ts |
| Citizen JS budget ≤180 kB gz NOT met (210–265 kB); Lighthouse not run | D#59; apps/citizen/e2e/budget.spec.ts |
| `guardrail_check: OK` | pack `guardrail_check`; scripts/guardrail_check.py |

## Product and privacy claims
| Claim | Source |
|---|---|
| APSI = RSA-FDH authority signatures + DH-commutative PSI, RFC 3526 2048-bit | D#5; services/privacy/THREAT_MODEL.md |
| Limits: semi-honest only, set sizes revealed, keys in memory | services/privacy/THREAT_MODEL.md |
| Revocation purges the couple workspace, ≤5 s, tested | docs/01 P-07; services/privacy/tests/; tests/integration/test_api_isolation.py |
| Uniform counselor notice for every partner | D#27; contracts/api.md |
| Counselor shift defaults off; case data only on shift | D#40, D#53 |
| CareTimeline shows jumped-over states as "Skipped" | D#50 |
| Arabic patient copy: 71 strings, TODO(native-review); counselor and eval Arabic are placeholders | D#48, D#50 |
| Counselor AI draft (Sarvam): built, paused (`ai_draft_enabled=false`), counselor-side, English only, never patient-facing | D#62, D#63, D#64; contracts/api.md v1.3.0 |
| Integrations (Malaffi, SEHA, Thiqa, Judicial) are SIMULATED adapters | docs/00 out of scope; pack `simulated_vs_real` |
| Roadmap S0–S4 and kill criteria | docs/05 §4 |
| Deployment: two targets, one switch | D#62, D#64; docs/demo/DEPLOY.md |

## Removed or reworded during the audit
- The gate's held-out figure is the current v2 (62.4%). The safety claim rests on closed templates (D#37/#49).
- "100% interception" appears only as a source target.
- Internal build-process cards are not published, so no claim cites them. Each was repointed to a repo file or a DECISIONS entry.
