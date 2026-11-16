# 03 — UI / UX Design (v3: évolvé brand + full-page captures of eddyrlora.com, reminous.com, inception42.ai)

## 0. Brand: évolvé (team brand — overrides any color/type choice below)
Logo supplied by the team: white lowercase geometric wordmark **évolvé** with the "o" in lime, beside a radial "sunburst/clock" mark of white dashes with **one lime stroke at 12 o'clock**, on deep navy. Sampled from the logo file:
| Token | Hex | Use |
|---|---|---|
| `--evolve-navy` | `#00357D` | brand ground, primary buttons on light, app bar, counselor-console accents |
| `--evolve-navy-2` | `#114285` | hover/raised navy surfaces |
| `--evolve-lime` | `#C1FF72` | **brand accent only**: logo "o", primary CTA on navy/dark, focus ring, the one highlighted step. Never a status color. |
| `--evolve-cream` | `#FFFEF0` | wordmark white on navy, warm paper accents |
| `--evolve-mist` | `#AFBFCC` | secondary text on navy, dividers |
Rules: the logo is used as supplied (no recolor, stretch, or effects); minimum clear space = height of the "é"; on light grounds use the navy version (TODO: request the navy/mono logo variants from the team). Product name for the app is **TODO(team)**; until decided, UI shows "évolvé" + descriptor "Inherited risk, explained" (descriptor wording TODO(team)).
**Mark → motion:** the sunburst's dashes double as our progress indicator (each dash = a closed-loop step; the lime stroke = "you are here") and as the loader, alongside the two-circle Venn for anything about partners/APSI.
**Status-color change (from v2):** because lime is now the brand accent, "Compatible" moves to emerald `#1F9D6B` (with check icon + text). Signal colors stay meaning-only: Compatible emerald · Review amber `#F5A524` · Escalated coral `#F0556B` · Private vault violet `#7A5AF8`.

v1 was based on viewport-only looks. v2 is based on the full-page captures you supplied (8 pages each) plus inception42.ai. Reference renders are kept outside the repo; colors below were sampled from them.

## 1. What each reference actually is
**eddyrlora.com — "Ledger" (dark editorial monochrome).** Near-black `#141412` sections alternating with warm paper-grey `#E5E4E0` sections; the grey sections have large rounded top corners that "slide up" over the black. Film-grain noise over everything. Heavy condensed grotesque headlines (tight tracking), small body text, tiny mono captions. Black-and-white photography only. Sections: pill nav → hero (gradient/blur, giant name) → About (stacked photos + two-column text + credentials) → marquee photo strip → giant split-word header with logo inserted ("EQUITY [logo] RESEARCH") → feature with document preview → "logged changes" table (Old / New / Why) → histogram → **scroll-pinned step list that fades unread text** beside a **terminal panel** (checklist with done/matched/ready; `pytest … 364 passed`) → experience cards with logo rows → heat-map grids (contributions) with huge counter numerals → "GET [photo] IN TOUCH" → full-width wordmark in a rounded paper panel. Tone: evidence over adjectives — every figure carries a source line, "simulated for the animation" disclosures.

**reminous.com — "Clinic-blue" (cool, trustworthy product).** Ground `#F6F7FB`, tiles `#ECF1F7`, ink navy `#0A1225`/`#0E1A33`, blue `#2E62C8`, light blue `#9CC2FF`. One-ink duotone navy photography. Switzer-like sans, display weight with tight tracking; mono (JetBrains) for meta. Elements: status banner above nav · rounded-pill nav with navy CTA · hero photo card with big white headline and a floating **inline-fill sentence form** ("We run ___ , and we want ___" + suggestion chips + Continue) · quiet 4-column summary row · full-bleed photo with headline · **numbered tab cards 01–06** that drive a content area · **three-panel split "We / AI / Automation"** (navy / light-blue / royal-blue cards, each listing tasks with status pills `done`, `built`, `checked`, `on`) · sample dashboard with KPI tiles, hatched "last week" bars, table, a "The numbers / How they were counted" toggle, and a caption "A sample. No client is shown, and no number here is a result." · case-study block · notes cards · **"Six rules every account runs on"** table with a toggle/pill per rule · inline-underlined links · 3-step "what happens next" · contact form · **halftone-dot footer wordmark**.

