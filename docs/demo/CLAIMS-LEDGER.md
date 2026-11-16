# évolvé: claims ledger (R-DEMO-1, G5)

Every number and factual claim used in README.md, docs/demo/DEMO-SCRIPT.md, PITCH-OUTLINE.md and JUDGE-QA.md, with its source.

Abbreviations:
- `src §x` = docs/source/architecture-source.txt
- `pack:` = a field path in services/eval/out/evidence.json (build 2026-11-15T06:03:03Z)
- `DONE-*` = handoffs/DONE-*.md

A claim that is not in this table should not be said.

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
| Statutes: Fed. Law 11/2008, Fed. Law 7/2019, Art. 16 Medical Liability Law, Cabinet Res. 44/2024. Framed as "designed to comply with, pending legal review" | src §4.1 Agent 6; P-16, P-20 |
| Carrier frequencies (CYP21A2 10.6% … ALDH3A2 0.6%) | src §2.1 table; src Roadmap |
| Success targets: ≥85% comprehension, ≥90% SURE 4/4, 100% booked ≤48 h, ≥95% confirmatory, 0.0% arithmetic error, 0.0% leakage, 100% interception | src §5; docs/00 |

## Risk numbers (locked, deterministic)
| Claim | Source |
|---|---|
| V1 HBB "1 in 4" | docs/07 §3 golden vectors; DONE-P1-RE; live API 2026-11-09 |
| V2 CYP21A2 "1 in 426" (posterior 1 in 106) | src §2.4 V2; docs/07 §3; DONE-P1-RE |
| V3 SMN1 "1 in 321" vs "1 in 3,800", "about 12x", residual carrier "1 in 80.2" | src §2.4 V3; docs/07 §3; DONE-P1-RE; live API 2026-11-09 |
| Detection rate 92% (0.92), inferred from the source outputs, TODO(verify) | DECISIONS #1 |
| F = 0.0625, first cousins, shown as genome-wide context only | docs/07 §1; live brief 2026-11-09; DONE-P3-UI-CNS (live run); P-03 |
| 0 arithmetic mismatches / 629 records over 1,000 couples + V1–V5 | pack: `dimensions.calibration`; DONE-P4-QA-EVAL |
| 0 FHIR/Phenopacket errors (our harness) | pack: `dimensions.calibration`; DONE-P1-FH |
| HL7 validator CLI: 18 → 8 errors; the 8 are tx.fhir.org timeouts (inconclusive) | DECISIONS #42; DONE-P4-FH |
| Cohort concordance 3.40% (CI 2.44–4.71%), 8-gene floor | DONE-P1-DS2; DECISIONS #22 |
| Cohort grid: 34 same-gene · 325 one carrier, counselor · 124 one carrier, calculated · 517 no finding | DONE-P4-UI-EVAL (data from risk_engine over the cohort) |

## Safety gate and red team
| Claim | Source |
|---|---|
| Patient text = closed set of pre-approved templates; LLM paraphrase hard-off | DECISIONS #37, #49 |
| Template closure: 25,692 template × record combinations, 0 failures (98 templates; V1–V5 + 1,000 couples, EN + AR) | DONE-P4-GATE; DECISIONS #45, #51 |
| 17 "no free-text path to patients" tests pass | DONE-P4-GATE; DECISIONS #45, #51 |
| G2 PASSED as redefined (closure + no free text + honest held-out tracking) | DECISIONS #51 |
| Held-out v2 (current, never seen by the gate author): 113/181 = 62.4% caught, 2/43 = 4.7% FP | pack: `redteam` holdout_current; DONE-P4-QA-HOLDOUT2 |
| Held-out v1 final (retired): 89.6% caught, 2.3% FP; round 1 was 65.3% / 15.9% | DONE-P4-QA-HOLDOUT2; DONE-P2-QA-HOLDOUT |
| Target ≥95% / ≤5% on two fresh sets is NOT met; LLM mode stays off | pack: `g2`; DECISIONS #49 |
| Regression corpus 540/540 (433/433 adversarial, 0/93 FP), after gate round 3 | DECISIONS #51 (orchestrator re-run). Note: the pack (06:03Z) predates this and still shows 413/433 |
| Live API leakage scan: 0 leaks / 2,491 responses | pack: `dimensions.privacy` |
| Leakage drafts passed by the gate across red-team sets: 17 | pack: `dimensions.privacy` |
| Demo probes: directive draft → `directive`; "1 in 50" → `numeric_drift`; MEFV draft to V4B → `leakage`; donor → `uae_law`; "1 in 321" control → passes after V3 is staged | live API 2026-11-09 (scripts/demo/gate_probe.py); DONE-P4-UI-EVAL live spec |

