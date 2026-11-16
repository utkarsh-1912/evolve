# 05 — Rollout Plan

Two meanings of "rollout": (1) **hackathon build schedule** (what we ship, when), (2) **post-hackathon deployment path** (shown in the pitch as a credible roadmap; not built now). Timeline below assumes a ~7-day sprint; compress proportionally (Phase = fraction of total time) if shorter. TODO(verify): actual hackathon deadline and judging format.

## 1. Hackathon build schedule (phases, gates, owners)
> **Superseded by docs/08-IMPLEMENTATION-PLAN-v2.md §2** (slice-first). The cut line, drift checklist and roadmap below still apply.
| Phase | Days | Goal | Parallel work (build agents) | Exit gate |
|---|---|---|---|---|
| P0 Foundation | D0 | Repo, contracts, guardrails live | orchestrator: contracts/*, CI, `guardrail_check`; all: read charter | G0: CI green on empty skeleton; contracts v1.0.0 frozen |
| P1 Core engines | D1–2 | Math + data + crypto | risk-engine (R/F/Bayes + goldens); data-synth (V1–V5, 1,000 couples); privacy-apsi (sets, Bloom, signing, consent); fhir-interop (bundle+phenopacket) | G1: goldens + cohort sweep 0% error; APSI tests 1–6 pass; FHIR validator 0 errors |
| P2 Agents | D3–4 | Agent plane behind the gate | agent-runtime (7 agents, stub LLM, Bioethics gate, Copilot triggers); ui-frontend (design system, Landing, Vault); qa-redteam (corpus v1) | G2: red-team 100% on corpus v1; context isolation canary test passes |
| P3 Experience | D4–5 | End-to-end journeys | ui-frontend (Compatibility, Residual-risk, Teach-back, Care path, Counselor console); loop bus; real LLM wired through gate | G3: E2E V1–V5 pass EN+AR; a11y AA |
| P4 Evidence | D5–6 | Eval + polish | qa-redteam (eval harness/dashboard); ui polish (motion, halftone, Venn); docs-demo (script, deck) | G4: five metrics computed + stamped SIMULATED; Lighthouse ≥90 |
| P5 Freeze & rehearse | D6–7 | Demo hardening | docs-demo, orchestrator; **feature freeze at start of D6** | G5: 3 clean demo run-throughs on a fresh machine; offline fallback recorded video |

### Cut line (if time slips — drop in this order, never weaken guardrails)
1. Cascade token UI (keep backend) 2. PSI-CA counts 3. Arabic for counselor console (keep citizen AR) 4. Eval dashboard polish 5. CareNavigator Thiqa BMI branch. **Never cut:** risk math, APSI, Bioethics gate, escalation, EN/AR citizen flow, SIMULATED labels.

### Drift Checklist (orchestrator, at every gate)
- [ ] Every merged PR cites a requirement ID
- [ ] No files changed outside owner paths (git log by agent)
- [ ] No new agent/metric/dependency/gene beyond charter
- [ ] Contracts version unchanged or decision logged in DECISIONS.md
- [ ] Goldens unchanged
- [ ] Red-team pass rate not lower than previous gate
- [ ] No marriage-outcome metric anywhere (`grep`)
- [ ] All mocks labelled SIMULATED

## 2. Daily rhythm
09:00 orchestrator posts day plan (internal task cards, not published) · build agents work in parallel on disjoint paths · 14:00 integration merge window · 18:00 gate review + drift checklist · P0 bugs preempt everything.

## 3. Environments
`local` (docker compose, stub LLM) → `demo` (single VM/laptop, real LLM through gate, seeded synthetic data, reset script `scripts/reset_demo.sh`) → recorded fallback video.

## 4. Post-hackathon deployment roadmap (pitch slide; not built)
| Stage | Scope | Preconditions |
|---|---|---|
| S0 Sandbox | Synthetic + DoH-provided de-identified test data | DoH/M42 partnership; ADHICS gap assessment |
| S1 Shadow mode | Runs beside human counselors on consented real couples; outputs not shown to citizens; compare math & escalation decisions | Ethics approval, PDPL basis, clinical safety case, UAE-local hosting |
| S2 Counselor-assist | Counselor console + brief live; citizen app limited to consented pilot centers (e.g., Baniyas) | Clinical Arabic review, MMIC/GCOS-24 live measurement, red-team re-run |
| S3 Citizen pilot | APSI + citizen app at a few SEHA centers (Abu Dhabi City, Al Ain, Al Dhafra stratified) | Malaffi integration, Consent/AuditEvent to Malaffi, DPIA |
| S4 Scale | All 22 centers, ART/Thiqa navigation | Real-world evidence, regulator sign-off |
Kill criteria at each stage: any confirmed leakage, any directive output reaching a user, or math error ⇒ halt and RCA.

## 5. Risks (top 8)
Scope creep (→guardrails) · LLM drift (→gate, stub tests) · Arabic quality (→native review, TODO(verify)) · APSI complexity (→start with Bloom+signed sets, simple blinded protocol; document threat model honestly) · FHIR validator friction (→ pin IG versions early, P1) · demo-day connectivity (→ offline mode + video) · numeric formula ambiguity (→ `docs/07` + orchestrator decision) · legal-statement accuracy (→ cite doc §, TODO(verify) before external claims).
