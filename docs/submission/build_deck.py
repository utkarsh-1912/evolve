"""Fill the official submission template (layout untouched; content added under each heading).
Numbers come from services/eval/out/evidence.json and handoffs/DONE-*.md (see docs/demo/CLAIMS-LEDGER.md).
"""
import sys, pathlib
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

ROOT = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
prs = Presentation(str(ROOT / "docs/submission/submission-template.pptx"))
S = prs.slides

NAVY, LIME, INK, MUTED = RGBColor(0x00, 0x35, 0x7D), RGBColor(0xC1, 0xFF, 0x72), RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x78)
EMERALD, CORAL, AMBER, TINT, WHITE = RGBColor(0x1F, 0x9D, 0x6B), RGBColor(0xC0, 0x39, 0x4B), RGBColor(0xB7, 0x79, 0x1F), RGBColor(0xEE, 0xF2, 0xF8), RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Calibri"
X0, Y0, W = 0.35, 1.62, 9.3  # content frame under the template heading


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, name=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name: tb.name = name
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.03)
    for i, p in enumerate(paras):
        t, size, bold, color = (p + (False, INK))[:4] if len(p) < 4 else p
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.space_after = Pt(3)
        r = para.add_run(); r.text = t
        r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color; r.font.name = FONT
    return tb


def card(slide, x, y, w, h, title, body, fill=TINT, tcolor=NAVY, size=10.5):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.08; s.fill.solid(); s.fill.fore_color.rgb = fill; s.line.fill.background(); s.shadow.inherit = False
    s.name = f"card: {title}"
    text(slide, x + 0.1, y + 0.06, w - 0.2, h - 0.12,
         [(title, size + 1, True, tcolor)] + [(b, size, False, INK) for b in body])


def box(slide, x, y, w, h, label, fill=NAVY, color=WHITE, size=10):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.15; s.fill.solid(); s.fill.fore_color.rgb = fill; s.line.fill.background(); s.shadow.inherit = False
    s.name = f"box: {label}"
    tf = s.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.05)
    lines = label.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = ln; r.font.size = Pt(size if i == 0 else size - 1.5); r.font.bold = i == 0
        r.font.color.rgb = color; r.font.name = FONT


def arrow(slide, x, y, w=0.28, h=0.22, down=False):
    s = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW if down else MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = MUTED; s.line.fill.background(); s.shadow.inherit = False; s.name = "arrow"


def table(slide, x, y, w, rows, col_w, size=10, row_h=0.32):
    shp = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    t = shp.table
    for j, cw in enumerate(col_w): t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.text = ""; c.margin_left = c.margin_right = Inches(0.05)
            c.margin_top = c.margin_bottom = Inches(0.02)
            p = c.text_frame.paragraphs[0]; r = p.add_run(); r.text = val
            r.font.size = Pt(size); r.font.name = FONT; r.font.bold = i == 0
            r.font.color.rgb = WHITE if i == 0 else INK
            c.fill.solid(); c.fill.fore_color.rgb = NAVY if i == 0 else (TINT if i % 2 else WHITE)
    return shp


# ---------- 1. Cover: append values to the template's own label runs ----------
vals = ["évolvé", "1", "Fertility: Understanding and Reducing Inherited Disease Risk"]
labels = [sh for sh in S[0].shapes if sh.has_text_frame and "Team Name" in sh.text_frame.text][0]
for p, v in zip([p for p in labels.text_frame.paragraphs if p.runs], vals):
    src = p.runs[-1]; r = p.add_run(); r.text = " " + v
    r.font.size = src.font.size; r.font.bold = False
    if v.startswith("TO FILL"): r.font.color.rgb = CORAL

# ---------- 2. Team members table: team fills (left as template) ----------
members = [["1", "Utkarsh Gupta", "India", "Senior Software Engineer", "Sosuv", "24"]]
tbl = [sh for sh in S[1].shapes if sh.has_table][0].table
for i, row in enumerate(members, start=1):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j); para = cell.text_frame.paragraphs[0]
        for r in list(para.runs): r.text = ""
        r = para.add_run(); r.text = val; r.font.size = Pt(12); r.font.color.rgb = INK

