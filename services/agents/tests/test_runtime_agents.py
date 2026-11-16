"""Runtime orchestration (R-AGT-1/3, P-06/P-07/P-08/P-18). Real risk_engine, privacy and gate; no mocks."""
import json
import re
import subprocess
import sys

import pytest

from conftest import consent_both, j
from privacy.authority import Authority  # noqa: F401
from runtime import bioethics, policy, templates
from runtime._paths import ROOT
from runtime.agents import ConsentRequired
from runtime.llm import ScriptedLLM
from runtime.orchestrator import Runtime

GENES = ["CYP21A2", "HBB", "MEFV", "ABCA4", "HBA2", "SMN1", "DONSON", "ALDH3A2", "TPO", "CYP1B1", "GJB2"]
HGVS = re.compile(r"(?<![A-Za-z0-9])(?:[cp]\.\(?[A-Z0-9]|HGNC:)")


def texts(msgs):
    return " ".join(m["text"] for m in msgs)


def run(rt, cid):
    consent_both(rt, cid)
    return rt.run_compatibility(cid)


NOTICE = "A genetic counselor reviews every result and can talk it through with you."


def required_phrases(text):
    assert "not a diagnosis" in text
    assert "regardless" in text and "certificate" in text
    assert "no right or wrong choice" in text


def test_seven_agents_with_tool_bindings(rt):
    roster = json.loads((ROOT / "contracts" / "agents.json").read_text())["runtime_agents"]
    agents = [rt.guardian, rt.interpreter, rt.pedigree, rt.communicator, rt.navigator, rt.supervisor, rt.copilot]
    assert [a.name for a in agents] == roster
    assert all(a.TOOLS for a in agents)


def test_v4_compatible_couple_sees_no_gene_each_sees_own(rt):
    res = run(rt, "V4")
    assert res["apsi"]["compatible"] is True and res["apsi"]["shared_hgnc_ids"] == []
    assert res["records"] == []
    for pid in ("V4A", "V4B"):
        result = [m for m in res["messages"][pid] if m["kind"] == "result"]
        assert len(result) == 1 and "Compatible" in result[0]["text"]
        assert not any(g in result[0]["text"] for g in GENES)
        required_phrases(result[0]["text"])
    a_all, b_all = texts(rt.messages("V4A")), texts(rt.messages("V4B"))
    assert "MEFV" in a_all and "GJB2" in a_all and "ABCA4" not in a_all
    assert "ABCA4" in b_all and "MEFV" not in b_all and "GJB2" not in b_all
    assert {r["gene"] for r in rt.vault("V4A")["records"]} == {"MEFV", "GJB2"}
    assert {r["gene"] for r in rt.vault("V4B")["records"]} == {"ABCA4"}
    assert {c["gene"] for c in rt.vault("V4B")["calls"]} == {"ABCA4"}
    assert not HGVS.search(a_all + b_all)
    assert rt.queue() == []  # DECISIONS #11: V4 is compatible + optional private counseling


def test_v1_shared_hbb_one_in_four_escalation_a(rt):
    res = run(rt, "V1")
    assert res["apsi"]["compatible"] is False and res["apsi"]["shared_hgnc_ids"] == [4827]
    assert [r["gene"] for r in res["records"]] == ["HBB"]
    for pid in ("V1A", "V1B"):
        t = texts(res["messages"][pid])
        assert "HBB" in t and "1 in 4" in t
        required_phrases(t)
        assert any(m["kind"] == "escalation" for m in res["messages"][pid])
        result = next(m for m in res["messages"][pid] if m["kind"] == "result")
        assert result["locked_digests"] == [res["records"][0]["digest"]]
    q = rt.queue()
    assert [(c["couple_id"], c["trigger"]) for c in q] == [("V1", "a")]
    brief = rt.brief(q[0]["case_id"])
    assert brief["pedigree"]["relationship"] == "first_cousins"
    assert rt.loop.get("V1")["timer"]["required"] is True


def test_v3_carrier_sees_residual_partner_sees_no_gene(rt):
    res = run(rt, "V3")
    a, b = texts(rt.messages("V3A")), texts(rt.messages("V3B"))
    assert "1 in 321" in a and "1 in 3,800" in a and "about 12x" in a and "SMN1" in a
    assert not any(g in b for g in GENES) and not re.search(r"\d", b.replace("48", ""))
    assert [(c["couple_id"], c["trigger"]) for c in rt.queue()] == [("V3", "b")]
    assert not any(m["kind"] == "escalation" for m in rt.messages("V3B"))  # B is not told about A's result
    assert res["review_required"] == {"V3A": False, "V3B": False}


