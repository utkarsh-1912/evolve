"""Arabic patient copy (TASK-P4-AR-ARABIC). Modern Standard Arabic, plain (about grade 8), warm, non-directive,
non-stigmatizing. EVERY string here is a first draft: TODO(native-review) by a native clinical reviewer
(handoffs/AR-REVIEW-SHEET.md lists each one next to its English source, with terminology notes).

Rules followed (see the review sheet for the reasoning):
- Slots are identical to EN. Numbers appear ONLY through locked slots. For Arabic, templates.render fills each slot
  from the RiskOutput's *_ar display string (DECISIONS #48, e.g. "1 من كل 321", "حوالي 12 ضعفاً"), produced by
  risk_engine.lock() from the same value; no re-typing, no Arabic-Indic re-formatting, no number words.
- Carrier = "حامل للتغيّر الجيني" (never "حامل" alone, which also means pregnant), phrased generically
  ("كون الشخص حاملاً ...") to avoid gendered second-person forms.
- Consanguinity is never framed as blame or defect; "زواج الأقارب" does not appear in patient copy.
- The P-14 sentence states the certificate is issued "بغض النظر عن" the genetic results (the gate's accepted family).
- No sentence pairs a reference to the partner with a genetic-status word (P-06): the couple is addressed as
  "كلاكما" / "الخاطبين".
- Words starting with letter sequences the template verifier counts as number words (e.g. future-tense "ستـ") are
  avoided.
"""

# Communicator templates: same keys and slots as templates.EN. Every value: TODO(native-review)
AR = {
    "notice": "هذه المعلومات للمساعدة في اتخاذ القرار، وليست تشخيصاً ولا نصيحة طبية.",  # TODO(native-review)
    "header_result": "نتيجة الفحص الخاصة بكما كزوجين مقبلين على الزواج.",  # TODO(native-review)
    "apsi_compatible": ("فحص التوافق: لم يُعثر على جين يحمل فيه كلاكما تغيّراً، ضمن الجينات التي شملها الفحص "
                        "(متوافقان). الفحص لا يكشف كل الحالات، لذلك هذه النتيجة ليست ضماناً."),  # TODO(native-review)
    "apsi_incompatible": "فحص التوافق: كلاكما لديه تغيّر في الجين نفسه: {genes}.",  # TODO(native-review)
    "apsi_review": ("فحص التوافق: بعض النتائج تحتاج إلى مراجعة مستشار وراثي قبل إعطاء نتيجة للزوجين، "
                    "لذلك لا تظهر نتيجة الآن."),  # TODO(native-review)
    "couple_record_ok": ("في كل حمل، احتمال أن يرث الطفل نسخة متغيّرة من جين {gene} من كليكما هو "
                         "{offspring_risk_one_in}."),  # TODO(native-review)
    "couple_record_counselor": "لا يظهر هنا رقم خاص بجين {gene}؛ وسيشرحه لكما مستشار وراثي.",  # TODO(native-review)
    "options": ("من الخيارات التي يمكن للزوجين مناقشتها مع المستشار، دون ترتيب معيّن: أطفال الأنابيب مع الفحص "
                "الجيني للأجنة قبل الزرع (PGT-M) ضمن تغطية ثقة (ويتطلب ذلك موافقة خطية من الزوجين)، والتشخيص قبل "
                "الولادة، وخياراتكما الخاصة بشأن الزواج والأسرة."),  # TODO(native-review)
    "carrier_not_diagnosis": "كون الشخص حاملاً للتغيّر الجيني لا يعني تشخيصه بمرض.",  # TODO(native-review)
    "counselor_notice": "يراجع مستشار وراثي كل نتيجة، ويمكنه أن يناقشها معك.",  # TODO(native-review)
    "judicial": ("تُصدر الشهادة الصحية للزواج وتُرسل إلى دائرة القضاء في أبوظبي بغض النظر عن نتائج فحوصك "
                 "الجينية."),  # TODO(native-review)
    "close": ("لا يوجد خيار صحيح أو خطأ هنا. القرارات المتعلقة بالزواج والأسرة قراراتكما أنتما، ويمكن لمستشار "
              "وراثي أن يناقش معكما الخيارات المتاحة."),  # TODO(native-review)
    "header_private": "نتائجك الخاصة بالتغيّرات الجينية. هي خاصة بك ولا تظهر إلا لك.",  # TODO(native-review)
    "own_discordant_ok": ("لديك نسخة واحدة متغيّرة من جين {gene}. لا يكشف الفحص كل حاملي التغيّر في هذا الجين، "
                          "لذلك فإن النتيجة السلبية لا تنفي الاحتمال تماماً: احتمال أن يكون الشخص ذو النتيجة السلبية "
                          "حاملاً للتغيّر الجيني هو حوالي {posterior_carrier_b_one_in}. وبالنسبة لكما كزوجين، فإن "
                          "احتمال أن يتأثر الحمل هو حوالي {offspring_risk_one_in}."),  # TODO(native-review)
    "own_relative": ("ويبلغ هذا الرقم {relative_to_unrelated_display} مقارنة بالرقم لدى زوجين من غير الأقارب لديهما "
                     "نتائج الفحص نفسها، وهو {reference_unrelated_one_in}."),  # TODO(native-review)
    "own_confirmatory": ("لأن فحص جين {gene} صعب من الناحية التقنية، يُوصى بإجراء فحص تأكيدي قبل الاعتماد على أي "
                         "نتيجة."),  # TODO(native-review)
    "own_discordant_counselor": ("لديك نسخة واحدة متغيّرة من جين {gene}. لا يمكن حساب رقم لهذا الجين من البيانات "
                                 "المتوفرة، لذلك لا يظهر رقم. يمكنك التحدث عن ذلك بشكل خاص مع مستشار وراثي إن "
                                 "رغبت."),  # TODO(native-review)
    "esc_a": ("لأن لدى كليكما تغيّراً في الجين نفسه، سيتواصل معك مستشار وراثي. والهدف هو حجز موعد خلال "
              "48 ساعة."),  # TODO(native-review)
    "esc_b": "سيتواصل معك مستشار وراثي ليراجع معك نتيجتك الخاصة.",  # TODO(native-review)
    "esc_c": "بعض نتائجك تحتاج إلى مراجعة مستشار وراثي. سيتواصل معك مستشار.",  # TODO(native-review)
    "esc_d": "شكراً لك. سيتواصل معك مستشار وراثي ليجيب عن أسئلتك.",  # TODO(native-review)
    "esc_gate": "سيتواصل معك مستشار وراثي ليراجع معك نتائجك.",  # TODO(native-review)
    "disclosed_gene": ("اختار الطرف الآخر أن يشاركك نتيجة واحدة: تغيّر في جين {gene}. ولأن فحص جين {gene} صعب "
                       "من الناحية التقنية، يُوصى لك بإجراء فحص تأكيدي قبل الاعتماد على أي نتيجة."),  # TODO(native-review)
}

