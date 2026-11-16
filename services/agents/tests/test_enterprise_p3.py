"""P3 backend (TASK-P3-AR): CareNavigator rules, teach-back bank, notifications, care plan, disclosure consent
(DECISIONS #16), counselor workbench, family tokens. Real risk_engine, privacy and gate; no mocks."""
import json
from datetime import timedelta

import pytest

from conftest import consent_both
from loopbus import SimulatedClock
from runtime import templates
from runtime.agents import CareNavigator
from runtime.bioethics import GateContext, check
from runtime.enterprise import InvalidRequest
from runtime.orchestrator import Runtime

GENES = ["CYP21A2", "HBB", "MEFV", "ABCA4", "HBA2", "SMN1", "DONSON", "ALDH3A2", "TPO", "CYP1B1", "GJB2"]


def run(rt, cid):
    consent_both(rt, cid)
    return rt.run_compatibility(cid)


def partner(sex="female", age=30, bmi=24.0):
    return {"partner_id": "X", "sex": sex, "age": age, "bmi": bmi}


def check_of(elig, key):
    return next(c for c in elig["checks"] if c["key"] == key)


# --------------------------------------------------------------------- CareNavigator rules (R-AGT-4)
@pytest.mark.parametrize("age,status,note", [
    (17, "not_met", "eligibility.age.under_minimum"),
    (18, "met", "eligibility.age.met"), (45, "met", "eligibility.age.met"),
    (46, "needs_review", "eligibility.age.needs_afc"), (47, "needs_review", "eligibility.age.needs_afc"),
    (48, "not_met", "eligibility.age.discouraged"),
])
def test_age_rule(age, status, note):
    c = check_of(CareNavigator.eligibility(partner(age=age), own_plp=True, family_history=False, pgtm_option=False), "age")
    assert (c["status"], c["note_key"]) == (status, note)


@pytest.mark.parametrize("bmi,status,note", [
    (18.5, "needs_review", "eligibility.bmi.needs_review"), (19, "met", "eligibility.bmi.met"),
    (35, "met", "eligibility.bmi.met"), (36, "met", "eligibility.bmi.dietitian_referral"),
    (40, "met", "eligibility.bmi.dietitian_referral"), (41, "needs_review", "eligibility.bmi.needs_review"),
])
def test_bmi_rule(bmi, status, note):
    c = check_of(CareNavigator.eligibility(partner(bmi=bmi), own_plp=True, family_history=False, pgtm_option=False), "bmi")
    assert (c["status"], c["note_key"]) == (status, note)


def test_immediate_eligibility_cryo_and_pgtm_reminder():
    e = CareNavigator.eligibility(partner(), own_plp=False, family_history=True, pgtm_option=True)
    assert e["immediate"] is True
    assert check_of(e, "cryopreservation")["note_key"] == "eligibility.cryo.first_year"
    assert check_of(e, "post_pgtm_prenatal_confirmation")["note_key"] == "eligibility.pgtm.prenatal_confirmation"
    e2 = CareNavigator.eligibility(partner(sex="male", age=60), own_plp=False, family_history=False, pgtm_option=False)
    assert e2["immediate"] is False and check_of(e2, "age")["note_key"] == "eligibility.age.female_partner_only"


def test_options_unranked_no_donor_and_copy_passes_gate():
    opts = CareNavigator.options(incompatible=True, own_plp=True)
    ids = [o["id"] for o in opts]
    assert ids == sorted(ids) and all(o["rank"] is None for o in opts)
    assert not any("donor" in i for i in ids)
    ctx = GateContext("V1A", "en", [], [], "care")
    # an option's title and body are always shown (and gated) together; every other key stands alone
    units = [(f"care.option.{o}", [f"care.option.{o}.title", f"care.option.{o}.body"])
             for o in {k.split(".")[2] for k in templates.I18N_EN if k.startswith("care.option.")}]
    units += [(k, [k]) for k in templates.I18N_EN if not k.startswith("care.option.")]
    for name, keys in units:
        res = check(" ".join(templates.I18N_EN[k] for k in keys), ctx)
        assert res.passed, (name, res.violations)


# --------------------------------------------------------------------- teach-back + SURE
def test_teachback_bank_and_scoring(rt):
    items = rt.communicator.teachback_items("en")
    assert [i["key"] for i in items] == ["teachback.q.carrier_not_diagnosis", "teachback.q.each_pregnancy",
                                         "teachback.q.negative_not_zero", "teachback.q.you_decide"]
    run(rt, "V4")
    assert rt.teachback("V4A", {"tb1": False, "tb2": True, "tb3": True, "tb4": True})["passed"] is True
    assert rt.teachback("V4B", ["not", "booleans"]) == {"passed": False, "score": 0, "escalated": True}
    assert [c["trigger"] for c in rt.queue()] == ["d"]
    assert rt.cases[rt.queue()[0]["case_id"]]["subjects"] == ["V4B"]