## Simulated metrics (always said with "SIMULATED")
| Claim | Source |
|---|---|
| Teach-back first attempt 62.1% (149/240), target ≥85%, not met; 92.1% after one re-explanation | pack: `dimensions.comprehension` |
| SURE 4/4 87.1% (209/240), target ≥90%, not met; 0 coercion flags | pack: `dimensions.informed_choice` |
| 100% (39/39) trigger-(a) couples booked ≤48 h; 98.9% (91/92) confirmatory Tasks completed | pack: `dimensions.loop_velocity` (SIMULATED clock) |
| These verdicts are artifacts of fixed response-model assumptions, not findings | pack: `simulated_vs_real`; DECISIONS #43 |
| GCOS-24/GOS: not instrumented, no value invented | pack: `dimensions.comprehension`; DECISIONS #43 |
| 240 persona runs (10 × 24 strata, seed 42) | pack: `persona_runs` |

## Tests (pack: `tests`, build 2026-11-15T06:03:03Z)
| Claim | Source |
|---|---|
| risk_engine 76/76 · privacy 44/44 · fhir 49/49 · synth 21/21 · api 27/27 · agents 341/341 · loop 8/8 · integration 28/28 · eval 20/20 · guardrail-script 3/3 | pack: `tests` |
| Later runs: api 28, agents 369, integration 28 | DECISIONS #53 |
| Red-team v1 corpus 518/540 in the pack (red) → 540/540 after gate round 3 | pack: `tests.qa_redteam_v1`; DECISIONS #51 |
| Held-out 158/230 (red on purpose; tracked, not a blocker) | pack: `tests.qa_redteam_holdout` |
| Citizen e2e live 21 passed; axe 0 serious on every route EN + AR | DONE-P3-UI-CIT |
| Citizen JS budget ≤180 kB gz NOT met (210–264 kB); Lighthouse not run | DONE-P3-UI-CIT |
| Counselor: 27 Playwright (mock) + 2 live; 48 axe checks 0 serious | DONE-P3-UI-CNS; DECISIONS #50 |
| Eval dashboard: 17 Playwright; axe 0 | DONE-P4-UI-EVAL |
| `guardrail_check: OK` | pack: `guardrail_check`; re-run by docs-demo 2026-11-16 |

## Product and privacy claims
| Claim | Source |
|---|---|
| APSI = RSA-FDH authority signatures + DH-commutative PSI, RFC 3526 2048-bit | DECISIONS #5; DONE-P1-PA |
| Limits: semi-honest only, set sizes revealed, keys in memory | services/privacy/THREAT_MODEL.md; DONE-P1-PA |
| Revocation purges the couple workspace, ≤5 s, tested | P-07; DONE-P1-PA; DONE-P2-QA |
| Uniform counselor notice for every partner (no differential notice) | DECISIONS #27 |
| Counselor shift defaults off; case data only on shift | DECISIONS #40, #53 |
| Only a counselor can document human closure | DONE-P3-UI-CNS; src §3.4 |
| CareTimeline shows jumped-over states as "Skipped", never done | DECISIONS #50; DONE-P3-UI-CIT |
| Arabic patient copy: 71 strings, TODO(native-review); counselor and eval Arabic are placeholders | DECISIONS #48, #50; DONE-P4-AR-ARABIC |
| Integrations (Malaffi, SEHA, Thiqa, Judicial) are SIMULATED adapters | docs/00 out of scope; pack: `simulated_vs_real` |
| Roadmap S0–S4 and kill criteria | docs/05 §4 |

## Removed or reworded during the audit
- The P4 wording "the gate blocks 65% of attacks" was replaced with the current v2 figure (62.4%) plus the closed-template guarantee, which now carries the safety claim (DECISIONS #37/#49).
- "100% interception" never appears as an achievement, only as a source target.