# Teach-back items (true/false statements), by item id. Every value: TODO(native-review)
TEACHBACK_AR = {
    "tb1": "كون الشخص حاملاً للتغيّر الجيني يعني أنه يعاني من المرض.",  # TODO(native-review) (a false statement)
    "tb2": "عندما يحمل كلٌّ من الخاطبين تغيّراً في الجين نفسه، ينطبق الاحتمال على كل حمل بشكل منفصل.",  # TODO(native-review)
    "tb3": "قد يبقى احتمال صغير أن يكون الشخص حاملاً للتغيّر الجيني حتى لو كانت نتيجة فحصه سلبية.",  # TODO(native-review)
    "tb4": "القرارات المتعلقة بالزواج والأسرة قراراتي أنا.",  # TODO(native-review)
}

# AR reference copy behind the i18n keys the API returns (same keys as templates.I18N_EN minus teach-back keys,
# which are added from TEACHBACK_AR). The UI owns final wording. Every value: TODO(native-review)
I18N_AR = {
    "care.option.counseling.title": "تحدّث مع مستشار وراثي",  # TODO(native-review)
    "care.option.counseling.body": "يمكن للمستشار أن يشرح نتائجك ويجيب عن أسئلتك، بالوتيرة التي تناسبك.",  # TODO(native-review)
    "care.option.ivf_pgtm.title": "أطفال الأنابيب مع الفحص الجيني للأجنة قبل الزرع (PGT-M)",  # TODO(native-review)
    "care.option.ivf_pgtm.body": ("متاح ضمن تغطية ثقة. يتطلب PGT-M موافقة خطية من الزوجين. وبعد PGT-M يُوصى أيضاً "
                                  "بإجراء فحص تأكيدي أثناء الحمل."),  # TODO(native-review)
    "care.option.prenatal_diagnosis.title": "التشخيص قبل الولادة",  # TODO(native-review)
    "care.option.prenatal_diagnosis.body": "يمكن لطبيب مختص ومستشار وراثي أن يشرحا ما يتضمنه ذلك.",  # TODO(native-review)
    "care.option.own_choice.title": "خياراتك الخاصة بشأن الزواج والأسرة",  # TODO(native-review)
    "care.option.own_choice.body": "كل خيار هنا لك أن تنظر فيه أو لا. لا يوجد خيار صحيح أو خطأ.",  # TODO(native-review)
    "care.option.family_screening.title": "إتاحة الفحص للأقارب",  # TODO(native-review)
    "care.option.family_screening.body": "يمكنك إنشاء رمز خاص لفحص العائلة لا يكشف هويتك.",  # TODO(native-review)
    "eligibility.immediate.met": "لا تنطبق فترة انتظار بسبب نتيجة فحصك.",  # TODO(native-review)
    "eligibility.immediate.not_met": "يمكن للمستشار أن يشرح فترة الانتظار المعتادة.",  # TODO(native-review)
    "eligibility.age.met": "عمرك ضمن النطاق المعتاد.",  # TODO(native-review)
    "eligibility.age.needs_afc": "يلزم فحص لمخزون المبيض قبل تأكيد ذلك.",  # TODO(native-review)
    "eligibility.age.discouraged": "لا يُشجَّع عادةً على العلاج في هذا العمر، ويمكن لطبيب مختص أن يشرح السبب.",  # TODO(native-review)
    "eligibility.age.under_minimum": "العلاج متاح ابتداءً من سن الرشد.",  # TODO(native-review)
    "eligibility.age.female_partner_only": "ينطبق هذا الشرط على الزوجة.",  # TODO(native-review)
    "eligibility.bmi.met": "مؤشر كتلة جسمك ضمن النطاق المعتاد.",  # TODO(native-review)
    "eligibility.bmi.dietitian_referral": "مشمول ضمن تغطية ثقة، مع إحالة إلى أخصائي تغذية.",  # TODO(native-review)
    "eligibility.bmi.needs_review": "سيراجع طبيب مختص هذا الأمر معك.",  # TODO(native-review)
    "eligibility.bmi.female_partner_only": "ينطبق هذا الشرط على الزوجة.",  # TODO(native-review)
    "eligibility.cryo.first_year": "تم تسجيل ملاحظة لفريق الرعاية بشأن حفظ الأجنة بالتجميد في السنة الأولى.",  # TODO(native-review)
    "eligibility.pgtm.prenatal_confirmation": ("يتطلب PGT-M موافقة خطية من الزوجين. وبعد PGT-M يُوصى بإجراء فحص "
                                               "تأكيدي أثناء الحمل."),  # TODO(native-review)
    "home.next.invite": "ادعُ الطرف الآخر إلى فحص توافق خاص",  # TODO(native-review)
    "home.next.consent": "وصلتك دعوة لفحص التوافق. راجعها وأعطِ موافقتك إن رغبت",  # TODO(native-review)
    "home.next.wait_partner": "بانتظار موافقة الطرف الآخر",  # TODO(native-review)
    "home.next.run_check": "ابدأ فحص التوافق الخاص بكما",  # TODO(native-review)
    "home.next.teachback": "تحقّق من فهمك للنتيجة",  # TODO(native-review)
    "home.next.counseling": "احجز جلسة مع مستشار وراثي",  # TODO(native-review)
    "home.next.care_plan": "اطّلع على خطة الرعاية الخاصة بك",  # TODO(native-review)
    "notif.result_ready": "نتيجتك جاهزة",  # TODO(native-review)
    "notif.counselor_contact": "سيتواصل معك مستشار وراثي",  # TODO(native-review)
    "notif.consent_received": "وصلتك دعوة لفحص التوافق",  # TODO(native-review)
    "notif.consent_revoked": "تم سحب موافقة، وحُذفت النتائج المشتركة",  # TODO(native-review)
    "notif.task_created": "أُضيفت خطوة جديدة إلى خطة رعايتك",  # TODO(native-review)
    "notif.appointment": "تم اقتراح موعد (محاكاة)",  # TODO(native-review)
    "notif.shared_gene": "شاركك الطرف الآخر نتيجة واحدة",  # TODO(native-review)
    "notif.loop.ResultIssued": "صدرت نتيجتك",  # TODO(native-review)
    "notif.loop.PatientNotified": "تم إبلاغك بنتيجتك",  # TODO(native-review)
    "notif.loop.ComprehensionConfirmed": "أكدت فهمك للنتيجة",  # TODO(native-review)
    "notif.loop.ConfirmatoryDone": "اكتمل الفحص التأكيدي",  # TODO(native-review)
    "notif.loop.CounselingDone": "اكتملت جلسة الاستشارة",  # TODO(native-review)
    "notif.loop.ReproReferralDone": "اكتملت الإحالة",  # TODO(native-review)
    "notif.loop.HumanClosure": "أغلق المستشار مرحلة الرعاية هذه",  # TODO(native-review)
}
