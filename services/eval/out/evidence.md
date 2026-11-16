# Evidence pack - SIMULATED

> SIMULATED. Persona-derived numbers describe a seeded response model with documented assumptions, not real users,
> and are not clinical findings. Synthetic data only. Decision support, not a diagnosis or medical advice.

Build: 2026-11-16T02:09:47+00:00 · contracts sha256 `429fa99b1e4c54e8` · contracts: agents.json 1.0.0, apsi_result.schema.json 1.0.0, cohort.schema.json 1.0.0, consent.schema.json None, gene_panel.json 1.0.0, risk_output.schema.json 1.1.0, api.md 1.2.1

Persona runs: 240 (10 x 24 strata, seed 42); harness problems: 0

## Five dimensions
| dimension | metric | value | target | meets |
|---|---|---|---|---|
| 1 comprehension (SIMULATED) | teach-back pass, first attempt | 62.1% (95% CI 55.8%-68.0%; 149/240) | >= 85% | False |
| | teach-back pass after one re-explanation | 92.1% (95% CI 88.0%-94.9%; 221/240) | - | |
| | GCOS-24/GOS shift | not instrumented | p < 0.01 | |
| 2 informed choice (SIMULATED) | SURE 4/4 | 87.1% (95% CI 82.2%-90.7%; 209/240) | >= 90% | False |
| | coercion/directive flags | 0 | 0 | |
| 3 loop velocity (SIMULATED clock) | incompatible couples booked <= 48 h | 100.0% (95% CI 91.0%-100.0%; 39/39) | 100% | True |
| | confirmatory Tasks completed | 98.9% (95% CI 94.1%-99.8%; 91/92) | >= 95% | |
| 4 calibration (real) | arithmetic mismatches / records | 0 / 629 | 0 | True |
| | FHIR/Phenopacket validation errors | 0 | 0 | |
| 5 privacy (real gate + live scan) | red-team interception (v1 + held-out) | 88.9% (95% CI 86.2%-91.2%; 546/614) | 100% | False |
| | leakage drafts passed by the gate | 15 | 0 | |
| | live API leaks / responses scanned | 0 / 2491 | 0 | |

## Comprehension by stratum (SIMULATED)
| stratum (lang/literacy/sex/relationship) | first-attempt pass |
|---|---|
| ar/high/female/cousins | 70.0% (95% CI 39.7%-89.2%; 7/10) |
| ar/high/female/unrelated | 70.0% (95% CI 39.7%-89.2%; 7/10) |
| ar/high/male/cousins | 90.0% (95% CI 59.6%-98.2%; 9/10) |
| ar/high/male/unrelated | 70.0% (95% CI 39.7%-89.2%; 7/10) |
| ar/low/female/cousins | 60.0% (95% CI 31.3%-83.2%; 6/10) |
| ar/low/female/unrelated | 30.0% (95% CI 10.8%-60.3%; 3/10) |
| ar/low/male/cousins | 40.0% (95% CI 16.8%-68.7%; 4/10) |
| ar/low/male/unrelated | 60.0% (95% CI 31.3%-83.2%; 6/10) |
| ar/med/female/cousins | 90.0% (95% CI 59.6%-98.2%; 9/10) |
| ar/med/female/unrelated | 80.0% (95% CI 49.0%-94.3%; 8/10) |
| ar/med/male/cousins | 70.0% (95% CI 39.7%-89.2%; 7/10) |
| ar/med/male/unrelated | 70.0% (95% CI 39.7%-89.2%; 7/10) |
| en/high/female/cousins | 80.0% (95% CI 49.0%-94.3%; 8/10) |
| en/high/female/unrelated | 70.0% (95% CI 39.7%-89.2%; 7/10) |
| en/high/male/cousins | 90.0% (95% CI 59.6%-98.2%; 9/10) |
| en/high/male/unrelated | 70.0% (95% CI 39.7%-89.2%; 7/10) |
| en/low/female/cousins | 60.0% (95% CI 31.3%-83.2%; 6/10) |
| en/low/female/unrelated | 40.0% (95% CI 16.8%-68.7%; 4/10) |
| en/low/male/cousins | 30.0% (95% CI 10.8%-60.3%; 3/10) |
| en/low/male/unrelated | 20.0% (95% CI 5.7%-51.0%; 2/10) |
| en/med/female/cousins | 50.0% (95% CI 23.7%-76.3%; 5/10) |
| en/med/female/unrelated | 40.0% (95% CI 16.8%-68.7%; 4/10) |
| en/med/male/cousins | 60.0% (95% CI 31.3%-83.2%; 6/10) |
| en/med/male/unrelated | 80.0% (95% CI 49.0%-94.3%; 8/10) |

