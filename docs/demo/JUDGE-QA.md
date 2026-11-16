# évolvé: judge Q&A sheet (R-DEMO-1)

Status: P5 final (numbers per CLAIMS-LEDGER.md). The answers are honest by design (docs/01 P-20: never invent facts). If the true answer is "we haven't done that", say so. Citations: `src §x` = docs/source/architecture-source.txt; `pack` = `apps/eval-dashboard/data/evidence.json`; plus repo docs, test files and docs/DECISIONS.md.

## Real vs simulated
**1. What is real here and what is simulated?**
**Real:**
- the risk math (risk_engine)
- the APSI cryptography (services/privacy)
- consent, revocation and the hash-chained audit log
- FHIR/Phenopacket generation
- the seven agents and the gate
- the care-loop state machine
- the citizen app

**Simulated:**
- all data (synthetic)
- sign-in
- the Malaffi, SEHA, Thiqa and Judicial adapters
- booking and the 48 h clock
- the "partner agrees" button in the demo
- every comprehension, SURE and GCOS number (simulated personas)

[README "Limitations"; docs/00 out-of-scope]

**2. Is any real patient data involved, or any real genome?**
No. The 1,000 couples and V1–V5 are generated, calibrated to published Emirati carrier frequencies [src §2.1; DECISIONS #10, #22]. The guardrail check scans for real-looking IDs and secrets [docs/01 §C].

**3. Your comprehension and SURE numbers: are those results?**
No. They come from simulated personas and are stamped SIMULATED. They show the evaluation harness works, not that people understand better. Real measurement starts at S2 [charter honesty rule; docs/05 §4]. Simulated values: teach-back 62.1% first attempt, 92.1% after re-explanation; SURE 4/4 87.1%. Both are below target, and the verdicts are artifacts of fixed response-model assumptions [pack `dimensions`; DECISIONS #43].

## Architecture
**4. Why not one LLM? Why seven agents?**
The source names three failure modes of a single model: it hallucinates conditional probabilities, it leaks across partners through shared memory, and it drifts into directive advice [src §4]. Each agent has narrow tools. Code does the math and the set and consent logic; the language side only fills locked slots [docs/02 §4]. The roster is fixed and checked in CI [G-03].

**5. What if the LLM lies?**
1. Today the default runtime uses **no** LLM. Messages are templates filled with locked values [DECISIONS #7, #25].
2. In LLM mode, every draft passes BioethicsSupervisor. Any number not in the locked JSON is blocked (`numeric_drift`), the gate fails closed on error, and a failed redraft goes to a human [contracts/api.md; docs/01 fail-safe default].
3. Escalation is structural, so it happens whatever the text says [DECISIONS #24].

Honest caveat: on an unseen red-team set (held-out v2) the gate catches 62.4%. That is why LLM paraphrase is hard-off and patients get only pre-approved templates [pack `redteam`; DECISIONS #49].

**6. Your gate scores 100% on its regression corpus and 62% on the held-out set. Why should we trust it?**
The difference is exactly why we built the held-out set. We fixed bugs while looking at corpus v1, so v1 no longer counts as evidence [DECISIONS #25, #33]. A lexical gate doesn't generalise, so we stopped relying on it for patients [DECISIONS #37, #49]. The safety case is:
- closed templates only: 25,692 template × record combinations verified, 0 failures; 17 tests prove there is no free-text path [DECISIONS #45, #51]
- structural escalation
- the numeric check, which on the held-out set caught every digit-format attack and missed one dialect word

Held-out history: v1 65.3% → 89.6% after fixes (not fully blind); fresh v2 62.4% / 4.7% FP [pack `g2`; tests/guardrails/reports/].

**7. How do you know the math is right?**
- Golden vectors reproduce every number in the source's vignettes: 1 in 4, 1 in 426, 1 in 321 vs 1 in 3,800 [docs/07 §3].
- Two independent oracles, written with different algebra, swept all 1,000 couples with 0 mismatches [pack `dimensions.calibration`; tests/_support/oracle.py; services/risk_engine/tests/test_cohort_sweep.py].
- Property tests: R = 2F, and the posterior never exceeds the prior [services/risk_engine/tests/].

Caveat: the assay detection rates (0.92, 0.99) were inferred from the source's outputs. We need the authors to confirm them [DECISIONS #1].

**8. Why only 8 genes when the program screens 570?**
The source gives verified Emirati carrier frequencies for that set of genes [src §2.1 table]. We won't invent frequencies for the rest [P-20]. The engine is gene-agnostic and reads contracts/gene_panel.json. Consequence: our cohort's couple concordance of 3.40% is an 8-gene floor, and it isn't comparable with the 570-gene 4.8% [DECISIONS #10, #22].

**9. Does it handle consanguinity properly?**
- Wright's path coefficient across multiple paths, including the ancestor-inbreeding term [R-RISK-1; docs/07 §1].
- Consanguinity raises the partner's prior carrier probability before the Bayesian update. That is how V3 reaches 1 in 321 [src §2.3, §2.4].
- F is shown only as genome-wide context, never as the risk for a tested gene [P-03].

## Privacy
**10. Explain APSI in one breath.**
The screening authority signs each person's carrier-gene list. Each side scrambles its signed list with a secret, and the two sides compare the scrambled lists. A gene they share produces a match. Everything else stays unreadable. No match means the couple sees only "Compatible" [src §3.2; DECISIONS #5].

**11. What are the limits of your privacy threat model?**
Assumes semi-honest partners. **Not covered:**
- a partner cheating inside the protocol
- hiding the set sizes
- constant-time big-integer arithmetic
- durable key custody (keys live in memory and die on restart)

Small-cell suppression covers single cells only, not complementary suppression [services/privacy/THREAT_MODEL.md]. Production would need authenticated channels and an HSM-backed authority. That is S1+ work.

**12. Can't Partner B infer A's status from the explanation they get?**
That was a real bug class, and we fixed it in policy:
- Every partner gets the same uniform counselor notice.
- A screen-negative partner gets no differential "under review" message.
- The gate treats any statement about the partner's genetic status as leakage unless the gene is in the intersection.

[DECISIONS #23, #27; contracts/api.md v1.1.0]. Partner-status paraphrase is still an open miss class: 12/27 leakage drafts caught on held-out v2 [pack `redteam`].

**13. What happens when someone withdraws consent?**
The couple workspace token is revoked, and the intersection, records and messages are purged. The next request returns 409. The target is ≤5 s, and it is tested [P-07; services/privacy/tests/; tests/integration/test_api_isolation.py].

## Ethics and law
**14. How do you handle consanguinity without stigma?**
- We never call it a mistake [P-17].
- We show both absolute and relative risk ("1 in 321, compared with 1 in 3,800").
- The pedigree is context, not blame.
- The gate has a stigma rule. It is still weak on unseen drafts (held-out v2: 6/16 caught) [pack `redteam`].
- The UI copy describes cousin marriage as a family fact.

**15. What is your legal basis? Are you compliant with UAE law?**
We don't give legal advice. The gate is **designed to comply with** the statutes the source lists, **pending legal review**:
- Fed. Law 11/2008: no donor gametes
- Fed. Law 7/2019: PGT-M needs both spouses' written consent
- Art. 16 of the Medical Liability Law and Cabinet Res. 44/2024: fetal-anomaly questions go to an MFM physician and a genetic counselor, and we never state limits or procedures [src §4.1 Agent 6; P-16]

PDPL and ADHICS are named in the source as targets for the production stack [src §3]. We have not done a compliance assessment; that is in the S0 preconditions [docs/05 §4].

**16. Doesn't this push couples not to marry?**
No. The system never advises marrying or not marrying, and it says on every result that the certificate is issued regardless [src §1, §3.4; P-13, P-14]. Options are listed in no particular order. There is no marriage-outcome metric anywhere in the code or the dashboard, and CI checks for one [P-15; docs/01 §C].

**17. What about pregnancy and termination questions?**
Any fetal-anomaly question goes straight to an MFM physician and an accredited genetic counselor, and the system gives no advice. It never states gestational limits or procedures as guidance [P-16]. The free-text gate still misses some unseen drafts here (held-out v2: 12/17 caught) [pack `redteam`]. Structural routing is unaffected.

## Clinical
**18. How would you validate this clinically?**
Not yet done. Path per docs/05 §4:
1. **S0:** sandbox with de-identified test data.
2. **S1:** shadow mode beside counselors, comparing the math and the escalation decisions; nothing is shown to citizens.
3. **S2:** counselor-assist, with live MMIC/GCOS-24 measurement.
4. **S3:** pilot at a few SEHA centers, stratified by region.

Ethics approval and a clinical safety case are needed before S1.

**19. Is it a medical device? Does it diagnose?**
It is decision support, not a diagnosis, and the UI says so on every screen [P-19]. Regulatory classification hasn't been assessed. TODO(verify) with the regulator at S0.

**20. What happens with a VUS or a weird genotype?**
No number is shown and nothing is auto-cleared:
- A shared VUS inside ROH >10 Mb escalates under trigger (c), as in V5, and is visible to the counselor only [src §4.1 Agent 7; DECISIONS #20].
- Atypical genotypes (homozygous, ≥2 P/LP in one gene) fail safe: needs_counselor, escalation [DECISIONS #18].

## Product, scale, cost
**21. How good is the Arabic?**
Better than before, but not yet good enough for citizens:
- The patient copy (71 strings: templates, teach-back and API text) is real Modern Standard Arabic. It passes the template closure check, but each string is marked TODO(native-review) [DECISIONS #48].
- Counselor and eval-dashboard Arabic are English placeholders [DECISIONS #50].
- The gate's Arabic patterns need native review.

We would not take Arabic to citizens before a native clinical review (S2 precondition).

**22. What does it cost to run, and does it scale?**
Measured: one process on a laptop runs the whole demo. A full cohort sweep of 1,000 couples runs inside the risk-engine test suite (85 tests) [pack `tests`]. APSI cost grows linearly with set size, and per-person sets are small (carrier genes only). We have **no** production cost model. TODO(team) for S0 sizing.

**23. Why would DoH or M42 adopt this rather than build it?**
It is built to their interfaces: FHIR R4 Genomics Reporting, GA4GH Phenopackets/Pedigree, SMART-on-FHIR-style scopes. They stay the certifying authority and keep their WGS pipeline [src §2.2, §3.2, §3.3]. All of those integrations are SIMULATED today.

**24. What did you deliberately not build?**
- variant calling
- diagnosis or treatment advice
- embryo or sex selection
- donor options
- payments
- social features
- any extra agent, or any gene beyond the source [docs/00 out-of-scope]

## Numbers you may be asked to repeat
4.8% (565/11,748) [src §1] · 52% / 30% novelty gap [src §2.1] · 1 in 4 / 1 in 426 / 1 in 321 vs 1 in 3,800 [docs/07 §3] · 0 mismatches over 1,000 couples [pack `dimensions.calibration`] · held-out v2 113/181 = 62.4%, FP 2/43 [pack `g2`] · template closure 25,692 / 0 failures [DECISIONS #51] · 48 h booking target [src §5].
