# évolvé: pitch outline (10 slides, R-DEMO-1)

Status: P5 final (numbers per CLAIMS-LEDGER.md). Every claim carries a citation in brackets: a source section (`src §x`, from docs/source/architecture-source.txt), a repo doc, or a DONE card / evidence-pack field. Theme: Clinic for slides 1–5 and Ledger for slides 6–8 (docs/03 §3). The product name is TODO(team); until it's decided, use "évolvé · Inherited risk, explained" (docs/03 §0).

Things you must not do on any slide:
- show a marriage-outcome metric (P-15);
- make a clinical-efficacy claim;
- present a statute as legal advice (P-16, P-20);
- show a metric without the word **SIMULATED** where it comes from personas (charter honesty rule).

---

### 1. The problem: screening finds risk; people still have to understand it
- 570 genes and >840 recessive conditions, through mandatory premarital WGS [src Intro]
- 565 of 11,748 couples at risk, about 4.8% [src Intro, §1]
- Three bottlenecks:
  - 52% of Emirati P/LP variants are absent from gnomAD and 30% from ClinVar [src Intro, §2.1]
  - naive sharing exposes a partner's private findings [src §3.2]
  - pipelines ignore consanguinity and the test's blind spots [src Intro]

**Speaker notes:** Abu Dhabi already has the screening. The gap is what happens after the result: comprehension, privacy, and getting to a counselor. "Screening only achieves clinical impact when individuals and couples comprehend…" [src Intro]. Say the 4.8% exactly. The 13.1% figure comes from an enriched early cohort [src §1]. Don't mix the two.

### 2. Insight: separate the math, the privacy and the words
- A single LLM can hallucinate conditional probabilities, leak context across partners, and drift into directive advice [src §4]
- So code does the math, set logic and consent checks; language models only write words from locked JSON [src §4; docs/02 §4]
- Success means comprehension, informed choice and reaching care. It never means marriages cancelled [src §1; charter]

**Speaker notes:** The source records that the certificate is issued regardless of the result, and that after non-directive counseling couples made their own choices [src §1]. We take that as a design constraint. Don't quote the 33%/67% split as an outcome we aim at. If asked, say it describes the baseline and that we never optimise it (P-15).

### 3. Product: one journey from result to human care
- Private vault → consent by both partners → private check → plain-language explanation in EN/AR → counselor handoff → 7-state care loop up to human closure [src §3.4; docs/02 §6]
- Screens: citizen Home, Compatibility, Result explainer, Care plan; counselor workbench; eval dashboard [docs/09 §4]
- The demo covers V4, V1 and V3 live, with V2 and V5 as spares [src §2.4; tests/golden/cohort]

**Speaker notes:** Show screenshots of V4 "Compatible", the V1 handoff, and the V3 "negative is not zero" screen. Screenshots: apps/citizen/screenshots/p3/cit/, apps/counselor/screenshots/, apps/eval-dashboard/screenshots/. Say "decision support, not a diagnosis" out loud.

