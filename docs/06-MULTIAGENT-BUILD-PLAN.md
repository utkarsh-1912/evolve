# 06 — Multi-Agent Build Plan (how AI agents build this repo)

Don't confuse: **runtime agents** (the 7 in the product) vs **build agents** (Claude Code subagents that write the code). This doc covers build agents. Their definitions and long-form briefs are internal build files (not published).

## 1. Topology: orchestrator + 8 specialists, disjoint ownership
```
                         orchestrator (plans, gates, merges, owns contracts/)
 ┌──────────┬────────────┬────────────┬───────────┬──────────────┬──────────┬───────────┐
data-synth risk-engine privacy-apsi fhir-interop agent-runtime ui-frontend qa-redteam docs-demo
```
| Agent | Owns (write) | Reads | Produces | Depends on |
|---|---|---|---|---|
| orchestrator | `contracts/`, `docs/DECISIONS.md`, internal task cards, CI, build-agent config, CODEOWNERS | all | task cards, gate verdicts | — |
| data-synth | `services/synth/`, `tests/golden/cohort/` | contracts, charter | 1,000-couple cohort, V1–V5 fixtures, novelty-gap sim | contracts |
| risk-engine | `services/risk_engine/`, `tests/golden/risk_vectors.json` | docs/07 | pure-Python Wright/Bayes, lock fn | contracts |
| privacy-apsi | `services/privacy/` | contracts | APSI, signing, consent store, OIDC/PKCE, scopes, AuditEvent, cascade token | contracts |
| fhir-interop | `services/fhir/` | synth output | FHIR bundles, Phenopackets, pedigree, validator harness | data-synth schema |
| agent-runtime | `services/agents/`, `services/loop/` | risk, privacy, fhir APIs | 7 agents, gate, copilot, loop bus, `LLMClient` + stub | risk-engine, privacy-apsi |
| ui-frontend | `apps/`, `design/` | contracts, docs/03 | citizen, counselor, eval dashboard | agent-runtime API (mock first) |
| qa-redteam | `tests/`, `services/eval/` | everything (read-only on src) | corpus, e2e, eval harness, findings | all |
| docs-demo | `docs/demo/`, `README.md` | all | demo script, deck outline, README | all |

Rule: **write-ownership is exclusive**; cross-boundary needs a handoff card (internal, not published). qa-redteam is deliberately independent — it must not edit code it tests (files bugs as internal bug cards).

## 2. Contract-first sequencing (unblocks parallelism)
Day 0 orchestrator freezes: `risk_output.schema.json`, `agents.json`, consent/apsi/brief/loop schemas, API route list (`contracts/openapi.yaml`, stub). After that every agent builds against contracts using mocks, so P1 runs fully in parallel.

## 3. Task card format (internal task cards, not published)
```
id · agent · requirement IDs · inputs (files/contracts) · deliverable (paths) · acceptance (tests that must pass) · guardrails touched · est. · deadline-gate
```
Handoffs back: an internal DONE card listing PR/branch, tests run + results, deviations (should be none), open questions.

## 4. Parallel run recipe (Claude Code)
1. Orchestrator (main session) creates task cards for the phase.
2. Spawn specialists in parallel, each in its **own git worktree** (`isolation: worktree`) on branch `agent/<role>/<id>`; brief = their internal role definition + task card. Only agents with non-overlapping owned paths run concurrently.
3. Each returns DONE card; orchestrator reviews diff against owner paths + guardrail script, merges in dependency order, resolves contract conflicts.
4. qa-redteam runs after each merge window against the integrated tree and files findings; orchestrator reschedules fixes.
5. Gate review with Drift Checklist (docs/05).

## 5. Phase → task cards (initial backlog)
> **Superseded by docs/08 and the internal P1 task cards.** Ownership and protocol above still apply; P1 runs in a shared folder (no git), not worktrees.
**P0** O-1 contracts+schemas · O-2 CI + guardrail_check + CODEOWNERS · O-3 repo skeleton/Docker compose.
**P1** RE-1 Wright R/F (multi-path, inbred ancestor) · RE-2 Bayes (3 scenarios, detection rate) · RE-3 lock+schema validation · RE-4 goldens + Fraction oracle · DS-1 allele-frequency sampler · DS-2 V1–V5 · DS-3 novelty-gap + ROH flags · DS-4 1,000 cohort · PA-1 signed carrier sets · PA-2 Bloom+blinded APSI · PA-3 Consent store + revocation purge · PA-4 PKCE/scopes/AuditEvent · PA-5 cascade token · FH-1 GenomicReport bundle · FH-2 Variant/Genotype/DiagnosticImplication · FH-3 Phenopacket+Pedigree · FH-4 validator + ref-walker.
**P2** AR-1 orchestrator graph + per-user context · AR-2 VariantInterpreter · AR-3 PedigreeRiskEngine wrapper · AR-4 CulturalCommunicator (stub+real LLM) · AR-5 BioethicsSupervisor 4 gates · AR-6 CounselorCopilot + brief · AR-7 CareNavigator rules · AR-8 loop bus · UI-1 design system tokens/components · UI-2 landing + vault · QA-1 corpus v1.
**P3** UI-3 compatibility+APSI animation · UI-4 residual-risk + teach-back · UI-5 care path + privacy center · UI-6 counselor console · UI-7 AR/RTL pass · QA-2 e2e V1–V5.
**P4** QA-3 eval harness+dashboard · UI-8 polish/motion · DD-1 demo script · DD-2 deck · DD-3 README/reset script.

## 6. Agent anti-drift mechanics
- Every agent's system prompt begins by loading the internal operating contract + docs/01 + its brief (internal files, not published).
- Tool limits: reviewers/qa get read-only + test-run tools; builders get edit tools scoped by instruction + CODEOWNERS enforcement.
- Output must end with a **Guardrail Attestation** block (checklist of invariants touched) — orchestrator rejects work without it.
- "Stop-and-ask" triggers: clinical/legal/privacy ambiguity, contract change need, >2× estimate, desire to add anything not in charter.
- Orchestrator never accepts "done" without seeing test output.