# --------------------------------------------------------------------- home, notifications, loop visibility
def test_home_next_step_progression(rt):
    assert rt.portal.home("V1A")["couple_status"] == "not_linked"
    rt.request_consent("V1A", "V1B")
    assert rt.portal.home("V1A")["next_step"]["kind"] == "wait"
    assert rt.portal.home("V1B")["next_step"]["kind"] == "consent"
    rt.request_consent("V1B", "V1A")
    assert rt.portal.home("V1B")["next_step"]["kind"] == "run_check"
    rt.run_compatibility("V1")
    h = rt.portal.home("V1A")
    assert h["couple_status"] == "result_ready" and h["next_step"]["kind"] == "teachback"
    assert h["counts"]["notifications_unread"] > 0 and h["consent"]["status"] == "active"
    rt.teachback("V1A", [False, True, True, True])
    assert rt.portal.home("V1A")["next_step"]["kind"] == "counseling"


def test_screen_negative_partner_view_is_not_differential(rt):
    run(rt, "V3")
    run(rt, "V4")  # V4B: compatible couple, nothing escalated for B
    b3, b4 = rt.portal.care_plan("V3B"), rt.portal.care_plan("V4B")
    assert b3["loop"]["state"] == "PatientNotified" and b3["tasks"] == [] and b3["appointments"] == []
    # same notification kinds as a partner of a compatible couple with nothing escalated
    assert sorted(n["title_key"] for n in rt.portal.notifications("V3B")) == \
        sorted(n["title_key"] for n in rt.portal.notifications("V4B"))
    kinds_b3 = sorted(n["title_key"] for n in rt.portal.notifications("V3B"))
    assert "notif.counselor_contact" not in kinds_b3 and "notif.task_created" not in kinds_b3
    assert {o["id"] for o in b3["options"]} == {"counseling"}
    dump = json.dumps([b3, rt.portal.home("V3B"), rt.portal.notifications("V3B")])
    assert not any(g in dump for g in GENES)
    # the carrier sees her own task and the escalation
    a3 = rt.portal.care_plan("V3A")
    assert [t["kind"] for t in a3["tasks"]] == ["confirmatory_test"] and "SMN1" not in json.dumps(a3)


def test_loop_notifications_and_history_shape(authority):
    clock = SimulatedClock()
    rt = Runtime(clock=clock)  # own Authority on the simulated clock (signed sets carry issued_at)
    run(rt, "V1")
    keys = [n["title_key"] for n in rt.portal.notifications("V1A")]
    assert "notif.loop.ResultIssued" in keys and "notif.loop.PatientNotified" in keys
    lp = rt.portal.visible_loop("V1A")
    assert all(set(h) == {"state", "ts", "actor_role"} for h in lp["history"])
    clock.advance(timedelta(hours=49))
    assert rt.loop.timer("V1")["overdue"] is True


# --------------------------------------------------------------------- disclosure consent (DECISIONS #16)
def test_disclosure_consent_unlocks_negative_partner_task(rt):
    run(rt, "V3")
    case = next(c for c in rt.cases.values() if c["couple_id"] == "V3")
    with pytest.raises(PermissionError):  # no Task for the screen-negative partner without the carrier's consent
        rt.workbench.create_task(case["case_id"], kind="confirmatory_test", partner_id="V3B")
    with pytest.raises(InvalidRequest):
        rt.disclose_gene("V3B", 11117)  # not the carrier
    c = rt.disclose_gene("V3A", 11117)
    assert c["purpose"] == "disclose-gene-to-partner" and c["scope"] == {"hgnc_id": 11117}
    b = rt.portal.care_plan("V3B")
    assert [t["kind"] for t in b["tasks"]] == ["confirmatory_test"]
    shared = [m for m in rt.messages("V3B") if m["kind"] == "care"]
    assert len(shared) == 1 and "SMN1" in shared[0]["text"]
    assert rt.workbench.create_task(case["case_id"], kind="appointment", partner_id="V3B")["status"] == "requested"
    assert any(x["purpose"] == "disclose-gene-to-partner" for x in rt.list_consents("V3B"))
    rt.revoke_consent("V3A", c["id"])
    assert all(t["status"] == "cancelled" for t in rt.portal.care_plan("V3B")["tasks"] if t["kind"] == "confirmatory_test")
    with pytest.raises(PermissionError):
        rt.workbench.create_task(case["case_id"], kind="follow_up", partner_id="V3B")


