# API contract v1.3.0 (P5+) — backend `services/api` ⇄ apps, agent-runtime ⇄ qa-redteam

Orchestrator-owned. One FastAPI app (modular monolith, docs/08). Base path `/api`. JSON only. Every response that carries numbers carries the `digest`s of the locked RiskOutputs (contract risk_output v1.1.0) those numbers came from.

## Packages and run command
- Backend app: `services/api/evolve_api/main.py` → `uvicorn evolve_api.main:app --app-dir services/api --port 8000`
- Runtime agents: `services/agents/runtime/` (the package is named `runtime`, NOT `agents`: the repo-root `agents/` folder holds markdown briefs and would shadow it)
- Loop bus: `services/loop/loopbus/`
- The backend imports `risk_engine`, `privacy`, `fhirgen` and `synth` by adding their service dirs to `sys.path` in `evolve_api/bootstrap.py`. No pip installs of our own packages.

## Session (simulated sign-in; SMART/PKCE hardening = P3)
`POST /api/session` `{partner_id}` → `{token, partner_id, scopes:["patient/Observation.rs","patient/DiagnosticReport.r","patient/Consent.cru"], expires_in: 3600}`. Token = bearer header. Every request is scoped to that partner. The counselor uses `{role:"counselor"}` → scopes `user/DiagnosticReport.rs user/Task.cru`. UI label: SIMULATED sign-in.

## Endpoints
| Method & path | Caller | Returns |
|---|---|---|
| `POST /api/demo/reset` | demo | reseeds V1–V5 + cohort; clears consents, workspaces, audit, loop |
| `GET /api/demo/vignettes` | demo | `[{couple_id, label, partner_ids:[A,B]}]` (no genotype data) |
| `GET /api/me/vault` | partner | own calls in plain language + own records where audience ∈ {carrier_partner_only (if carrier_role is me), couple}. Never the other partner's data |
| `POST /api/consents` `{counterpart}` | partner | Consent (consent.schema.json), status active |
| `DELETE /api/consents/{id}` | partner | revoked; couple workspace purged |
| `POST /api/couples/{couple_id}/compatibility` | either partner | `{apsi: ApsiResult, records:[RiskOutput audience=couple], messages:[Message], review_required: bool}` (review_required true ⇒ UI must not show "Compatible" as the headline, e.g. V5). Refused (409) unless both consents are active |
| `GET /api/me/messages` | partner | `[Message]` addressed to me |
| `POST /api/teachback` `{answers:[...]}` | partner | `{passed, score, escalated}` |
| `POST /api/sure` `{answers:[4 bools]}` | partner | `{score, escalated}` (score<4 ⇒ escalate) |
| `GET /api/counselor/queue` | counselor | `[{case_id, couple_id, trigger:"a"|"b"|"c"|"d"|"gate", created_at}]` |
| `GET /api/counselor/briefs/{case_id}` | counselor | Consultation Brief (pedigree summary, consented variant summary, pending Tasks, couple questions) |
| `GET /api/loop/{couple_id}` | partner/counselor | `{state, history:[...]}` (7 states, docs/02 §6) |
| `POST /api/loop/{couple_id}/advance` `{to}` | counselor (HumanClosure: counselor only) | new state |
| `GET /api/guardrail/events` | dashboard | `[{ts, rule, outcome:"blocked"|"rewritten"|"escalated"|"passed", message_id}]` (no message text, no genes) |
| `POST /api/demo/gate-probe` `{recipient_partner_id, draft, lang}` | demo | runs the draft through BioethicsSupervisor only → GateResult. Used for the live "guardrail block" demo |