# ---------- 3. Capability summary (<= 1,000 characters) ----------
cap = ("évolvé builds privacy-first clinical decision support for Abu Dhabi's premarital genomic screening. "
       "Our working prototype combines: deterministic genetic-risk mathematics (Wright coefficients, Bayesian residual risk) "
       "that reproduces published vignette figures exactly; cryptographic private set intersection so partners see only "
       "shared findings; HL7 FHIR R4 Genomics and GA4GH Phenopacket exports checked with the official HL7 validator; a "
       "seven-agent runtime with a fail-closed bioethics gate; bilingual Arabic/English citizen, counselor and evaluation "
       "apps meeting WCAG AA; and an independent red-team and evaluation harness with 1,100+ automated tests.")
assert len(cap) <= 1000, len(cap)
text(S[2], X0, Y0, W, 2.3, [(cap, 13, False, INK), (f"({len(cap)} characters)", 9, False, MUTED)])
text(S[2], X0, 4.2, W, 0.7, [("Team", 11, True, NAVY),
                                ("Utkarsh Gupta: Computer Science & Engineering graduate, IIT Dhanbad; Senior Software Engineer at Sosuv (India). Designed and led the full prototype end to end (architecture, backend, privacy layer, apps, test harness) using an AI-assisted multi-agent development workflow.", 11, False, INK)])

# ---------- 4. Architecture ----------
s = S[3]
box(s, 0.35, 1.7, 1.55, 0.62, "Partner A app\nprivate vault", fill=RGBColor(0x7A, 0x5A, 0xF8))
box(s, 0.35, 2.45, 1.55, 0.62, "Partner B app\nprivate vault", fill=RGBColor(0x7A, 0x5A, 0xF8))
arrow(s, 1.97, 2.27)
box(s, 2.32, 2.0, 1.5, 0.78, "ConsentGuardian\n+ APSI private\nset intersection")
arrow(s, 3.88, 2.27)
box(s, 4.23, 2.0, 1.5, 0.78, "Risk engine\nWright + Bayes,\nlocked numbers")
arrow(s, 5.79, 2.27)
box(s, 6.14, 2.0, 1.5, 0.78, "Closed templates\nEN / AR, numbers\nonly from locks")
arrow(s, 7.70, 2.27)
box(s, 8.05, 2.0, 1.6, 0.78, "Bioethics gate\n7 rules, fails\nclosed", fill=RGBColor(0x1F, 0x29, 0x37))
arrow(s, 8.74, 2.85, w=0.22, h=0.28, down=True)
box(s, 8.05, 3.2, 1.6, 0.6, "Message to ONE\npartner only", fill=EMERALD)
arrow(s, 4.87, 2.85, w=0.22, h=0.28, down=True)
box(s, 4.23, 3.2, 1.5, 0.6, "CounselorCopilot\ntriggers a–d")
arrow(s, 3.88, 3.39)
box(s, 2.32, 3.2, 1.5, 0.6, "Counselor\nworkbench (human)", fill=RGBColor(0x1F, 0x29, 0x37))
box(s, 6.14, 3.2, 1.5, 0.6, "Care loop\n7 states, human closure")
box(s, 0.35, 3.2, 1.55, 0.6, "FHIR R4 Genomics\n+ Phenopackets", fill=MUTED)
text(s, 0.35, 4.0, 9.3, 0.95, [
    ("Code does all math, set logic and consent checks; patients only ever receive pre-approved templates (25,508 template × result combinations verified, 0 failures). "
     "Every message passes the gate; any error holds the message. SEHA, Malaffi, Thiqa and the judicial link are SIMULATED adapters today.", 10.5, False, INK)])

# ---------- 5. Target users & outcome ----------
s = S[4]
card(s, 0.35, Y0, 2.95, 1.8, "Couples & individuals", [
    "Emirati citizens in mandatory premarital (and preconception) screening.",
    "Outcome: understand their own result privately, see only shared findings, reach counseling fast."])
card(s, 3.5, Y0, 2.95, 1.8, "Genetic counselors & physicians", [
    "~100 genomics-trained professionals across SEHA centers.",
    "Outcome: a prioritized queue, a consented-scope brief, pedigree and tasks; humans close every case."])
card(s, 6.65, Y0, 3.0, 1.8, "DoH / ADPHC", [
    "Program owners of the screening pathway.",
    "Outcome: measurable comprehension, care-loop speed and privacy, never 'marriages avoided'."])
text(s, X0, 3.6, W, 0.7, [("Non-directive by design: the marriage health certificate is issued regardless of the genetic result, and the product never advises marrying, not marrying, or ending a pregnancy.", 10.5, True, NAVY)])