def test_v5_escalation_c_and_no_clearance(rt):
    res = run(rt, "V5")
    assert [(c["couple_id"], c["trigger"]) for c in rt.queue()] == [("V5", "c")]
    for pid in ("V5A", "V5B"):
        t = texts(res["messages"][pid])
        assert "Compatible" not in t and "DONSON" not in t  # P-05 clearance suppressed; VUS not disclosed
    assert res["records"] == []


def test_compatibility_requires_both_consents(rt):
    rt.request_consent("V1A", "V1B")
    with pytest.raises(ConsentRequired):
        rt.run_compatibility("V1")


def test_revocation_purges_and_next_call_refused(rt):
    ca, _ = consent_both(rt, "V1")
    rt.run_compatibility("V1")
    token = rt.workspaces["V1"].token
    rt.revoke_consent("V1A", ca["id"])
    assert "V1" not in rt.workspaces and rt.vault("V1A")["records"] == []
    assert rt.messages("V1A") == [] and rt.messages("V1B") == []
    from privacy.consent import WorkspaceError
    with pytest.raises(WorkspaceError):
        rt.guardian.read_workspace(token)
    with pytest.raises(ConsentRequired):
        rt.run_compatibility("V1")


def _canary_couple():
    def call(hid, gene):
        return {"hgnc_id": hid, "gene": gene, "hgvs_c": None, "hgvs_p": None, "refseq": None, "zygosity": "het",
                "classification": "P", "variant_type": "snv", "absent_gnomad": True, "absent_clinvar": True,
                "in_roh_gt_10mb": False}
    return {"couple_id": "VC", "relationship": {"type": "unrelated", "paths": []}, "partners": [
        {"partner_id": "VCA", "role": "A", "sex": "female", "age": 25, "bmi": 22.0,
         "calls": [call(990009, "ZZZ9"), call(6998, "MEFV")], "assays": {}},
        {"partner_id": "VCB", "role": "B", "sex": "male", "age": 27, "bmi": 24.0,
         "calls": [call(990008, "ZZZ8"), call(34, "ABCA4")], "assays": {}}]}


def test_canary_isolation_interleaved(authority, monkeypatch):
    # defense-in-depth: simulate an AUTHORIZED LLM build (DECISIONS #37) to prove per-user context isolation
    monkeypatch.setattr(policy, "llm_paraphrase_allowed", lambda: True)
    llm = ScriptedLLM([])
    rt = Runtime(authority=authority, llm=llm)
    rt.add_couple(_canary_couple())
    outputs = {"VCA": [], "VCB": []}
    rt.request_consent("VCA", "VCB")
    outputs["VCB"].append(json.dumps(rt.vault("VCB")))
    rt.request_consent("VCB", "VCA")
    outputs["VCA"].append(json.dumps(rt.vault("VCA")))
    res = rt.run_compatibility("VC")
    for pid in ("VCB", "VCA", "VCB", "VCA"):
        outputs[pid].append(json.dumps(res["messages"][pid]))
        outputs[pid].append(json.dumps(rt.vault(pid)))
        outputs[pid].append(json.dumps(rt.messages(pid)))
        outputs[pid].append(json.dumps(rt.teachback(pid, [False, True, True, True])))
    a, b = " ".join(outputs["VCA"]), " ".join(outputs["VCB"])
    assert "ZZZ9" in a and "ZZZ9" not in b and "MEFV" not in b
    assert "ZZZ8" in b and "ZZZ8" not in a and "ABCA4" not in a
    # per-user LLM context (P-08): each history only ever saw its own partner's text
    ha, hb = rt.contexts["VCA"].llm_history, rt.contexts["VCB"].llm_history
    assert ha is not hb
    assert all("ZZZ8" not in h["text"] for h in ha) and all("ZZZ9" not in h["text"] for h in hb)


