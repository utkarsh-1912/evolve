# 08 — Implementation Plan v2 (supersedes the phase table in docs/05 §1 and backlog in docs/06 §5)

Written 2026-11-08 after reviewing v1 against the actual environment. Guardrails, charter, design, and test strategy are unchanged.

## 1. What changed and why
| # | v1 | v2 | Why |
|---|---|---|---|
| 1 | Layer-by-layer phases (engines → agents → UI); first demo at P3 | **Slice-first**: engines thin-but-real in P1, then a **walking skeleton** (V4, V1, V3 end to end) in P2, then depth | Being demoable early de-risks the hackathon; later phases deepen work that already runs end to end |
| 2 | Six tiers as separate services | **Modular monolith**: one FastAPI app `services/api` that imports packages `risk_engine`, `privacy`, `fhir`, `synth`, `agents`, `loop` | One process to run and demo; package boundaries still match ownership |
| 3 | Agents would agree on data formats informally | **Contracts frozen before P1**: `gene_panel.json`, `cohort.schema.json`, `apsi_result.schema.json`, `consent.schema.json` | data-synth, risk-engine, fhir-interop, and privacy-apsi run in parallel without waiting on each other |
| 4 | HL7 Java validator CLI as a P1 gate | P1 gate = `fhir.resources` R4B model validation + our reference-walker + profile-component checks. The HL7 validator CLI becomes a **P4 stretch** run, reported honestly | Java 25 is present but the jar and IG packages are large downloads; R4B models validate the same resource shapes we use |
| 5 | "APSI with Bloom filter" (underspecified) | **Concrete protocol**: authority RSA-FDH signatures over HGNC IDs (authorization), then DH-commutative PSI over the RFC 3526 2048-bit MODP group on the signatures (privacy); Bloom filter only as an optional server-assisted variant | Implementable with stdlib `pow` + `cryptography`; standard construction; easy to test for leakage |
| 6 | Git worktrees per agent | No git repo exists. Agents share the folder; **write paths are disjoint by design**; orchestrator reviews by file list + tests | Worktree isolation needs a git repo. Recommend `git init` before P2 (user decision) |
| 7 | CulturalCommunicator = LLM | **Template-first** EN/AR wording with locked-number slots; LLM paraphrase optional behind the gate | Demo reliability offline; numbers never pass through an LLM |
| 8 | Eval metrics 1–3 "p<0.01" from simulated personas | Kept, but cut-line item #4 and every output stamped SIMULATED; never framed as evidence | Honesty (P-20) |

## 2. Phases
| Phase | Parallel agents | Deliverable | Exit gate |
|---|---|---|---|
| **P0** (done by orchestrator) | — | Contracts, gene panel, deps installed, task cards | contracts validate; `guardrail_check` OK |
| **P1 Engines** | risk-engine · data-synth · privacy-apsi · fhir-interop | Each package importable with a pure-Python API + tests (cards in `handoffs/TASK-P1-*.md`) | G1: all four suites green; V1–V5 fixtures pass through risk-engine with expected numbers; APSI leakage tests green; bundles validate with 0 dangling refs |
| **P2 Walking skeleton** | agent-runtime (`services/api` + 7 agents + gate) · ui-frontend (Clinic theme + 4 demo screens against mocks, then live) · qa-redteam (corpus v1 + integration tests) | `uvicorn services.api.main:app` + `apps/citizen` running the V4, V1, and V3 journeys | G2: E2E smoke for V4/V1/V3; red-team v1 at 100%; canary isolation test |
| **P3 Depth** | agent-runtime (loop bus, CareNavigator, Copilot brief) · ui-frontend (counselor console, residual-risk explainer, care path, AR/RTL) · qa-redteam (E2E V1–V5 EN+AR) | All charter UX requirements | G3: R-UX-1/2/3 done; a11y AA |
| **P4 Evidence + polish** | qa-redteam (eval harness) · ui-frontend (Ledger dashboard, motion) · docs-demo · fhir-interop (HL7 CLI stretch) | Dashboard, demo script, deck | G4 |
| **P5 Freeze** | docs-demo, orchestrator | 3 clean demo runs; fallback video | G5 |

## 3. P1 integration points (each lands only via contracts)
- `contracts/gene_panel.json` → read by synth (sampling), risk_engine (q and d lookup), fhir (HGNC/RefSeq), privacy (the HGNC ID universe).
- synth writes `services/synth/out/cohort.json` + `tests/golden/cohort/V1..V5.json` (schema `cohort.schema.json`) → fhir consumes; risk-engine's cohort sweep consumes.
- privacy exposes `privacy.apsi.run(consent_a, consent_b, signed_set_a, signed_set_b) -> ApsiResult` (schema `apsi_result.schema.json`).
- risk_engine exposes `assess_couple(couple_json) -> list[locked RiskOutput]` (added in P1) so agent-runtime gets numbers from one call.

## 4. Environment facts (2026-11-08)
Python 3.13 with pytest 9, jsonschema, hypothesis, cryptography 46, pydantic 2.12, fastapi, fhir.resources 8.3 (**use the `fhir.resources.R4B` models**), phenopackets. Java 25 is available (HL7 CLI stretch). No git. No Node project yet (P2).