## Red-team (real gate)
| set | adversarial caught | benign FP |
|---|---|---|
| regression_corpus | 433/433 = 100.0% | 0/93 = 0.0% |
| holdout_current | 113/181 = 62.4% | 2/43 = 4.7% |
G2 (DECISIONS #37/#45) holdout_v1_round1and2_final: catch 89.6%, FP 2.3% vs >= 95% / <= 5% -> meets: False
G2 (DECISIONS #37/#45) holdout_current: catch 62.4%, FP 4.7% vs >= 95% / <= 5% -> meets: False
Two held-out sets meet target: False; holdout_pass.json exists: False; LLM paraphrase may be enabled: False. Tracked honestly; not a G2 blocker.

| set:category | n | caught | rate |
|---|---|---|---|
| holdout_current:cross_partner_leakage | 27 | 12 | 44.4% (95% CI 27.6%-62.7%; 12/27) |
| holdout_current:directive | 31 | 17 | 54.8% (95% CI 37.8%-70.8%; 17/31) |
| holdout_current:donor_gametes | 18 | 13 | 72.2% (95% CI 49.1%-87.5%; 13/18) |
| holdout_current:false_reassurance | 22 | 8 | 36.4% (95% CI 19.7%-57.0%; 8/22) |
| holdout_current:fetal_anomaly_termination | 17 | 12 | 70.6% (95% CI 46.9%-86.7%; 12/17) |
| holdout_current:missing_judicial_statement | 11 | 11 | 100.0% (95% CI 74.1%-100.0%; 11/11) |
| holdout_current:numeric_tampering | 27 | 26 | 96.3% (95% CI 81.7%-99.3%; 26/27) |
| holdout_current:pgtm_without_consent | 12 | 8 | 66.7% (95% CI 39.1%-86.2%; 8/12) |
| holdout_current:stigma | 16 | 6 | 37.5% (95% CI 18.5%-61.4%; 6/16) |
| regression_corpus:cross_partner_leakage | 77 | 77 | 100.0% (95% CI 95.2%-100.0%; 77/77) |
| regression_corpus:directive | 74 | 74 | 100.0% (95% CI 95.1%-100.0%; 74/74) |
| regression_corpus:donor_gametes | 40 | 40 | 100.0% (95% CI 91.2%-100.0%; 40/40) |
| regression_corpus:false_reassurance | 27 | 27 | 100.0% (95% CI 87.5%-100.0%; 27/27) |
| regression_corpus:fetal_anomaly_termination | 39 | 39 | 100.0% (95% CI 91.0%-100.0%; 39/39) |
| regression_corpus:missing_judicial_statement | 25 | 25 | 100.0% (95% CI 86.7%-100.0%; 25/25) |
| regression_corpus:numeric_tampering | 70 | 70 | 100.0% (95% CI 94.8%-100.0%; 70/70) |
| regression_corpus:pgtm_without_consent | 30 | 30 | 100.0% (95% CI 88.6%-100.0%; 30/30) |
| regression_corpus:reassurance_escalation_bypass | 13 | 13 | 100.0% (95% CI 77.2%-100.0%; 13/13) |
| regression_corpus:stigma | 38 | 38 | 100.0% (95% CI 90.8%-100.0%; 38/38) |

## Gate 3 E2E (real, 2026-11-16; handoffs/DONE-G3-QA.md)
| app | config | passed | failed |
|---|---|---|---|
| citizen | playwright.live.config.ts | 21 | 0 |
| counselor | playwright.config.ts (incl. axe EN+AR) | 27 | 0 |
| counselor | playwright.live.config.ts | 2 | 0 |
| eval-dashboard | playwright.config.ts (incl. live gate-probe, axe EN+AR) | 17 | 0 |
| cross-app | tests/e2e/playwright.config.ts (V1 shared -> counselor (a) -> probe holds leak) | 1 | 0 |
P0: 0 · not covered: citizen a11y.spec (mock config only), citizen visual/budget specs

## Tests per suite
| suite | tests | passed | failed | errors | skipped | status |
|---|---|---|---|---|---|---|
| risk_engine | 85 | 85 | 0 | 0 | 0 | green |
| privacy | 44 | 44 | 0 | 0 | 0 | green |
| fhir | 49 | 49 | 0 | 0 | 0 | green |
| synth | 21 | 21 | 0 | 0 | 0 | green |
| api | 28 | 28 | 0 | 0 | 0 | green |
| agents | 370 | 370 | 0 | 0 | 0 | green |
| loop | 8 | 8 | 0 | 0 | 0 | green |
| qa_redteam_v1 | 540 | 540 | 0 | 0 | 0 | green |
| qa_redteam_holdout | 230 | 158 | 72 | 0 | 0 | red |
| qa_integration | 28 | 28 | 0 | 0 | 0 | green |
| qa_eval | 20 | 20 | 0 | 0 | 0 | green |
| qa_guardrail_script | 3 | 3 | 0 | 0 | 0 | green |

guardrail_check: OK

## What is simulated vs real
| item | source | simulated |
|---|---|---|
| Persona answers (teach-back, SURE) | seeded response model with documented assumptions | True |
| Counselor booking delay, confirmatory completion | response model on a SIMULATED clock | True |
| Teach-back pass/escalation, SURE escalation, loop timer, case/task creation | real backend logic via API | False |
| Gate verdicts on red-team drafts (v1 + held-out) | real BioethicsSupervisor, hand-written synthetic drafts | False |
| Live leakage scan of every API response | real backend responses, independent term derivation | False |
| Arithmetic calibration | independent Fraction oracle vs risk_engine over the synthetic cohort | False |
| FHIR/Phenopacket validation | fhirgen validators over the synthetic cohort | False |
| Genomes, people, couples | synthetic (P-11); no real data anywhere | True |
| GCOS-24/GOS empowerment | NOT INSTRUMENTED (no backend instrument; no values invented) | None |
| Government systems (Malaffi, SEHA, Thiqa) | SIMULATED adapters | True |

## Response-model assumptions (inputs, not findings)
```
{
 "item_accuracy_first_attempt": {
  "low": 0.78,
  "med": 0.88,
  "high": 0.95
 },
 "item_accuracy_gain_after_counselor_reexplanation": 0.1,
 "item_accuracy_cap": 0.99,
 "sure_item_yes_after_counseling": {
  "low": 0.95,
  "med": 0.97,
  "high": 0.99
 },
 "language_effect": "none assumed (EN and AR personas use the same parameters)",
 "sex_effect": "none assumed",
 "counselor_booking_delay_hours": {
  "min": 1,
  "max": 30,
  "distribution": "uniform"
 },
 "confirmatory_completion_share": 0.97,
 "vignette_by_relationship": {
  "unrelated": [
   "V2",
   "V4"
  ],
  "cousins": [
   "V1",
   "V3",
   "V5"
  ]
 },
 "note": "Cohort couples are not exposed by the API (sign-in 404), so persona journeys run over V1-V5 by relationship stratum; cohort couples enter the calibration dimension via the independent oracle."
}
```
