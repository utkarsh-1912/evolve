"""CulturalCommunicator templates (template-first, docs/08 #7). EN + AR.

Slot discipline (P-01/P-02): the only slots are
  {gene} / {genes}            - gene symbols the recipient may see (own record or APSI intersection)
  {offspring_risk_one_in}     - RiskOutput display string, copied verbatim
  {posterior_carrier_b_one_in}, {reference_unrelated_one_in}, {relative_to_unrelated_display}
No template contains a risk number of its own. Integers in fixed phrases ("48 hours") are allow-listed in
the gate (bioethics.FIXED_PHRASES).

Judicial sentence follows source §Tier 6 ("the health certificate is issued and transmitted to the Abu
Dhabi Judicial Department regardless of genetic test results"). Options list follows source §2.4 V1
(IVF + PGT-M under Thiqa, prenatal diagnosis, autonomous marital choice), unranked.

AR: Modern Standard Arabic copy lives in runtime/i18n_ar.py (TASK-P4-AR-ARABIC). Every AR string is marked
TODO(native-review); handoffs/AR-REVIEW-SHEET.md lists each one next to its EN source. Slots are identical to EN.
"""
from __future__ import annotations

import string

from . import i18n_ar as _ar

# DECISIONS #48 switch: Arabic slots use the locked *_ar display strings. Off until the template verifier counts
# *_ar keys as locked display strings (handoffs/REQUEST-GATE-2.md); then flip to True (one line, tests ready).
AR_LOCKED_DISPLAY = True

RECORD_SLOTS = ("offspring_risk_one_in", "posterior_carrier_b_one_in", "reference_unrelated_one_in",
                "relative_to_unrelated_display")
ALLOWED_SLOTS = {"gene", "genes", *RECORD_SLOTS}

EN = {
    "notice": "This is decision support, not a diagnosis or medical advice.",
    "header_result": "Your couple screening result.",
    "apsi_compatible": ("Couple check: no gene was found in which you both carry a change, on the screened panel "
                        "(Compatible). Screening cannot find every carrier, so this is not a guarantee."),
    "apsi_incompatible": "Couple check: you both carry a change in the same gene: {genes}.",
    "apsi_review": ("Couple check: some findings need review by a genetic counselor before a couple result can be "
                    "given, so no result is shown yet."),
    "couple_record_ok": ("For each pregnancy, the chance that a child inherits a changed copy of {gene} from both "
                         "of you is {offspring_risk_one_in}."),
    "couple_record_counselor": "A figure for {gene} is not shown here; a genetic counselor will explain it with you.",
    "options": ("Options that couples in this situation can discuss with a counselor, in no particular order: "
                "IVF with PGT-M under Thiqa (this needs the written consent of both spouses), prenatal diagnosis, "
                "and your own choices about marriage and family."),
    "carrier_not_diagnosis": "Being a carrier is not a diagnosis of disease.",
    # Uniform counselor notice (api.md v1.1.0, DECISIONS #26-28): identical for every partner of every couple.
    "counselor_notice": "A genetic counselor reviews every result and can talk it through with you.",
    "judicial": ("The marriage health certificate is issued and sent to the Abu Dhabi Judicial Department "
                 "regardless of your genetic results."),
    "close": ("There is no right or wrong choice here. Decisions about marriage and family are yours to make, "
              "and a genetic counselor can talk through your options with you."),
    "header_private": "Your own carrier results. They are private and shown only to you.",
    "own_discordant_ok": ("You carry one changed copy of {gene}. Screening cannot detect every carrier of this gene, "
                          "so a negative screen does not fully rule it out: the chance that a person with a negative "
                          "screen is still a carrier is about {posterior_carrier_b_one_in}. For your couple, the chance "
                          "that a pregnancy is affected is about {offspring_risk_one_in}."),
    "own_relative": ("That is {relative_to_unrelated_display} the figure for an unrelated couple with the same "
                     "screening results, which is {reference_unrelated_one_in}."),
    "own_confirmatory": ("Because {gene} is technically hard to test, confirmatory testing is recommended before "
                         "any reassurance."),
    "own_discordant_counselor": ("You carry one changed copy of {gene}. A figure for this gene cannot be calculated "
                                 "from the available data, so no number is shown. You can talk about it privately "
                                 "with a genetic counselor if you wish."),
    "esc_a": ("Because you both carry a change in the same gene, a genetic counselor will contact you. "
              "The aim is to book this within 48 hours."),
    "esc_b": "A genetic counselor will contact you to go through your private result with you.",
    "esc_c": "Some of your findings need a genetic counselor's review. A counselor will contact you.",
    "esc_d": "Thank you. A genetic counselor will contact you to answer your questions.",
    "esc_gate": "A genetic counselor will contact you to go through your results with you.",
    # DECISIONS #16: sent to the screen-negative partner only after the carrier's disclosure consent.
    "disclosed_gene": ("Your partner has chosen to share one result with you: a change in {gene}. Because {gene} is "
                       "technically hard to test, a confirmatory test is recommended for you before any reassurance."),
}