def test_disclosure_requires_complex_locus(rt):
    run(rt, "V4")
    with pytest.raises(InvalidRequest):
        rt.disclose_gene("V4A", 6998)  # MEFV: not a complex locus


# --------------------------------------------------------------------- workbench
def test_case_view_scope_tasks_notes_closure(rt):
    run(rt, "V3")
    case = next(c for c in rt.cases.values() if c["couple_id"] == "V3")
    row = rt.workbench.cases(status="open", trigger="b")[0]
    assert row["priority"] == "high" and row["sla_due_at"] > row["opened_at"]
    v = rt.workbench.case_view(case["case_id"], "counselor-7", True)
    assert v["access_basis"] == {"couple_consent": True, "on_shift": True}
    assert v["case"]["assigned_to"] == "counselor-7"
    assert any(n["role"] == "partner_A" for n in v["pedigree"]["nodes"]) and v["pedigree"]["F"] == 0.0625
    assert any(e["kind"] == "couple" and e["consanguineous"] for e in v["pedigree"]["edges"])
    assert [r.get("gene") for r in v["variants"]] == ["SMN1"]
    t = next(t for t in v["tasks"] if t["code"]["text"] == "confirmatory_test")
    assert t["resourceType"] == "Task" and t["for"]["reference"] == "Patient/V3A"
    rt.workbench.update_task(case["case_id"], t["id"], "completed")
    assert rt.loop.get("V3")["state"] == "ConfirmatoryDone"
    n = rt.workbench.add_note(case["case_id"], "counselor-7", "Discussed residual risk.")
    assert n["visible_to_patient"] is False
    assert not any("residual" in json.dumps(e) for e in rt.audit.events())  # note text never audited
    out = rt.workbench.closure(case["case_id"], "counselor-7", "Closed after counseling.")
    assert out["loop"]["state"] == "HumanClosure" and out["case"]["status"] == "closed"


def test_variants_outside_consent_are_placeholders(rt):
    run(rt, "V4")
    rt.teachback("V4A", [True, True, True, True])  # (d) for V4A only
    case = next(c for c in rt.cases.values() if c["couple_id"] == "V4")
    v = rt.workbench.case_view(case["case_id"], "c1", True)
    genes = [r.get("gene") for r in v["variants"]]
    assert sorted(g for g in genes if g) == ["GJB2", "MEFV"]
    assert {"outside_consent": True} in v["variants"] and "ABCA4" not in json.dumps(v["variants"])


def test_family_token_own_call_only(rt):
    tok = rt.portal.family_token("V3A", 11117)
    assert set(tok["token"]) == {"hgnc_id", "variant_digest", "issued_at", "expiry", "signature"}
    assert tok["qr_payload"].startswith("IDR-CST1.") and "V3A" not in json.dumps(tok)
    with pytest.raises(InvalidRequest):
        rt.portal.family_token("V3B", 11117)


def test_disclosure_consent_matches_shared_schema(rt):
    import jsonschema
    from runtime.enterprise import CONSENT_SCHEMA
    run(rt, "V2")
    c = rt.disclose_gene("V2A", 2600)
    jsonschema.validate(c, CONSENT_SCHEMA)
    assert c["purpose"] == "disclose-gene-to-partner" and c["scope"] == {"hgnc_id": 2600}
    jsonschema.validate(rt.revoke_consent("V2A", c["id"]), CONSENT_SCHEMA)
    for apsi in (x for x in rt.list_consents("V2A") if x["purpose"] == "apsi-couple-compatibility"):
        jsonschema.validate(apsi, CONSENT_SCHEMA)


def test_disclosure_consent_signed_and_checked_by_privacy(rt):
    from privacy.consent import DISCLOSE_PURPOSE
    run(rt, "V3")
    with pytest.raises(InvalidRequest):
        rt.disclose_gene("V3B", 11117)  # runtime check: the grantor must carry the gene (privacy checks panel only)
    c = rt.disclose_gene("V3A", 11117)
    assert rt.consent_service.check(c, purpose=DISCLOSE_PURPOSE) is None          # privacy signature
    assert rt.consent_service.check({**c, "scope": {"hgnc_id": 2600}}) == "bad_signature"
    assert rt.guardian.verify(c) == "wrong_purpose"                                # never usable for APSI
    assert not hasattr(rt.disclosures, "_key") and not hasattr(rt.disclosures, "_sign")
    rt.revoke_consent("V3A", c["id"])
    assert rt.consent_service.check(c, purpose=DISCLOSE_PURPOSE) == "revoked"
    assert rt.disclosed_recipients("V3") == set()
