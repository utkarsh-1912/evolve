# 01 — Guardrails (strict, enforced, anti-deviation)

Three layers: **(A) Scope guardrails** keep us on the project. **(B) Product invariants** keep the product safe and lawful. **(C) Process/mechanical enforcement** makes violations fail CI rather than rely on goodwill. Every rule has an ID; PRs cite which they touch.

## A. Scope guardrails (anti-drift)
| ID | Rule | Enforcement |
|---|---|---|
| G-01 | Every change maps to a requirement ID in `docs/00-CHARTER.md`. No ID → no merge. | PR template + `scripts/guardrail_check.py --pr-body` |
| G-02 | Out-of-scope list in the charter is binding. | Orchestrator review; forbidden-term scan |
| G-03 | The seven runtime agents and their names are fixed. No new agent, no merged agent. | `guardrail_check.py` verifies `contracts/agents.json` == the seven |
| G-04 | Contracts (`contracts/*`) change only via orchestrator-approved PR with version bump. | CODEOWNERS + golden-vector check |
| G-05 | Each build agent edits only its owned paths. | CODEOWNERS; `guardrail_check.py --owned-paths` |
| G-06 | Dependencies: allow-list in `scripts/allowed_deps.txt`; new dep needs a one-line justification in PR. | CI diff check |
| G-07 | The source architecture doc outranks all other docs. Conflicts → `handoffs/QUESTION-*.md`, not silent decisions. | Process |
| G-08 | Timebox: a task exceeding its estimate by 2× is escalated to orchestrator, not extended. | Orchestrator |
| G-09 | No "while I'm here" refactors or features. | Reviewer |

## B. Product invariants (a violation is a P0 bug)
**Computation**
- P-01 **Zero numerical drift.** Any number in user-facing text must exist verbatim in the locked `RiskOutput` JSON for that session. Gate: `BioethicsSupervisor.rule1`.
- P-02 Risk math lives only in `services/risk_engine`. No arithmetic on probabilities in agent, UI or prompt code. Lint: ban `*`/`/` on fields named `*risk*|*prob*|*freq*` outside risk_engine (AST check).
- P-03 `F` (inbreeding) must never be used alone to counsel risk for a tested gene when molecular results exist (source §2.3). Output schema carries `fusage: "genome_wide_context_only"`.
- P-04 A screen-negative partner in a discordant couple is **never** labelled "no risk"; residual risk is shown with assay detection rate. Technically complex loci (CYP21A2, SMN1) ⇒ confirmatory FHIR Task before reassurance.
- P-05 VUS in ROH >10 Mb or red-flag pedigree ⇒ automated clearance suppressed.

**Privacy**
- P-06 **Zero cross-partner leakage.** Outbound message to user X contains no gene/variant/history of partner Y unless in the consented intersection. Gate: `rule2`.
- P-07 APSI runs only with two valid, unexpired, unrevoked Consent resources. Revocation terminates the workspace token and purges couple state ≤ 5 s (tested).
- P-08 Per-user LLM context. No shared conversation memory across partners. Couple workspace stores intersection genes only.
- P-09 Gene sets enter APSI only if authority-signed; client-fabricated sets rejected.
- P-10 Scopes are granular (`patient/Observation.rs`, never `patient/*.*`). Tokens ≤ 1 h. Every read writes an `AuditEvent`.
- P-11 Synthetic data only. No real genome/PHI, no secrets, no real person's data in fixtures or prompts. Population-health queries use small-cell suppression (k ≥ 10).
- P-12 Logs/traces never contain variant strings or gene symbols (redacted IDs only).

**Ethics & law**
- P-13 **Non-directive.** Blocklist + classifier for "you should (not) marry/cancel/proceed/terminate". Gate: `rule3`.
- P-14 **Judicial decoupling.** Result screens state: the health certificate is issued regardless of genetic result.
- P-15 No success metric, chart, or copy references marriage cancellation.
- P-16 **UAE statutes (rule4).** Block: donor sperm/eggs/embryos (Fed. Law 11/2008). Require written consent of both spouses before any PGT-M step (Fed. Law 7/2019). Any fetal-anomaly question ⇒ immediate route to licensed MFM physician + accredited genetic counselor with no advice given (Art. 16 Medical Liability Law / Cabinet Res. 44/2024). Never state gestational limits or procedures to the user as guidance — only the human clinician does.
- P-17 Non-stigmatizing language: consanguinity is never "a mistake"; carrier ≠ diagnosis; always absolute **and** relative risk.
- P-18 Escalation is mandatory (CounselorCopilot a–d). No path lets the LLM skip it.
- P-21 LLM output is allowed ONLY counselor-side as a labelled, gate-checked AI draft for human review (DECISIONS #62); never patient-facing.
- P-19 UI carries a persistent "decision support — not a diagnosis or medical advice" notice. Simulated integrations are labelled `SIMULATED`.
- P-20 If a clinical, legal, or numeric fact is not in the source doc: `TODO(verify)`, never invented.

**Fail-safe default:** any gate error/timeout ⇒ message **not sent**, session routed to human counselor, event logged. Safety gates fail closed.

## C. Mechanical enforcement
1. `scripts/guardrail_check.py` (run locally, in pre-commit, and in CI). Checks: agent roster, forbidden phrases in source/copy, banned patterns (`patient/*`, real-looking IDs, secrets), `risk*` arithmetic outside risk_engine, contracts version, unlabelled mocks. Exit ≠ 0 blocks merge.
2. `tests/guardrails/` red-team corpus (qa-redteam): directive prompts, leakage probes, donor-gamete probes, anomaly-termination probes, number-tampering. Must be 100% intercepted; CI gate.
3. Golden vectors (`tests/golden/risk_vectors.json`): changing any value requires orchestrator sign-off.
4. CODEOWNERS + branch protection: orchestrator + qa-redteam approval required for `contracts/`, `agents/bioethics*`, `services/risk_engine/`, `services/privacy/`.
5. Claude Code project config (`.claude/settings.json`, `.claude/agents/*`) restricts tools per build agent; read-only for reviewers.
6. Drift review ritual: at each phase gate the orchestrator runs the **Drift Checklist** (docs/05 §Gates): requirements traced? any unowned file changes? any new dependency/agent/metric? any invariant weakened?

## Deviation protocol
Spot a conflict, ambiguity, or tempting extra? → stop → `handoffs/QUESTION-<n>.md` (what, which rule, options) → orchestrator decides → decision recorded in `docs/DECISIONS.md`. Silent deviation = revert.
