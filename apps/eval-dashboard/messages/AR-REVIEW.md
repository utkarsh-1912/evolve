# AR-REVIEW: eval dashboard Arabic (apps/eval-dashboard/messages/ar.json)
Status: **first draft, TODO(native-review)**. All 295 keys are in Modern Standard Arabic. Please mark changes directly in ar.json, or comment here. Synthetic demo only.
This note replaces the old `_todo` key that used to sit inside ar.json.

## Rules the translation keeps
- **Terminology** follows `handoffs/AR-REVIEW-SHEET.md`:
  - carrier = حامل للتغيّر الجيني (never bare حامل)
  - genetic counselor = مستشار وراثي
  - other partner = الطرف الآخر
  - certificate sentence uses الشهادة الصحية للزواج + بغض النظر
  - decision support = للمساعدة في اتخاذ القرار … ليست تشخيصاً ولا نصيحة طبية
  - SIMULATED = محاكاة
- **SIMULATED stays as a visible Latin token** next to محاكاة: the environment banner, the badge, the simulated-vs-real chips and the footer.
- **Honesty texts are faithful in meaning**, with no softening:
  - تحقق الهدف / لم يتحقق الهدف
  - يحقق الهدف: لا
  - غير مُقاس (GCOS not instrumented)
  - the closed-template statement
  - the "this zero is not the whole story" leakage callout
  - the calibration caption
  - "reported, not hidden"
- **Placeholders `{…}` are byte-identical** to en.json (checked by `e2e/i18n.spec.ts`). Numbers are never typed into the copy; they come from the evidence pack through the placeholders, with Western digits.
- **Kept in Latin script, by design:**
  - product, contract and test names: SURE, GCOS-24/GOS, FHIR/Phenopacket, PGT-M, LLM, G2, P0, BioethicsSupervisor, LockedNumber, junit, guardrail_check
  - file and endpoint paths
  - set names v1/v2
  - DECISIONS #n references
  - the logo (évolvé)
  - the language-switch label "English" (it must be readable to an English speaker) and its locale code `en`

## Choices a reviewer should confirm
| key | draft | question |
|---|---|---|
| gate.* "held-out" | المجموعة المحجوبة | Is "مجموعة اختبار غير مرئية" clearer to clinicians? |
| dim.privacy.title "red-team" | اختبار الاختراق | Acceptable, or prefer "اختبار الفريق الأحمر"? |
| gate.cat.donor_gametes | اقتراحات غير قانونية بشأن الأمشاج | Avoids naming donor material; confirm it reads as the UAE-law category. |
| cohort.vignette | الحالة النموذجية | For "vignette" (V1–V5). |
| probe.held | محجوزة، لم تُرسل | Must read as "held back, not delivered". |
| ui.visibility.couple | أنت والطرف الآخر | Follows the sheet (الطرف الآخر), not شريكك. |

## Process
`scripts/sync_messages.py` no longer regenerates ar.json from English. It keeps every translation, mirrors new and removed keys, and lists new keys as `TODO(ar)`. `e2e/i18n.spec.ts` fails while any value lacks Arabic script, apart from the allowlisted tokens.