**inception42.ai (G42 group, Abu Dhabi) — "Sovereign" (full capture, 5 pages).** Lavender-white ground `#FBF8FF`, charcoal `#1F1F1F` sections, electric lime `#91FE02`, one violet block `#AE73FF`. Wide geometric grotesque (licensed abcDiatype / Lineca). Patterns:
- full-bleed cinematic photo hero with a thin glass header bar, light-weight large headline bottom-left, short paragraph + CTA bottom-right
- **chamfered full-width CTA bars** (arrow-pointed ends, lime, uppercase small label, chevron right)
- **corner-bracket marks** (⌟ ⌜) framing statement paragraphs, plus a small dash before them
- **12-column hairline grid**: uppercase micro-label in a left column ("OUR PRODUCTS"), content in the right column, 1 px rules between rows
- statement paragraphs with a **bold lead phrase** then regular text
- photo mosaic of product tiles with white logo-mark + name overlay; carousel with progress bar + square arrow buttons
- dark section with blurred photo background, portrait card left, **giant thin numerals with small unit suffix** ("32 models", "33 %")
- full lime block statement next to a dark label column
- **value list**: 4 rows on dark, two-line light title left, small body right, hairline separators
- "Human-led." collage hero; violet label block + partner logo row with short captions
- news cards (photo, tag, title, date, "Open ›"); two-up CTA cards (light / dark); dark footer with accordion link groups
- **cookie banner with Reject and Accept** (we default to reject non-essential, P-11)

## 2. Our concept: "Two circles, one overlap" + "Show your work"
- Each partner = private circle; only the consented overlap is ever drawn (APSI). The Venn is logo, loader, and result.
- Both references share one ethic we want as brand: **every number is sourced, every sample is labelled.** Our `LockedNumber` + `SIMULATED` badge are that ethic as components. Capture-style captions: "A simulated couple. No real person is shown and no number here is a clinical result."

## 3. Two themes, one system (token-switchable)
| | **Clinic** (default — citizen app, landing, care path) | **Ledger** (counselor console, eval dashboard, "under the hood" pages, demo finale) |
|---|---|---|
| Inspired by | Reminous | Eddy R. Lora |
| Ground | `#F6F7FB` · tile `#ECF1F7` · card `#FCFDFF` | `#141412` · panel `#1A1A1A` · paper `#E5E4E0` |
| Ink | `#0A1225` / secondary `#5B6478` | `#E9E8E4` on dark · `#141412` on paper |
| Accent | blue `#2E62C8` · soft `#9CC2FF` | monochrome; single white pill CTA |
| Brand layer (both) | évolvé navy `#00357D` replaces Reminous blue as primary in Clinic; évolvé lime `#C1FF72` is the single accent in both themes (CTA, focus, "you are here") |
| Signal colors (both) | Compatible = emerald `#1F9D6B` · Review = amber `#F5A524` · Escalated = coral `#F0556B` (calm, never alarm-red) · Private vault = violet `#7A5AF8` |
| Imagery | Duotone navy photography / halftone | B&W grain photography / charts on paper |
| Texture | none (halftone dots on hero + footer) | film grain overlay (2–3% noise) |
Rule: **signal colors carry meaning only** (never decoration); every status also has an icon + text (color-blind safe).

**Photography policy:** use stock/AI-free licensed imagery or our own illustrations; apply the one-ink duotone filter via CSS (`mix-blend-mode` + gradient map) so any image fits. No real patient images; no faces implying a diagnosis.

