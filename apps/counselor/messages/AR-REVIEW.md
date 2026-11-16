# Counselor workbench, Arabic UI copy: review notes
Scope: `apps/counselor/messages/ar.json`. This is counselor-facing UI text, not patient copy. Patient copy is in handoffs/AR-REVIEW-SHEET.md and follows the closed-template rules.
Status: complete first translation into professional clinical Modern Standard Arabic (2026-11-17), **TODO(native-review)**. A native clinical reviewer should check it before any real use. Synthetic demo only.
It supersedes the earlier "counselor Arabic stays English placeholders" cut-line (DECISIONS #50 item 3), at the user's request.

## Rules applied
- **Placeholders** in `{braces}` are kept exactly. The test `e2e/ar-messages.spec.ts` checks the key set, the placeholders, Arabic script in every value, and that no Arabic-Indic digits are used.
- **Digits:** Western digits (UAE usage), e.g. "48 ساعة" and "5,000 حرف". No number words.
- **Latin values allowed** (no Arabic needed): `English` (language switch), `en`, `SURE` (instrument name), `Sarvam` (provider brand). Gene symbols, HGNC IDs, case IDs, scopes and the `F` symbol stay Latin inside Arabic sentences.
- **AI draft:** the label and controls are Arabic. The **draft text stays English** because Sarvam has no Arabic (DECISIONS #62). It renders with `lang="en" dir="ltr"`.
- **Register:** formal, neutral and non-stigmatizing. Consanguinity is described neutrally ("زواج أقارب" appears only as the technical pedigree legend term for the double line).

## Terminology (aligned with handoffs/AR-REVIEW-SHEET.md)
| EN | AR | note for reviewer |
|---|---|---|
| genetic counselor | مستشار وراثي | the sheet asks whether "أخصائي إرشاد وراثي" is preferred in UAE usage; keep both files consistent |
| carrier | حامل للتغيّر الجيني | avoids "حامل" alone (also means pregnant) |
| variant | تغيّر جيني | "طفرة" is avoided |
| pedigree | شجرة العائلة | tab and graph title; "النسب الوراثي" was considered |
| consent | موافقة | "couple consent" = موافقة الزوجين |
| consented scope | نطاق الموافقة | "outside consented scope" = خارج نطاق الموافقة |
| partner A / B | الطرف (أ) / الطرف (ب) | |
| couple | الزوجان | premarital context; the patient copy uses "الخاطبين" in places |
| trigger (escalation reason) | سبب الإحالة | the letters (a)–(d) stay Latin to match the backend codes |
| residual risk | خطر متبقٍّ | |
| variant of uncertain significance | تغيّر غير محدد الدلالة | |
| run of homozygosity | امتداد من تماثل الزيجوت | please confirm the technical term |
| teach-back | إعادة الشرح | |
| human closure | الإغلاق البشري | counselor-only loop state |
| on shift / off shift | في المناوبة / خارج المناوبة | the shift state is always visible text |
| audit log | سجل التدقيق | |
| locked figure | رقم مثبّت | values from the risk engine |
| first cousins | أبناء عمومة أو خؤولة من الدرجة الأولى | covers paternal and maternal cousins |
| SIMULATED | محاكاة | |

## Items for the reviewer
1. "أساس الاطلاع" for "Viewing under" (the access-basis line). Is "الاطلاع بموجب" clearer?
2. "عمّ أو خال وابنة أخ أو أخت" for uncle–niece. Is it too long for a chip?
3. "نموذج بديل دون اتصال" for "offline stub" (AI provider). Is "نسخة تجريبية دون اتصال" preferred?
4. SLA chip "متبقٍّ {h} س {m} د" uses the abbreviations س/د for hours and minutes. Check readability.