# ---------- 6. Success measures ----------
table(S[5], X0, Y0, W, [
    ["Dimension", "Target", "Prototype result", "Basis"],
    ["Comprehension (teach-back)", "≥85%", "62.1% first try · 92.1% after re-explain", "SIMULATED personas"],
    ["Informed choice (SURE 4/4)", "≥90%, 0 coercion", "87.1% · 0 coercion flags", "SIMULATED personas"],
    ["Counselor booking ≤48 h", "100%", "39/39 incompatible couples", "SIMULATED clock"],
    ["Confirmatory tests completed", "≥95%", "91/92 (98.9%)", "SIMULATED clock"],
    ["Risk-math accuracy", "0 errors", "0 mismatches / 629 records", "Real (independent oracle)"],
    ["Cross-partner leaks", "0", "0 in 2,491 live API responses", "Real"],
    ["Gate on unseen attacks", "≥95% / ≤5% FP", "62.4% / 4.7% → patient text is templates-only", "Real (held-out)"],
], [2.35, 1.45, 3.45, 2.05], size=10, row_h=0.36)
text(S[5], X0, 4.65, W, 0.4, [("Never measured: cancelled marriages or any single personal decision. GCOS-24 not yet instrumented (needs licensed instrument and real users).", 9.5, False, MUTED)])

# ---------- 7. Evidence ----------
s = S[6]
card(s, 0.35, Y0, 4.55, 2.25, "From the literature (source document)", [
    "565 of 11,748 screened couples (≈4.8%) were genetically incompatible (2022–Jul 2026).",
    "52% of Emirati P/LP variants are absent from gnomAD; 30% from ClinVar (Rabea et al.).",
    "NEJM 2026 cohort: 13.1% couple-level risk in an enriched early cohort.",
    "Up to 78% carry ≥1 recessive variant, so naive sharing risks needless disclosure."], size=10)
card(s, 5.1, Y0, 4.55, 2.25, "From our testing", [
    "Risk engine reproduces the source's vignette figures exactly (1 in 426; 1 in 321 vs 1 in 3,800).",
    "25,508 template × result combinations, EN + AR: 0 failures.",
    "Red-team: 433/433 known attacks caught; 62.4% on fresh unseen attacks (reported as measured).",
    "Official HL7 validator: V2–V5 0 errors; V1 8 server timeouts.",
    "1,100+ automated tests; all three apps pass Gate 3."], size=10)

# ---------- 8. Data sources ----------
table(S[7], X0, Y0, W, [
    ["Source", "Type", "Owner / licence", "Sensitivity", "Personal data?"],
    ["Synthetic 1,000-couple cohort + 5 vignettes", "Generated genotypes & pedigrees", "Team (évolvé)", "None (synthetic)", "No"],
    ["Emirati carrier frequencies", "Published aggregate statistics", "Rabea et al.; cited in source doc", "Public, aggregate", "No"],
    ["Reference transcripts, HGNC IDs", "Public reference data", "NCBI / HGNC (open)", "Public", "No"],
    ["HPO, GENO, LOINC codes", "Ontologies / terminologies", "Open licences", "Public", "No"],
    ["HL7 FHIR Genomics IG 3.0.0, GA4GH", "Standards", "HL7 / GA4GH (open)", "Public", "No"],
], [2.6, 1.95, 1.95, 1.45, 1.35], size=9.5, row_h=0.42)
text(S[7], X0, 4.35, W, 0.6, [("No real patient or genomic data is used anywhere. Live EGP / Malaffi data would need a DoH data-sharing agreement, ethics approval and PDPL basis (pilot stage S1).", 10, False, INK),
                                ("Confirmed by the team: no real patient data was used at any stage.", 10, True, NAVY)])

