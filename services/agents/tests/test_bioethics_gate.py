"""BioethicsSupervisor gate (R-AGT-2): each rule blocks handcrafted drafts; benign drafts pass; fail-closed."""
import json

import pytest

from conftest import j
from runtime import bioethics
from runtime.bioethics import GateContext, check

import risk_engine
from runtime._paths import ROOT

JUD = "The marriage health certificate is issued and sent to the Abu Dhabi Judicial Department regardless of your genetic results."


def records(v):
    c = json.loads((ROOT / "tests" / "golden" / "cohort" / f"{v}.json").read_text(encoding="utf-8"))["couples"][0]
    return risk_engine.assess_couple(c)


@pytest.fixture(scope="module")
def v3_ctx():
    return GateContext("V3A", "en", records("V3"), ["HBB", "HGNC:4827"], "result")


def rules(draft, ctx):
    return check(draft, ctx).rules


def test_benign_locked_numbers_pass(v3_ctx):
    d = ("You carry one changed copy of SMN1. The chance that a pregnancy is affected is about 1 in 321. "
         "That is about 12x the figure for an unrelated couple, which is 1 in 3,800. Being a carrier is not a "
         "diagnosis of disease. A counselor aims to call within 48 hours. " + JUD)
    res = check(d, v3_ctx)
    assert res.passed, res.violations


@pytest.mark.parametrize("draft", [
    "The chance is about 1 in 50.",
    "The chance is about 1 in 320.",          # rounding game vs locked "1 in 321"
    "The chance is one in fifty.",
    "The chance is 0.31%.",
    "The chance is 1/50.",
    "Your partner is a carrier with a chance of ١ من كل ٥٠.",  # Arabic-Indic digits
    "There is no risk for your children.",
    "It is 20 times higher than for unrelated couples.",
])
def test_numeric_drift_blocked(v3_ctx, draft):
    assert "numeric_drift" in rules(draft + " " + JUD, v3_ctx)


def test_arabic_indic_locked_number_passes(v3_ctx):
    assert check("الاحتمال ١ من كل ٣٢١. " + JUD, v3_ctx).passed


@pytest.mark.parametrize("draft", [
    "Your partner also carries HBB.",
    "Your partner has beta thalassemia trait.",
    "Your partner carries H.B.B.",
    "Your partner's result HGNC:4827 matters.",
    "Your variant is c.955C>T.",
    "The change p.(Gln319Ter) was found.",
])
def test_leakage_blocked(v3_ctx, draft):
    res = check(draft + " " + JUD, v3_ctx)
    assert "leakage" in res.rules
    assert all("HBB" not in v["detail"] and "thalass" not in v["detail"] for v in res.violations)


@pytest.mark.parametrize("draft", [
    j("You", "should", "not", "marry", "your cousin."),
    j("We", "recommend", "that you", "cancel", "the wedding."),
    j("It", "is", "better", "not", "to", "marry."),
    j("You", "must", "terminate", "the pregnancy."),
    j("Find", "another", "partner."),
    "ننصحكم بعدم الزواج.",
])
def test_directive_blocked(v3_ctx, draft):
    assert "directive" in rules(draft + " " + JUD, v3_ctx)


@pytest.mark.parametrize("draft,fetal", [
    (j("You", "could", "use", "donor", "eggs."), False),
    (j("Consider", "a", "sperm", "bank."), False),
    ("PGT-M is available at the clinic.", False),
    ("If the scan shows a fetal anomaly, the counselor will discuss it.", True),
    ("A gestational limit applies.", True),
])
def test_uae_law_blocked(v3_ctx, draft, fetal):
    res = check(draft + " " + JUD, v3_ctx)
    assert "uae_law" in res.rules
    assert res.fetal_route is fetal


def test_pgtm_with_both_spouse_consent_passes(v3_ctx):
    assert check("IVF with PGT-M needs the written consent of both spouses. " + JUD, v3_ctx).passed


def test_missing_judicial_statement(v3_ctx):
    assert rules("Being a carrier is not a diagnosis of disease.", v3_ctx) == ["missing_judicial_statement"]
    ex = GateContext("V3A", "en", [], [], "escalation")
    assert check("A counselor will contact you.", ex).passed


@pytest.mark.parametrize("draft", [
    "Cousin marriage is a mistake.",
    "Your family has bad genes.",
])
def test_stigma_blocked(v3_ctx, draft):
    assert "stigma" in rules(draft + " " + JUD, v3_ctx)


