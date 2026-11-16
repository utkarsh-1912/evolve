# 04 — Test Strategy

Principle: the riskiest parts (math, privacy, ethics gate) are **deterministic and tested exhaustively**; the LLM is tested through the gate, not trusted.

## 1. Pyramid
| Layer | Tooling | Targets | Gate |
|---|---|---|---|
| Unit — risk math | pytest + Hypothesis | Wright R/F, Bayes, edge cases | 100% branch cov on `risk_engine` |
| Golden vectors | `tests/golden/risk_vectors.json` | V1–V5 + doc numbers | any diff blocks merge |
| Cohort sweep | script over 1,000 synthetic couples | independent re-implementation (fractions/`Fraction` exact) vs engine | 0.0% error (tolerance 1e-12) |
| FHIR/GA4GH validity | HL7 validator CLI, phenopacket-tools, ref-walker | all bundles | 0 errors, 0 dangling `hasMember`/`derivedFrom` |
| APSI/crypto | pytest | correctness, leakage, forged sets, replay | see §3 |
| Consent/auth | pytest | scopes, PKCE, expiry, revocation latency ≤5 s | 100% |
| Agent contract | pytest w/ stub LLM | tool-binding, per-user context isolation | 100% |
| Guardrail red-team | `tests/guardrails/corpus/*.yaml` | ≥300 adversarial prompts (EN+AR) | 100% intercepted, 0 false leak |
| E2E | Playwright | V1–V5 journeys, EN+AR | pass |
| A11y/visual | axe, Playwright screenshots, Lighthouse | citizen + counselor | AA, ≥90 |
| Perf | k6/locust-lite | APSI ≤2 s p95 on 570-gene sets; page TTI ≤3 s | thresholds |
| Simulated outcomes | eval harness | 5 dimensions | thresholds in charter, labelled SIMULATED |

## 2. Risk-math tests (owner: risk-engine, reviewed by qa-redteam)
Golden vectors (reproduced and verified from the source doc):
- V2 CYP21A2, unrelated, q=0.106, d=0.92 → residual 0.0094 (1 in 106.4), offspring 1 in 425.7; d=0.99 → 0.00118 (1 in 844.4), offspring 1 in 3,377.6.
- V3 SMN1, first cousins, q=0.013, d=0.92 → prior 0.13637, residual 0.01248 (1 in 80.2), offspring 1 in 320.6; unrelated → 1 in 3,800.2.
- Concordant → 0.25. Concordant negative → ≈ (q(1−d))²-based small value per formula; document exact formula in `docs/07-RISK-MATH-SPEC.md`.
- Wright: first cousins R=1/8, F=1/16; double first cousins R=1/4, F=1/8; ancestor-inbred scaling.
Property tests: posterior ∈ [0,1]; monotone in d; d=1 ⇒ posterior 0; d=0 ⇒ posterior=prior; r=0 ⇒ prior=q; symmetric couple handling; Fraction vs float agreement.

## 3. Privacy / APSI tests
1. Disjoint sets ⇒ empty output; **assert transcript reveals no element** (Bob's view test).
2. Overlap ⇒ exactly the intersection, nothing more.
3. Forged/unsigned element ⇒ rejected.
4. Consent missing/expired/revoked ⇒ APSI never invoked (spy assert).
5. Revocation ⇒ workspace token dead, cache purged ≤5 s.
6. Replay of old session blob ⇒ rejected.
7. Cross-partner context bleed: run both partners' sessions interleaved with canary gene "ZZZ9"; canary never appears in the other's outputs (metamorphic test).
8. Cascade token: contains only HGNC ID + variant digest; no index identity (schema + fuzz).
9. Small-cell suppression: counts <10 suppressed.
10. Logs scan: no gene symbols/HGVS in logs.

## 4. Ethics / legal gate tests (BioethicsSupervisor)
Corpus categories (each ≥40 cases, EN+AR, incl. jailbreak/paraphrase/multi-turn): directive marriage advice · donor gametes · PGT-M without both-spouse consent · fetal-anomaly termination advice/gestational limits · numeric tampering (e.g., "1 in 50" vs locked "1 in 80.2") · cross-partner leakage via indirect phrasing · stigmatizing consanguinity language · reassurance on CYP21A2/SMN1 negatives · hidden-escalation bypass.
Pass = blocked/rewritten/escalated, **and** a safe benign control set still passes (false-positive budget ≤5%, since over-blocking hurts comprehension).
Fail-closed test: kill the classifier ⇒ no message delivered.

## 5. Evaluation harness (R-EVAL-1) — simulated
Synthetic user personas (language × literacy × gender) answer MMIC/SURE items via a scripted/LLM-persona model; compute the five dimensions with stratification; **report CIs and "SIMULATED" stamps**. Never claim clinical validity.

## 6. CI pipeline
`lint → guardrail_check → unit → golden → cohort-sweep → fhir-validate → apsi/consent → agent-contract → red-team → e2e (smoke) → a11y`. Merge requires all green; nightly full red-team + perf.

## 7. Defect severity
P0: leakage, numeric drift, directive/unlawful output, silent clearance of escalation case, wrong risk math. P0 stops all feature work until fixed + regression test added.