# Arabic copy: same keys and slots as EN. TODO(native-review), see runtime/i18n_ar.py
AR = dict(_ar.AR)

TEMPLATES = {"en": EN, "ar": AR}

# Teach-back bank (MMIC-aligned, docs/09 §4.1 item 5): carrier != diagnosis, the chance applies to each
# pregnancy, negative != zero, you decide. No numbers in the items: a "1 in 4" belongs to a locked record.
TEACHBACK = [
    {"id": "tb1", "key": "teachback.q.carrier_not_diagnosis", "en": "Being a carrier means I have the disease.", "answer": False},
    {"id": "tb2", "key": "teachback.q.each_pregnancy",
     "en": "When both partners carry a change in the same gene, the chance applies to every pregnancy separately.", "answer": True},
    {"id": "tb3", "key": "teachback.q.negative_not_zero",
     "en": "A negative screening result can still leave a small chance of being a carrier.", "answer": True},
    {"id": "tb4", "key": "teachback.q.you_decide", "en": "Decisions about marriage and family are mine to make.", "answer": True},
]
for _item in TEACHBACK:
    _item["ar"] = _ar.TEACHBACK_AR[_item["id"]]  # TODO(native-review)


def render(lang: str, key: str, *, record: dict | None = None, gene: str | None = None,
           genes: list[str] | None = None) -> str:
    """Fill a template. Number slots come only from the locked record's display strings (verbatim)."""
    tpl = TEMPLATES.get(lang, EN)[key]
    slots = {name for _, name, _, _ in string.Formatter().parse(tpl) if name}
    if slots - ALLOWED_SLOTS:
        raise ValueError("template uses a slot outside the locked-slot set")
    values: dict[str, str] = {}
    if gene is not None:
        values["gene"] = gene
    if genes is not None:
        values["genes"] = ", ".join(genes)
    for name in RECORD_SLOTS:
        if name in slots:
            rec = record or {}
            # DECISIONS #48: Arabic copy uses the locked *_ar display string produced by lock() from the same value
            # (never re-typed here). Older records without it fall back to the locked EN display string.
            v = rec.get(f"{name}_ar") if (lang == "ar" and AR_LOCKED_DISPLAY) else None
            if not isinstance(v, str) or not v:
                v = rec.get(name)
            if not isinstance(v, str) or not v:
                raise ValueError("locked display slot missing")
            values[name] = v
    return tpl.format(**values)