# ---------- 9. Risks & safeguards ----------
s = S[8]
items = [
    ("Privacy", "Authorized PSI; dual consent; revocation purges the couple workspace; per-partner sessions; audit hash chain."),
    ("Security", "Scoped tokens ≤1 h; shift-gated counselor access; no secrets in repo; gene names never logged."),
    ("Bias & equity", "EN + AR parity; persona evaluation stratified by language, literacy, sex; Arabic native review pending."),
    ("Explainability", "Every number is a locked engine output with 'how it was counted' (formula, inputs, digest)."),
    ("Misuse / harm", "Closed templates only; gate blocks directive, donor-gamete, termination and stigmatising text."),
    ("Human oversight", "Counselor escalation on 4 triggers; only a human counselor can close a case."),
]
for i, (t, b) in enumerate(items):
    card(s, 0.35 + (i % 3) * 3.12, Y0 + (i // 3) * 1.3, 2.98, 1.18, t, [b], size=10)

# ---------- 10. Hardware ----------
card(S[9], X0, Y0, W, 0.95, "None required", [
    "Software only: three web apps (citizen, counselor, evaluation) and one backend; runs on a laptop for the demo.",
    "Pilot would run on UAE-hosted infrastructure under ADHICS; no wearables, sensors or devices."], size=11)

# ---------- 11. Access ----------
card(S[10], X0, Y0, W, 1.75, "No credentials needed: simulated sign-in", [
    "Start everything: powershell -ExecutionPolicy Bypass -File scripts\\demo\\run_local.ps1",
    "Citizen app http://localhost:3000: pick a synthetic partner (V1A … V5B); no password.",
    "Counselor workbench http://localhost:3001: synthetic counselor; switch 'On shift' to see cases.",
    "Evaluation dashboard http://localhost:3002: no sign-in.",
    "All data is synthetic; integrations are labelled SIMULATED."], size=11)
text(S[10], X0, 3.5, W, 0.4, [("TO FILL (team): public demo URL, if hosted.", 10, True, CORAL)])

# ---------- 12. Path to pilot ----------
table(S[11], X0, Y0, W, [
    ["Stage", "Scope", "Preconditions"],
    ["S0 Sandbox", "Synthetic + de-identified test data", "DoH/M42 partnership; ADHICS gap assessment"],
    ["S1 Shadow mode", "Runs beside counselors; not shown to citizens", "Ethics approval, PDPL basis, UAE hosting, safety case"],
    ["S2 Counselor-assist", "Workbench + brief live at pilot centers", "Native clinical Arabic review; live MMIC / GCOS"],
    ["S3 Citizen pilot", "APSI + citizen app at a few SEHA centers", "Malaffi integration; consent + audit to Malaffi; DPIA"],
    ["S4 Scale", "All 22 centers; ART/Thiqa navigation", "Real-world evidence; regulator sign-off"],
], [1.8, 3.4, 4.1], size=10, row_h=0.4)
text(S[11], X0, 4.45, W, 0.5, [("Kill criteria at every stage: any confirmed leak, any directive message reaching a user, or any math error halts the rollout.", 10, True, NAVY),
                                ("TO FILL (team): timeline assumptions.", 10, True, CORAL)])

# ---------- 13. IP & third-party ----------
s = S[12]
card(s, 0.35, Y0, 4.55, 2.3, "Ours", [
    "All application code, contracts, tests and docs were written for this challenge by the team.",
    "évolvé name and logo: team-owned (TO FILL: confirm).",
    "UI patterns inspired by public websites; no assets, copy or fonts copied.",
    "Developed with AI coding assistance (Anthropic Claude); all output reviewed and owned by the team."], size=10)
card(s, 5.1, Y0, 4.55, 2.3, "Third-party (open source)", [
    "Python: FastAPI, Pydantic, cryptography, fhir.resources, phenopackets, pytest, hypothesis.",
    "Web: Next.js, React, Tailwind, Radix UI, lucide, TanStack, next-intl, Playwright, axe-core.",
    "Fonts: Lexend, Instrument Sans, JetBrains Mono, IBM Plex Sans Arabic (SIL OFL).",
    "Validation tools used, not shipped: HL7 FHIR validator, phenopacket-tools.",
    "Licences to be re-confirmed from package metadata before submission."], size=10)

# ---------- 14. Conflict of interest ----------
card(S[13], X0, Y0, W, 0.95, "None", [
    "The team has no relationship with the organizers, co-creators, partners or judges of the challenge."], size=12)

# ---------- 15. Additional: product screenshots ----------
shots = [
    ("apps/citizen/screenshots/p4-clean/after/04-home-en-1280.png", "Citizen app: next step, private results"),
    ("apps/counselor/screenshots/p4-clean/after/04-case-V1-pedigree-en.png", "Counselor workbench: consented case, pedigree"),
    ("apps/eval-dashboard/screenshots/en-1280-01-top.png", "Evaluation dashboard: honest metrics"),
]
for i, (p, cap_) in enumerate(shots):
    x = 0.35 + i * 3.12
    S[14].shapes.add_picture(str(ROOT / p), Inches(x), Inches(Y0), width=Inches(2.98))
    text(S[14], x, 4.25, 2.98, 0.5, [(cap_, 10, True, NAVY)])

for sh in S[14].shapes:
    if sh.has_text_frame and "Additional Slide" in sh.text_frame.text:
        sh.top = Inches(0.94)
prs.save(str(OUT)); print("saved", OUT)