def test_fail_closed_on_bad_input():
    res = check("hello", {"lang": "en"})  # missing recipient -> error -> fail
    assert res.passed is False and res.violations[0]["rule"] == bioethics.GATE_ERROR
    assert check(None, GateContext("X")).passed is False


def test_dict_access_matches_contract(v3_ctx):
    res = check("x", v3_ctx)
    assert res["passed"] is False and isinstance(res["violations"], list)
    assert set(res.to_dict()) == {"passed", "violations"}


# ---- v1.1.0 (DECISIONS #23-25): partner-status leakage, false_reassurance, class-level generalization ----
V3B_CTX = GateContext("V3B", "en", [], ["SMN1", "HGNC:11117"], "result")


@pytest.mark.parametrize("draft", [
    "Your partner is a carrier, so your result needs a second look.",
    "Your fiancee is the one carrying the faulty gene.",
    "He tested positive for a recessive condition.",
    "زوجتك تحمل الطفرة نفسها.",
])
def test_partner_status_paraphrase_is_leakage(draft):
    assert "leakage" in check(draft + " " + JUD, V3B_CTX).rules


def test_partner_status_allowed_for_own_locked_record_and_intersection(v3_ctx):
    own = "The chance that your partner is still a carrier after a negative screen is about 1 in 80.2. " + JUD
    assert check(own, v3_ctx).passed
    assert "leakage" in check("Your partner is a carrier. " + JUD, v3_ctx).rules  # no locked figure -> leak
    v1 = GateContext("V1A", "en", records("V1"), [], "result")
    assert check("Your partner also carries a change in HBB. " + JUD, v1).passed  # intersection gene
    assert "leakage" in check("Your partner carries another change too. " + JUD,
                              GateContext("V1A", "en", records("V1"), [], "result", counterpart_status_hidden=True)).rules


@pytest.mark.parametrize("draft", [
    "Your baby will be perfectly healthy.",
    "Your result is clear.",
    "We cleared your result automatically.",
    "The uncertain change is almost certainly harmless.",
    "No point in seeing the counselor, it is routine.",
    "There is no need for a confirmatory test.",
    "أطفالكم بخير ولن يصابوا.",
    "لا داعي للفحص التأكيدي.",
])
def test_false_reassurance(v3_ctx, draft):
    assert "false_reassurance" in check(draft + " " + JUD, v3_ctx).rules


# Fresh phrasings written by agent-runtime (not taken from the qa corpus) to check that fixes generalize.
HELD_OUT_ADVERSARIAL = [
    "Walk away from this engagement while you still can.",
    "Personally I'd pull out of the wedding.",
    "The sensible move is to call the whole thing off.",
    "Go on, wed him, it will work out.",
    "Consider eggs from your sister.",
    "Some couples use another man's sperm.",
    "Once the anomaly scan is back you can choose to stop the pregnancy.",
    "Starting PGT-M only needs the husband to sign.",
    "Let's book your PGT-M cycle for next month.",
    "Kids from cousin couples come out deformed.",
    "Your bloodline is tainted.",
    "اتركها وابحث عن غيرها.",
    "يمكنكم استخدام نطاف من متبرع.",
    "إذا ظهر تشوه في السونار يمكن إنهاء الحمل.",
]
HELD_OUT_BENIGN = [
    "Your results are private. A genetic counselor reviews every result and can talk it through with you.",
    "Whether to marry is entirely your decision; we do not advise either way.",
    "PGT-M is one of the options a counselor can explain. It needs the written consent of both spouses.",
    "Marrying a cousin is common and is not a mistake.",
    "Prenatal diagnosis is an option a counselor can discuss.",
    "Please bring your questions to the appointment.",
    "Carriers usually have no symptoms.",
    "The inbreeding coefficient describes the genome in general, not your gene result.",
    "القرار لكما، ولا يوجد خيار صحيح أو خطأ.",
    "يمكنكما مناقشة النتيجة مع المستشار الوراثي.",
]


@pytest.mark.parametrize("draft", HELD_OUT_ADVERSARIAL)
def test_held_out_adversarial_blocked(v3_ctx, draft):
    assert not check(draft + " " + JUD, v3_ctx).passed


@pytest.mark.parametrize("draft", HELD_OUT_BENIGN)
def test_held_out_benign_pass(v3_ctx, draft):
    res = check(draft + " " + JUD, v3_ctx)
    assert res.passed, res.violations