## 4. Type
Display: **Lexend or Sora** (free geometric, close to the évolvé wordmark and inception42's wide grotesque) for brand headlines and big numerals; tight-tracked **Instrument Sans / Inter Tight** for Clinic UI; **Archivo Narrow / Barlow Condensed** for Ledger giant headlines. Body: Instrument Sans 16–18 px. Mono captions/meta: **JetBrains Mono** 12 px uppercase-optional. Arabic: **IBM Plex Sans Arabic** (+ Noto Kufi Arabic for display). Do not use Switzer/abcDiatype (licensed). Display sizes via `clamp()`; giant wordmark panels at 18–22 vw.

## 5. Layout & motion vocabulary (lifted patterns → our usage)
| Pattern from references | Our use |
|---|---|
| Status banner above nav (Reminous) | Persistent "SIMULATED ENVIRONMENT · synthetic data only" bar (satisfies P-19) |
| Pill nav + single filled CTA | Same; CTA = "Check compatibility" |
| Hero photo card + big white headline | Landing: duotone hero, headline "Understand your results. Share only what you choose." |
| **Inline-fill sentence form** + chips | **Onboarding intake**: "I'm preparing for ___ and I'd like to understand ___" (chips: premarital screening · planning a family · a relative's result). Non-directive wording. |
| Numbered tab cards 01–06 | The **7-state closed-loop tracker** (Result issued → … → Human closure) |
| **We / AI / Automation 3-panel** | **Who does what: People · Calculator · Assistant** — human counselors (navy), deterministic risk engine (blue), LLM language assistant (light-blue) with the status pills. Explains neuro-symbolic safety to citizens and judges in one picture. |
| Sample dashboard + "How they were counted" toggle | Result screen: flip a switch on any number to show its provenance (`LockedNumber` → formula, inputs q/d/R, contract version, digest) |
| Hatched "last week" bars | Residual-risk **DetectionBar**: solid = detected by test, hatched = what a negative result can't rule out |
| "Six rules every account runs on" | Public **"Seven promises"** page: each guardrail (non-directive, no leakage, numbers locked, certificate regardless, human counselor on flag, synthetic data, you can revoke) as a row with a live status pill |
| Workflow graph (n8n panel) | Counselor/judge view of the **agent graph** with live events |
| Scroll-pinned text that fades unread lines (Eddy) | Explainer pages (carrier ≠ diagnosis; negative ≠ zero) — reading-progress highlight |
| **Terminal panel with checklist/pytest** (Eddy) | **Guardrail & Test panel** on eval dashboard: live feed "✔ numeric-drift gate · ✖ blocked directive draft · 1,000/1,000 couples matched oracle · 364 passed". Real numbers from CI artifacts, labelled with build time. |
| Heat-map grid + giant counter | Cohort grid (1,000 couples as dots coloured by scenario) + giant "0" leakage counter |
| Histogram vs "what I measured" line | Calibration chart: distribution of residual risk across cohort with the vignette marked |
| "Old / New / Why" change table | Audit trail & "what changed since your last result" (re-issued report status=amended) |
| Source/caption line under every chart | Mandatory `SourceCaption` component on every number-bearing visual |
| Rounded-top paper section sliding over black | Ledger-theme page transitions; Clinic uses soft 28 px card radii |
| Halftone wordmark footer | Brand footer: évolvé logo on navy over a halftone Venn |
| Chamfered lime CTA bar (inception42) | Primary action on landing and step transitions ("CHECK COMPATIBILITY ›"); at most one per screen |
| Corner brackets + micro-label grid (inception42) | Section framing for explainer and "Seven promises" pages; micro-labels uppercase mono |
| Giant numerals with unit suffix (inception42) | Locked results, e.g. "1 in **321**" with source caption; always via `LockedNumber` |
| Lime statement block (inception42) | One "what this means for you" block per result, non-directive copy only |
| Value-list rows on dark (inception42) | "How we protect you" rows: Private by design · Numbers you can check · People, not just software · You decide |
| Cookie banner Reject/Accept | Consent banner; non-essential off by default |
| Sunburst mark (évolvé) | Closed-loop progress ring + loader |
| Giant split-word header with inline image | "TWO [overlap] CIRCLES" signature section on landing |
Motion: scroll-linked reveals ≤ 600 ms, ease-out; Venn slide ≤ 1.2 s; halftone reacts to pointer (canvas, 60 fps budget); all disabled under `prefers-reduced-motion` with static equivalents. Counters animate **only** to values from locked JSON.

## 6. Information architecture
**Citizen app (`apps/citizen`, Clinic, EN/AR full RTL):** Landing → Intake sentence → Sign-in (SIMULATED UAE-Pass screen) → My Vault (private) → Compatibility (invite → dual consent → APSI → result) → Residual-risk explainer → Teach-back → Care path tracker → Family token → Privacy center (consents + audit) → Seven promises → SURE micro-screen.
**Counselor console (`apps/counselor`, Ledger):** queue by trigger (a–d) · consented couple view · pedigree · variant summary · pending Tasks · Consultation Brief · agent graph · document human closure.
**Eval dashboard (`apps/eval-dashboard`, Ledger):** five metric panels + cohort grid + calibration histogram + guardrail terminal feed; everything SIMULATED-stamped.

## 7. Components (build list)
`StatusBanner` · `PillNav` · `OverlapCircles` · `HalftoneField` · `GrainOverlay` · `InlineSentenceForm` · `ThreePanelSplit` · `NumberedTabs` · `LockedNumber` (+provenance toggle) · `SourceCaption` · `SimulatedBadge` · `DetectionBar` · `IconArray` (1-in-4) · `ConsentToggle` · `StateTracker` · `PromiseTable` · `TerminalPanel` · `CohortGrid` · `Histogram` · `AuditTable` · `GuardBanner` · `LangSwitch` · `GiantWordmark` · `AgentGraph`.

## 8. Copy rules (scanned in CI)
Non-directive; numbers only via `LockedNumber`; every risk shown absolute **and** relative; carrier ≠ diagnosis; never "mistake"; grade-8 reading level; tone = Reminous plain-spoken ("what ran, what it cost, how each number was counted" → "what we found, how likely, how it was counted"). Arabic reviewed by a native clinical speaker — `TODO(verify)`.

## 9. Quality bars
WCAG 2.2 AA (check contrast of grey-on-dark captions — the references' faded text would fail; we don't copy that), 360 px min, tap ≥44 px, Lighthouse ≥90, RTL screenshot tests, reduced-motion, keyboard complete.

## 10. Demo-critical screens (build first)
Landing (Clinic hero + Venn) → Intake sentence → Compatibility V4 "Compatible" → V1 + counselor handoff → V3 residual-risk with DetectionBar + provenance toggle → People/Calculator/Assistant panel → Ledger eval dashboard with terminal guardrail feed.

## 11. Do-not-copy
Logos, copy, photos, fonts, the "Eddy"/"Reminous"/"Inception"/"G42" names or any text. We reproduce *layout patterns and token logic* only. The only logo we ship is the team's own évolvé mark.