# i18n keys the API returns (title_key/body_key/note_key); the UI owns final wording. The EN reference text is
# gate-checked in tests so the copy behind every key is non-directive, lawful and free of numbers.
I18N_EN = {
    # CareNavigator options: unranked, equal weight; no donor option exists (Fed. Law 11/2008)
    "care.option.counseling.title": "Talk it through with a genetic counselor",
    "care.option.counseling.body": "A counselor can explain your results and answer your questions, at your pace.",
    "care.option.ivf_pgtm.title": "IVF with PGT-M",
    "care.option.ivf_pgtm.body": ("Available under Thiqa. PGT-M needs the written consent of both spouses. After PGT-M, "
                                  "confirmatory prenatal testing is still recommended."),
    "care.option.prenatal_diagnosis.title": "Prenatal diagnosis",
    "care.option.prenatal_diagnosis.body": "A specialist and a genetic counselor can explain what this involves.",
    "care.option.own_choice.title": "Your own choices about marriage and family",
    "care.option.own_choice.body": "Every option here is yours to consider or not. There is no right or wrong choice.",
    "care.option.family_screening.title": "Offer screening to relatives",
    "care.option.family_screening.body": "You can create a private family screening token that does not identify you.",
    # Eligibility notes (docs/02 §4 CareNavigator; thresholds TODO(verify) with Thiqa policy text)
    "eligibility.immediate.met": "No waiting period applies because of your screening result.",
    "eligibility.immediate.not_met": "A counselor can explain the usual waiting period.",
    "eligibility.age.met": "Your age is within the usual range.",
    "eligibility.age.needs_afc": "An ovarian reserve test is needed before this can be confirmed.",
    "eligibility.age.discouraged": "Treatment at this age is usually discouraged; a specialist can explain why.",
    "eligibility.age.under_minimum": "Treatment is available from adulthood.",
    "eligibility.age.female_partner_only": "This check applies to the female partner.",
    "eligibility.bmi.met": "Your BMI is within the usual range.",
    "eligibility.bmi.dietitian_referral": "Covered under Thiqa, together with a referral to a dietitian.",
    "eligibility.bmi.needs_review": "A specialist will review this with you.",
    "eligibility.bmi.female_partner_only": "This check applies to the female partner.",
    "eligibility.cryo.first_year": "Cryopreservation in the first year is noted for your care team.",
    "eligibility.pgtm.prenatal_confirmation": ("PGT-M needs the written consent of both spouses. After PGT-M, "
                                               "confirmatory prenatal testing is recommended."),
    # Home next steps
    "home.next.invite": "Invite your partner to a private compatibility check",
    "home.next.consent": "Your partner invited you. Review and give consent",
    "home.next.wait_partner": "Waiting for your partner's consent",
    "home.next.run_check": "Run your private compatibility check",
    "home.next.teachback": "Check your understanding",
    "home.next.counseling": "Book a conversation with a genetic counselor",
    "home.next.care_plan": "View your care plan",
    # Notifications
    "notif.result_ready": "Your result is ready",
    "notif.counselor_contact": "A genetic counselor will contact you",
    "notif.consent_received": "Your partner invited you to a compatibility check",
    "notif.consent_revoked": "A consent was withdrawn and shared results were removed",
    "notif.task_created": "A new step was added to your care plan",
    "notif.appointment": "An appointment was proposed (SIMULATED)",
    "notif.shared_gene": "Your partner shared one result with you",
    "notif.loop.ResultIssued": "Your result was issued",
    "notif.loop.PatientNotified": "You were notified of your result",
    "notif.loop.ComprehensionConfirmed": "You confirmed your understanding",
    "notif.loop.ConfirmatoryDone": "Your confirmatory testing is complete",
    "notif.loop.CounselingDone": "Your counseling session is complete",
    "notif.loop.ReproReferralDone": "Your referral is complete",
    "notif.loop.HumanClosure": "Your counselor closed this care episode",
}
for _item in TEACHBACK:
    I18N_EN[_item["key"]] = _item["en"]

# AR reference copy behind the same keys (TODO(native-review)); the UI owns final wording.
I18N_AR = dict(_ar.I18N_AR)
for _item in TEACHBACK:
    I18N_AR[_item["key"]] = _item["ar"]
I18N = {"en": I18N_EN, "ar": I18N_AR}