## Bodies pinned in v1.1.0 (DECISIONS #26–28)
- `GET /api/me/vault` → `{partner_id, calls:[{gene, hgnc_id, condition, condition_ar, classification, zygosity, plain_en, plain_ar, confirmatory_recommended: bool}], records:[RiskOutput]}`. `confirmatory_recommended` is computed by the backend from gene_panel `complex_locus` for the caller's OWN calls only. It is never set on a screen-negative partner's view (DECISIONS #16).
- `GET /api/consents` → `[Consent]` for the caller (both directions: given and received), used for the consent-status UI.
- **Uniform counselor notice:** every partner of every couple gets the same sentence ("A genetic counselor reviews every result and can talk it through with you"). No partner-specific "your case is under review" notice for a screen-negative partner, because a differential notice reveals that the other partner carries something (P-06). Escalation stays visible only to the counselor and to the partner whose own record escalated.
- Demo-only `POST /api/demo/simulate-partner-consent {couple_id}` (SIMULATED badge in UI) replaces the UI's one-off-session workaround.


## P3 additions (v1.2.0, DECISIONS #31) — feed the enterprise surfaces in docs/09
| Method & path | Caller | Returns |
|---|---|---|
| `GET /api/me/home` | partner | `{next_step:{kind, title_key, href}, couple_status:"not_linked"|"invited"|"both_consented"|"result_ready", consent:{status, expires_at}|null, counts:{results, notifications_unread}}` |
| `GET /api/me/activity?limit=` | partner | own AuditEvents only, as `[{ts, actor_role, action, object_kind}]` (no genes, no counterpart identity) |
| `GET /api/me/notifications` / `POST /api/me/notifications/{id}/read` | partner | `[{id, ts, kind, title_key, href, read}]` |
| `GET /api/me/care-plan` | partner | `{loop:{state, history:[{state, ts, actor_role}]}, tasks:[{id, kind, status, due}], appointments:[{id, ts, with_role, status, simulated:true}], options:[{id, title_key, body_key}] /* CareNavigator, unranked */, eligibility:{immediate:bool, checks:[{key, status:"met"|"not_met"|"needs_review", note_key}]} }` |
| `POST /api/me/teachback/start` · `POST /api/teachback` | partner | questions (keys) · result as in v1.0 |
| `POST /api/family/tokens` `{hgnc_id}` | carrier partner, own call only | `{token, qr_payload, expires_at}` (cascade token, no identity) |
| `GET /api/counselor/cases?status=&trigger=` | counselor (on shift) | `[{case_id, couple_id, trigger, priority, opened_at, sla_due_at, couple_status, assigned_to}]` |
| `GET /api/counselor/cases/{id}` | counselor | `{brief, pedigree:{nodes, edges, F, relationship}, variants:[consented scope only], tasks, notes, timeline, access_basis:{couple_consent:bool, on_shift:bool}}` |
| `POST /api/counselor/cases/{id}/tasks` · `PATCH .../tasks/{tid}` | counselor | FHIR-shaped Task |
| `POST /api/counselor/cases/{id}/notes` | counselor | note (stored, audited; no free-text sent to patients without the gate) |
| `POST /api/counselor/cases/{id}/closure` `{summary}` | counselor | loop → HumanClosure (counselor-only, audited) |
| `POST /api/counselor/shift` `{on:bool}` | counselor | online_access session flag; case endpoints 403 when off shift |
All new endpoints obey token scoping, AuditEvent on read, and the error shape. Strings use i18n keys (`title_key`) so the UI owns wording; any free text toward a patient goes through the gate.


## v1.3.0 additions (DECISIONS #62) — counselor AI draft (Sarvam) + deploy config
| Method & path | Caller | Returns |
|---|---|---|
| `POST /api/counselor/cases/{id}/summary-draft` | counselor, on shift | `{draft, provider:"sarvam"|"offline-stub", model, generated_at, ai_generated:true, gate:{passed, violations}, input_fields:[...]}` — English only; built from the consented-scope brief (no partner IDs, no free-text notes); gate runs on the draft (numeric_drift, directive, uae_law, stigma, false_reassurance); a failed gate returns the violations and NO draft text. Never stored on the case, never sent to a patient. 503 `llm_unavailable` on provider error (UI falls back gracefully). |
| `GET /api/config` | any | `{ai_draft_enabled: bool, provider, environment:"local"|"vm"|"vercel-render"}` |
Env: `SARVAM_API_KEY` (absent ⇒ offline-stub provider), `SARVAM_MODEL` (default `sarvam-105b`), `CORS_ORIGINS` (comma-separated; default the three localhost ports), `DEPLOY_TARGET`.

## Message
```json
{"id":"…","to":"V1A","lang":"en|ar","kind":"result|explainer|care|escalation",
 "text":"…","locked_digests":["…"],
 "gate":{"passed":true,"rules":["numeric","leakage","nondirective","uae_law"]},
 "simulated":true}
```
Templates fill the numbers (template-first, docs/08 #7); the LLM is optional and its output always passes through the gate.

## BioethicsSupervisor interface (qa-redteam tests against this)
`runtime.bioethics.check(draft: str, ctx: GateContext) -> GateResult`
- `GateContext`: `recipient_partner_id`, `lang`, `locked_records: list[dict]` (RiskOutputs this recipient may see), `forbidden_terms: list[str]` (other partner's gene symbols, HGNC IDs, HGVS, condition names not in the APSI intersection), `kind`
- v1.1.0 additions to `GateContext` (DECISIONS #23–24):
  - `counterpart_status_hidden: bool`: true unless the APSI intersection is non-empty (the recipient may then hear only about shared genes). When true, ANY statement about the partner's genetic status is a `leakage` violation: carrier/carries/variant/positive/mutation/affected/حامل/طفرة referring to the partner, wife, husband, fiancé(e), spouse or their family, or the Arabic equivalents.
  - `shared_hgnc_ids: list[int]`: the consented intersection.
  - `escalation_required: bool`: true if any locked record for this recipient has escalate=true or status needs_counselor.
- New rule `false_reassurance` (always on): blocks absolute safety claims ("your children are safe", "result is clear", "almost certainly harmless", "cleared automatically", "no need for a confirmatory test", Arabic equivalents). When `escalation_required`, it also blocks anything discouraging, skipping or delaying counseling or testing ("no need to see a counselor", "skip the appointment", "لا داعي لمراجعة"). Structural escalation (CounselorCopilot opens the case) happens regardless of text; this rule only stops the words.
- `GateResult`: `{passed: bool, violations: [{rule: "numeric_drift"|"leakage"|"directive"|"uae_law"|"missing_judicial_statement"|"stigma"|"false_reassurance"|"gate_error", detail: str}]}`
- Deterministic, no network. Errors and timeouts are a fail (fail-closed).

## Error shape
`{"error": {"code": "...", "message": "..."}}` with no PHI or genes in messages.
