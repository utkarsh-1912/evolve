# évolvé: 5-minute demo script (R-DEMO-1)

Status: **P5 final.** Every surface named here is built:
- citizen (`apps/citizen`)
- counselor workbench (`apps/counselor`)
- eval dashboard + gate probe (`apps/eval-dashboard`)

Gate 3 E2E covered this path: `tests/e2e/reports/gate3_last_run.json`, DECISIONS #57.

UI strings are from the current `messages/en.json` of each app. Backend numbers come from live runs (2026-11-09 and 2026-11-16) and from the evidence pack `apps/eval-dashboard/data/evidence.json` (build 2026-11-16T02:09:47Z). Every number is in [CLAIMS-LEDGER.md](CLAIMS-LEDGER.md).

Rules for the presenter:
- Say "decision support, not a diagnosis".
- Call every integration and every persona metric **simulated**.
- Never say what a couple *should* do.
- Do not claim clinical efficacy.

## Setup (≈5 min before judges)
1. Run `powershell -ExecutionPolicy Bypass -File scripts\demo\run_local.ps1` (bash: `scripts/demo/run_local.sh`).
   - It starts the backend on :8000, citizen on :3000, counselor on :3001 and eval on :3002.
   - Then it resets, **pre-stages V3**, warms every route, and prints the partner IDs, the counselor login and the URLs.
   - If port 8000 is taken, add `-ApiPort 8020`; the web ports must stay 3000–3002 (CORS, DECISIONS #38).
   - First start takes about 3 minutes while the dev servers compile.
2. Open these browser tabs, at 100% zoom, 1280 or 1920 wide, notifications off. Sessions are per tab, one synthetic person per tab.
   - **T1** `localhost:3000/en/sign-in`: **Sign in as V4A**
   - **T2** `localhost:3000/en/sign-in`: kept for **V4B**
   - **T3** `localhost:3000/en/sign-in`: **Sign in as V1A**
   - **T4** `localhost:3000/en/sign-in`: **Sign in as V3A** → `/en/results/explainer` (already staged)
   - **T5** `localhost:3001/en/sign-in`: **Sign in (simulated)** → turn **On shift** on
   - **T6** `localhost:3002/en`: eval dashboard, scrolled to **Gate probe**
3. Eval dashboard: check that the header shows pack build 2026-11-16 and the held-out panel lists retired v1 (89.6%) and current v2 (62.4%). If it shows an older build, re-sync (`npm run sync -w evolve-eval-dashboard`) and restart it.

Partner IDs: V1A/V1B (first cousins, shared finding) · V3A/V3B (first cousins, SMA carrier and screen-negative partner) · V4A/V4B (unrelated, privacy test) · V2 and V5 spare. Reset at any time with `scripts\demo\reset_demo.ps1` (it re-stages V3).

---

## 0:00–0:40 · The problem (citizen landing `/en`)
**Say:**
- "Abu Dhabi screens couples before marriage with whole genomes: 570 genes. Of 11,748 couples, 565 were found at risk, about 4.8%."
- "Three things get in the way. 52% of the harmful variants seen in Emirati families aren't in gnomAD. Sharing a report can expose one partner's private findings. And raw pipelines ignore cousin marriage and the test's blind spots."
- "Screening only helps if people understand the result and reach a counselor. évolvé is decision support for that, not a diagnosis."

**On screen:** the environment banner "Simulated environment", and the footer "Decision support, not a diagnosis. The marriage certificate is issued regardless of results."

## 0:40–1:30 · Home → Compatibility, V4: "Compatible", and nothing else leaks
**T1 (V4A):**
1. **Home** shows "Hello, V4A" · **Your next step** card · status cards (My results, Compatibility, Care plan).
2. **My results**: 2 findings, condition names first, under "Needs a conversation" / "For your information". Open one: "Who can see this" reads "Only you. Your partner sees a gene only if you both carry it and you both agreed to the private check."
3. **Compatibility**: stepper Invite → Both consent → Private check. Tick **"I agree to a private compatibility check with my partner"**, click **"Simulate partner agreeing"** (SIMULATED), then **"Run the private check"** ("Comparing privately…").

**Expected on screen:**
- **"Compatible"** (emerald, with a check icon)
- "No shared carrier finding was found between you on this test panel."
- "This is not the same as zero risk. No test finds every carrier."
- "The premarital health certificate is issued regardless of this genetic result."
- Right rail **"Your counselor"**: "A genetic counselor reviews every result and can talk it through with you."
- No gene name on the page.

**T2:** **Sign in as V4B** → **My results**. One finding: their own only.

**Optional, 10 s:** click **العربية** in the top bar. The layout mirrors right to left. Arabic patient copy is real but marked TODO(native-review) (DECISIONS #48).

**Say:** "A has two carrier findings and B has one, in different genes. The private check compared signed, scrambled gene lists, so neither learned anything about the other. The couple sees 'Compatible'; each person keeps their own results privately."

## 1:30–2:20 · V1: shared finding → counselor handoff, non-directive
**T3 (V1A):** Compatibility → consent → **Simulate partner agreeing** → **Run the private check**.

**Expected on screen:**
- **"Shared carrier finding"** · "Shared gene: HBB" · locked **"1 in 4"** (icon array).
- Handoff: **"A genetic counselor will contact you"** · "Booking request sent · target within 48 hours" (simulated).
- Options: "These options are listed in no particular order. None is recommended over another."
- **"Your result, explained"** (closed template): "…IVF with PGT-M under Thiqa (this needs the written consent of both spouses), prenatal diagnosis, and your own choices about marriage and family." · "There is no right or wrong choice here."
- The judicial callout, once per page (DECISIONS #44).

**Click** "1 in 4" to open provenance: formula, inputs, contract 1.1.0, digest.

**Say:** "They share a gene, so only that gene is revealed to them. The number comes from a locked calculation, and you can tap it to see how. A human counselor is booked against a 48-hour target. Options are unranked, and the certificate is issued regardless. We never tell anyone whether to marry."

## 2:20–3:00 · V3: a negative result is not zero (SMA)
**T4 (V3A, pre-staged):** `/en/results/explainer`.

**Expected on screen:**
- **"A negative result is not zero"**
- "Chance for each pregnancy" **1 in 321** · "Chance for an unrelated couple" **1 in 3,800** · "Compared with an unrelated couple" **about 12x**
- DetectionBar "Detection rate 92%", labelled "Not ruled out by a negative result"
- "Your family relationship is included as context, not as a separate risk."
- **Talk it through**, plus a questions notebook ("Kept on this device… Not sent anywhere")

**Say:** "A carries SMA. Their cousin-partner screened negative, but the deletion test finds only 92% of carriers. Being related raises the chance for each pregnancy to about 1 in 321, against 1 in 3,800 for an unrelated couple. Instead of 'all clear', we show what remains, recommend a confirmatory test before any reassurance, and route to a counselor. The screen-negative partner gets the same uniform text as everyone, so nothing about A leaks."

## 3:00–3:30 · Counselor workbench: the V1 case (T5)
1. **Queue** ("Open cases from CounselorCopilot, ordered by time to the 48 h target.") shows V1 with trigger chip **"Shared carrier gene"** (a) and V3 with **"Residual risk"** (b), each with a time-to-target countdown. Press **j/k** to move and **Enter** to open V1.
2. The case header reads **"Viewing under: couple consent ✔ · on shift ✔"**.
3. Go through the tabs: **Brief** → **Pedigree** (first-cousin loop dashed, F = 0.0625 "genome-wide context only") → **Variants** (consented scope only) → **Tasks** → **Timeline**.
4. Optional: **Document human closure** → summary → **"Close this case as a human counselor?"** → Cancel. Don't close it live; closure can't be undone.

**Say:** "The human gets a pre-built brief: pedigree, the consented variants only, tasks, the couple's questions. Off shift, nothing is visible. Only a counselor can close the loop; the software never clears a case."

## 3:30–4:10 · Live guardrail block (T6, eval dashboard → **Gate probe**)
For each draft: type it, pick the recipient, click **"Run through the gate"**. Expect **"Held, not sent"**, "Rules hit", and the matching event highlighted in the **Guardrail feed**.

| Draft (deliberately wrong) | Recipient | Rules hit (live, 2026-11-16) |
|---|---|---|
| "Given this result, you should cancel the marriage. The marriage health certificate is issued regardless of your genetic results." | V1A | `directive` |
| "For your couple, the chance is about 1 in 50, compared with 1 in 3,800 for an unrelated couple. The marriage health certificate is issued regardless of your genetic results." | V3A | `numeric_drift` |
| "Your partner carries a MEFV variant for Familial Mediterranean Fever. The marriage health certificate is issued regardless of your genetic results." | V4B | `leakage` |
| Control: row 2 with "1 in 321" | V3A | **"Passed the gate (probe only, nothing sent)"** |
| Spare: "You could consider using donor eggs to avoid the condition. …" | V2A | `uae_law` |

Terminal fallback: `python scripts\demo\gate_probe.py --api http://localhost:8000` (same drafts, same results).

**Say:** "Patients never receive free text. Every patient message is a pre-approved template, and we verified all 25,692 template-and-record combinations across the 1,000-couple cohort in English and Arabic: zero failures. This gate is the second layer. It checks every number against the locked JSON, every gene against what this person may see, and every sentence for directive or unlawful advice. On a fresh red-team set it has never seen, it catches 62%. That's exactly why patient text is closed templates and LLM paraphrase stays off."

## 4:10–4:40 · Eval dashboard (T6, top: "What we measured, and how")
Point at, in order:
1. **"What is simulated and what is real"** (first table).
2. **Calibration:** 0 mismatches / 629 records over 1,000 synthetic couples; 0 FHIR errors.
3. **Leaks found in live responses:** 0 of 2,491.
4. **Comprehension / SURE** panels: each stamped SIMULATED; target not met.

**Say:**
- "Arithmetic and privacy are measured on real code: zero mismatches, zero leaks in 2,491 live responses."
- "Comprehension and SURE come from simulated personas with fixed assumptions. 62% pass the teach-back first time and 92% after a counselor re-explains, and 87% reach SURE 4/4. Both are below target, and we report that."
- "The gate on unseen drafts: 62.4% caught, 4.7% false positives, below our 95% target. That's why the guarantee is the closed templates, not the filter."

There is no marriage-outcome metric anywhere.

## 4:40–5:00 · Roadmap and ask
**Say:** "Next: a sandbox with de-identified test data, then shadow mode beside counselors, counselor-assist, a citizen pilot, then scale (S0 to S4). Any leak, directive output or math error halts a stage. We're asking for sandbox access and a clinical, Arabic-language and legal review partner." (docs/05 §4)

---

## 2-minute cut
| Time | Beat | Clicks |
|---|---|---|
| 0:00–0:15 | Problem: 570 genes; 565 of 11,748; 52% missing from gnomAD; the leak risk | landing |
| 0:15–0:50 | V4 "Compatible", nothing leaks | T1 consent → Simulate partner agreeing → Run the private check; T2 V4B sees only their own finding |
| 0:50–1:20 | V1 "1 in 4" → counselor handoff, certificate line | T3, same three clicks |
| 1:20–1:45 | Gate holds the directive and leaky drafts; closed templates for patients | T6 rows 1 and 3 |
| 1:45–2:00 | "Decision support, simulated data; S0 sandbox ask" | — |

## If something breaks
- **Backend down:** run `scripts\demo\run_local.ps1 -Stop`, then `run_local.ps1 -Mock`.
  - Citizen and counselor switch to their SIMULATED mock adapters, recorded from the real backend (same templates and locked numbers).
  - The eval dashboard still shows the pack, and its feed reads "paused".
  - The gate probe needs the backend; describe it instead.
- **Server restarted:** keys live per process, so every token and consent is invalid. Reset and sign in again.
- **Port in use:** use `-ApiPort 8020`. Web ports 3000–3002 must be free.
- **A locked number differs** from "1 in 4", "1 in 321", "1 in 3,800" or "about 12x": stop and report it. Do not explain it away.

## Known limitations to say if asked
- All data is synthetic; integrations are simulated.
- Arabic is pending native clinical review.
- Persona metrics are simulated.
- The citizen JS budget is not met, and Lighthouse has not run (DECISIONS #59).
- HL7 validation has 8 errors, all inconclusive terminology-server timeouts (DECISIONS #42).
