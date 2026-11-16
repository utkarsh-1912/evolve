# 02 — System Design

## 1. Principles
Neuro-symbolic split · privacy by construction · fail closed · standards (FHIR R4 Genomics Reporting IG, GA4GH Phenopackets v2/Pedigree, SMART v2) · everything simulated behind adapters so real Malaffi/SEHA can replace mocks.

## 2. Six tiers → hackathon implementation
| Tier (source) | Real-world | Our prototype (all synthetic) |
|---|---|---|
| 1 Sovereign ingestion | M42 30X WGS pipeline | `data-synth` emits VCF-like call sets (JSON) for 570-gene panel subset |
| 2 FHIR/GA4GH standardization | Transformation service | `services/fhir`: GenomicReport Bundle, Variant/Genotype/DiagnosticImplication Observations, Phenopacket v2, Pedigree; validator CLI in CI |
| 3 APSI enclave | DoH/M42 signs carrier sets | `services/privacy/apsi`: authority-signed (RSA) HGNC-ID sets, Bloom filter, blinded intersection; PSI-CA variant for counts |
| 4 Identity/consent | SMART v2 + FHIR Consent | `services/privacy/auth`: OIDC+PKCE (local IdP), scope map, Consent store, AuditEvent log |
| 5 Agent plane | Seven agents | `services/agents`: orchestrator graph, tool bindings, per-user context |
| 6 Closed-loop bus | Malaffi/SEHA/ART/Judicial | `services/loop`: 7-state machine, simulated adapters (labelled) |

## 3. Topology
```
Citizen App (AR/EN) ─┐                         ┌─ Counselor Console
                     ▼                         ▼
              API Gateway (SMART scopes, PKCE, audit)  ── AuditEvent store
                     │
     ┌───────────────┼────────────────────────────┐
     ▼               ▼                            ▼
 ConsentGuardian  APSI service              Agent Orchestrator
     │  (consent→token)  (signed sets)       │
     │                                       ├─ VariantInterpreter ─┐ tools
     │                                       ├─ PedigreeRiskEngine ─┤ → risk_engine (pure Python)
     │                                       ├─ CulturalCommunicator (LLM, reads locked JSON only)
     │                                       ├─ CareNavigator ── eligibility rules (symbolic)
     │                                       ├─ BioethicsSupervisor (mandatory outbound gate, fail-closed)
     │                                       └─ CounselorCopilot ── Consultation Brief → Counselor Console
     ▼
 FHIR store (synthetic) ── Loop bus (state machine) ── SIMULATED Malaffi/SEHA/ART/Judicial adapters
```
Outbound path for every user-visible message: `draft (LLM) → BioethicsSupervisor → deliver | block+regenerate(≤2) | escalate`.

## 4. Agent specs (binding; tools are the only way an agent touches data)
| Agent | Kind | Tools | Hard rules |
|---|---|---|---|
| ConsentGuardian | symbolic | `consent.verify`, `consent.request`, `token.scope_check`, `apsi.invoke`, `audit.write`, `workspace.purge` | invokes APSI only after both signed Consents; revocation ⇒ kill token + purge ≤5 s |
| VariantInterpreter | symbolic | `fhir.parse_bundle`, `curation.lookup` (ClinVar/gnomAD-MID/ERGP fixtures), `fhir.make_task` | flags CYP21A2/SMN1 ⇒ recommended-action Task; surfaces novelty-gap variants |
| PedigreeRiskEngine | symbolic | `pedigree.build`, `risk.wright`, `risk.bayes`, `risk.lock` | outputs immutable `RiskOutput` JSON; no LLM inside |
| CulturalCommunicator | LLM | `risk.read_locked`, `teachback.generate` | never computes; absolute+relative risk; AR/EN; carrier≠diagnosis; teach-back before close |
| CareNavigator | symbolic rules + LLM wording | `eligibility.art_thiqa`, `directory.centers`, `referral.create` | non-directive; immediate eligibility w/o 12-mo wait; age 18–45 (46–47 w/ AFC≥5), BMI 19–35 / Thiqa 19–40 |
| BioethicsSupervisor | symbolic rules + classifier | `gate.numeric`, `gate.leakage`, `gate.nondirective`, `gate.uae_law` | all 4 must pass; fail-closed |
| CounselorCopilot | symbolic + LLM summary | `triage.rules`, `brief.assemble`, `task.create` | triggers (a) incompatible (b) discordant w/ elevated residual (c) VUS-in-ROH or red-flag pedigree (d) SURE<4 / teach-back fail |

Model choice: any LLM behind an interface `LLMClient`; default Claude (see `agents/agent-runtime.md`). Tests run with a deterministic stub LLM so gates are verifiable offline.

## 5. Data contracts (`contracts/`)
- `risk_output.schema.json` — locked numbers: scenario, genes, R, F, prior, detection_rate, posterior_carrier, reproductive_risk (as fraction + "1 in N" string + display strings AR/EN), flags, `fusage`.
- `agents.json` — roster (guardrail G-03).
- `consent.schema.json`, `apsi_result.schema.json`, `escalation_brief.schema.json`, `loop_state.schema.json`.
Version field `contract_version`; golden tests pin it.

## 6. Closed-loop state machine
`ResultIssued → PatientNotified → ComprehensionConfirmed → ConfirmatoryDone → CounselingDone → ReproReferralDone → HumanClosure`. Only a human actor can write `HumanClosure`. Timers: incompatible couples must reach counseling booking ≤48 h (simulated clock).

## 7. Security & privacy design
OIDC+PKCE (state ≥122-bit), tokens ≤1 h, private-key JWT for services, least-privilege scopes (table in source §3.3), AuditEvent on each read/disclosure, logs redacted, small-cell suppression k≥10 for population view, UAE-local deployment assumption documented (we run local; no external data egress except the LLM call carrying **only locked JSON + non-identifying context** — LLM adapter strips identifiers; documented residual risk).

## 8. Tech stack (recommended; allow-list in `scripts/allowed_deps.txt`)
Python 3.12 + FastAPI + Pydantic v2 (services, risk engine) · `cryptography` (RSA signatures), custom Bloom filter · `fhir.resources` + HL7 validator CLI (Java) · `phenopackets` + phenopacket-tools · SQLite/Postgres · Next.js 14 + TypeScript + Tailwind + `next-intl` (AR RTL) + Framer Motion/GSAP · pytest, Hypothesis, Playwright, axe-core · Docker Compose.

## 8a. Repo layout
```
/services/{risk_engine,fhir,privacy,agents,loop,synth}
/apps/{citizen,counselor,eval-dashboard}
/contracts  /tests/{golden,guardrails,e2e,perf}  /docs  /agents  /handoffs  /scripts
```