### 4. Privacy: the partner learns only what you share
- Authority-signed gene sets (RSA-FDH), so nobody can probe with invented genes [src §3.2; DECISIONS #5]
- Blinded intersection (DH-commutative PSI, RFC 3526 2048-bit group). An empty result shows only "Compatible" [src §3.2; DECISIONS #5; services/privacy/THREAT_MODEL.md]
- Two valid consents are required. Revocation purges the workspace, and this is tested [P-07; services/privacy/tests/; tests/integration/test_api_isolation.py]
- Cascade Screening Token: a single gene, with no identity of the index patient [src §3.2; services/privacy/tests/]

**Speaker notes:** Tested: forged sets, missing, expired or revoked consent, replay, and canary isolation across V1–V5 [services/privacy/tests/; tests/integration/test_api_isolation.py]. Be clear about the limits: semi-honest partners only, set sizes are revealed, keys live in memory [services/privacy/THREAT_MODEL.md].

### 5. Safety: the gate, and escalation that doesn't depend on wording
- BioethicsSupervisor checks every outbound draft for numeric drift, leakage, directive phrasing, UAE-law content, the judicial statement, stigma and false reassurance. It fails closed [src §4.1 Agent 6; contracts/api.md]
- Designed to comply with Fed. Law 11/2008 (no donor gametes), Fed. Law 7/2019 (PGT-M needs both spouses' written consent), and Art. 16 of the Medical Liability Law with Cabinet Res. 44/2024 (fetal anomaly → MFM + counselor). Pending legal review [src §4.1 Agent 6]
- CounselorCopilot escalation (a)–(d) is structural: incompatible; residual risk; VUS in ROH or a red-flag pedigree; SURE <4 or failed teach-back [src §4.1 Agent 7]

**Speaker notes:** Show the live gate block (demo beat 3:30). Be honest: on the unseen held-out v2 set the gate catches 113/181 = 62.4%, with 4.7% false positives [pack `g2`; tests/guardrails/reports/holdout_last_run.json]. The safety guarantee is therefore structural: patients get only pre-approved templates, closure verified over 25,692 combinations with 0 failures, LLM paraphrase hard-off [DECISIONS #37, #45, #49, #51].

### 6. Evidence (Ledger): what we measured, and how
| Dimension | Result | Source |
|---|---|---|
| Calibration: arithmetic | 0 mismatches, 1,000 synthetic couples, 2 independent oracles | pack `dimensions.calibration`; tests/integration/test_cross_package.py |
| Calibration: FHIR | 0 errors on our harness; HL7 CLI 8 errors, all terminology-server timeouts (inconclusive) | pack; DECISIONS #42 |
| Privacy | 0 leaks / 2,491 live API responses; gate let 17 red-team leakage drafts through | pack `dimensions.privacy` |
| Patient text | closed templates: 25,692 combinations, 0 failures; 17 no-free-text tests | DECISIONS #45, #51 |
| Gate on unseen drafts | held-out v2 62.4% caught / 4.7% FP (target ≥95% / ≤5%, not met) | pack `g2` |
| Comprehension, SURE, loop velocity (**SIMULATED**) | teach-back 62.1% first attempt (target 85%); SURE 4/4 87.1% (target 90%); 39/39 booked ≤48 h; GCOS not instrumented | pack `dimensions` |

**Speaker notes:** Every SIMULATED cell says so on the slide. Targets come from source §5: ≥85% comprehension, ≥90% SURE 4/4, 100% booked ≤48 h, 0.0% arithmetic error, 0.0% leakage, 100% interception. Present them as targets, not achievements, unless the evidence pack shows them.

### 7. Ecosystem fit: built to plug in (integrations SIMULATED)
- Malaffi (HIE): FHIR R4 GenomicReport bundles, Consent, AuditEvent [src §2.2, §3.3]
- SEHA: booking for counseling and confirmatory tests; designated screening centers [src §3.1, §3.4]
- M42 / DoH: the certifying authority for signed carrier sets; the WGS pipeline stays theirs [src §3.2, §1]
- Thiqa: ART/PGT-M eligibility checks (age, BMI) [src §4.1 Agent 5]
- Judicial Department: certificate decoupling, informational only [src §3.4]

**Speaker notes:** None of these is connected. All of them are SIMULATED adapters [docs/00 out-of-scope]. Say "integration targets", never "integrated with". We don't do variant calling [charter out-of-scope].

### 8. Roadmap S0–S4, with kill criteria
| Stage | Scope |
|---|---|
| S0 Sandbox | synthetic + DoH de-identified test data |
| S1 Shadow mode | runs beside counselors; no citizen output |
| S2 Counselor-assist | brief and console live |
| S3 Citizen pilot | a few SEHA centers, stratified |
| S4 Scale | all centers, ART/Thiqa navigation |

Kill criteria at every stage: any leak, any directive output, any math error ⇒ halt and do a root-cause analysis [docs/05 §4].

**Speaker notes:** The preconditions per stage are in docs/05 §4: ethics approval, PDPL basis, clinical safety case, UAE-local hosting, Arabic clinical review, DPIA. Clinical validation starts at S1 and not before.

### 9. Team évolvé
- Team: names and roles TODO(team)
- How we built it: nine scoped build agents under one orchestrator, every rule mechanically checked (guardrail_check, red team, golden vectors) [docs/06]

**Speaker notes:** Credit the human team. Explain the AI-assisted build only if asked, and frame it as more process control, not less human oversight.

### 10. The ask
- Sandbox access (S0) with DoH/M42 de-identified test data [docs/05 §4]
- A clinical genetics partner for validation and native Arabic clinical review [TODO(ar); docs/05 §5]
- Legal review of the statute mapping before any external legal claim [P-20]

**Speaker notes:** Close on the promise: "We explain. We never tell you what to do." (apps/citizen landing copy). Leave the slide up for questions.