def test_gate_bypass_impossible(rt, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("gate down")
    monkeypatch.setattr(bioethics, "check", boom)
    res = run(rt, "V1")
    assert res["messages"] == {"V1A": [], "V1B": []}
    assert rt.messages("V1A") == [] and rt.messages("V1B") == []
    assert any(c["trigger"] == "gate" for c in rt.queue())
    assert any(e["outcome"] == "escalated" for e in rt.guardrail_events)


def test_bad_llm_draft_regenerated_from_template(authority, monkeypatch):
    monkeypatch.setattr(policy, "llm_paraphrase_allowed", lambda: True)  # simulated authorized build
    bad = j("You", "should", "not", "marry.") + " The chance is 1 in 50."
    rt = Runtime(authority=authority, llm=ScriptedLLM([bad, bad, bad, bad]))
    res = run(rt, "V1")
    t = texts(res["messages"]["V1A"])
    assert "1 in 50" not in t and "1 in 4" in t
    outcomes = {e["outcome"] for e in rt.guardrail_events}
    assert {"blocked", "rewritten"} <= outcomes
    assert all(set(e) == {"ts", "rule", "outcome", "message_id"} for e in rt.guardrail_events)


def test_unfixable_draft_escalates_and_fetal_routes(rt):
    from runtime.agents import Draft, Section
    from runtime.bioethics import GateContext
    d = Draft("result", "en", [Section("If the scan shows a fetal anomaly, options exist.")])
    rv = rt.supervisor.review(d.text, d, GateContext("V1A", "en", [], [], "result"))
    assert rv.text is None and rv.outcome == "escalated" and rv.route_fetal
    assert len(rv.attempts) == 1  # no rewrite of fetal-anomaly content


def test_arabic_templates_render_and_pass(rt):
    rt.set_lang("V3A", "ar")
    res = run(rt, "V3")
    ar = [m for m in res["messages"]["V3A"] if m["lang"] == "ar"]
    # DECISIONS #48/#53: Arabic messages carry the locked Arabic figure, not the English one
    assert ar and "1 من كل 321" in texts(ar) and "1 in 321" not in texts(ar)
    assert set(templates.AR) == set(templates.EN)


def test_teachback_and_sure_escalate_d(rt):
    run(rt, "V4")
    assert rt.teachback("V4A", [True, True, True, True]) == {"passed": False, "score": 3, "escalated": True}
    assert rt.sure("V4B", [True, True, True, False])["escalated"] is True
    assert rt.sure("V4A", [True] * 4) == {"score": 4, "escalated": False}
    assert [c["trigger"] for c in rt.queue()] == ["d"]


def test_guardrail_check_clean():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "guardrail_check.py")], capture_output=True, text=True)
    mine = [ln for ln in out.stdout.splitlines()
            if any(p in ln.replace("\\", "/") for p in ("services/agents", "services/api", "services/loop"))]
    assert mine == [], mine


def test_uniform_counselor_notice_and_no_differential_notice(rt):
    for cid in ("V1", "V2", "V3", "V4", "V5"):
        run(rt, cid)
        for pid in (cid + "A", cid + "B"):
            result = [m for m in rt.messages(pid) if m["kind"] == "result"]
            assert len(result) == 1 and NOTICE in result[0]["text"]
    # screen-negative partners of discordant couples get no escalation/review message (P-06)
    for pid in ("V2B", "V3B"):
        assert [m["kind"] for m in rt.messages(pid)] == ["result"]
    assert texts(rt.messages("V3B")) == texts(rt.messages("V2B"))


def test_consents_listing_and_simulated_partner_consent(rt):
    made = rt.simulate_partner_consent("V2")
    assert len(made) == 2 and rt.simulate_partner_consent("V2") == []
    assert len(rt.list_consents("V2A")) == 2 and rt.list_consents("V1A") == []
    assert rt.run_compatibility("V2")["apsi"]["status"] == "ok"


def test_vault_call_shape(rt):
    calls = rt.vault("V3A")["calls"]
    assert {"gene", "hgnc_id", "classification", "zygosity", "plain_en", "plain_ar", "confirmatory_recommended"} <= set(calls[0])
    assert calls[0]["confirmatory_recommended"] is True
    assert rt.vault("V3B")["calls"] == []


def test_llm_paraphrase_hard_off(authority, monkeypatch, tmp_path):
    from runtime.llm import StubLLM
    monkeypatch.delenv(policy.ENV_FLAG, raising=False)
    with pytest.raises(policy.LLMPolicyError):
        Runtime(authority=authority, llm=StubLLM())
    monkeypatch.setenv(policy.ENV_FLAG, "1")  # env alone is not enough
    monkeypatch.setattr(policy, "HOLDOUT_PASS_FILE", tmp_path / "holdout_pass.json")
    with pytest.raises(policy.LLMPolicyError):
        Runtime(authority=authority, use_llm=True)
    (tmp_path / "holdout_pass.json").write_text(json.dumps({"sets": [{"name": "h1", "catch": 0.97, "fp": 0.03}]}))
    with pytest.raises(policy.LLMPolicyError):  # one passing set is not enough
        Runtime(authority=authority, use_llm=True)
    (tmp_path / "holdout_pass.json").write_text(json.dumps(
        {"sets": [{"name": "h1", "catch": 0.97, "fp": 0.03}, {"name": "h2", "catch": 0.96, "fp": 0.04}]}))
    assert Runtime(authority=authority, use_llm=True).use_llm is True
    assert Runtime(authority=authority).use_llm is False  # default stays off
