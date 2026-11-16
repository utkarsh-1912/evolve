"""SarvamClient + counselor AI draft (DECISIONS #62, P-21). Fake HTTP transport only: no network in tests."""
import json
import logging

import pytest

from conftest import consent_both
from runtime import counselor_draft, policy
from runtime.llm_sarvam import LLMUnavailable, OfflineStubClient, SarvamClient, client_from_env
from runtime.orchestrator import Runtime


class FakeTransport:
    """Scripted responses: each item is (status, body_dict) or an Exception to raise."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append({"url": url, "headers": headers, "body": json.loads(body), "timeout": timeout})
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        status, payload = r
        return status, json.dumps(payload).encode()


def ok(text, **extra):
    return 200, {"choices": [{"message": {"content": text, **extra}, "finish_reason": "stop"}]}


def err(status, code):
    return status, {"error": {"message": code, "code": code, "request_id": "r1"}}


def client(*responses, sleeps=None):
    t = FakeTransport(*responses)
    c = SarvamClient("test-key", transport=t, sleep=(sleeps.append if sleeps is not None else lambda s: None))
    return c, t


# --------------------------------------------------------------------- client
def test_success_payload_and_headers():
    c, t = client(ok("Summary text.", reasoning_content="hidden chain"))
    assert c.complete("SYS", "USER") == "Summary text."
    call = t.calls[0]
    assert call["url"].endswith("/v1/chat/completions") and call["timeout"] == 20.0
    assert call["headers"]["api-subscription-key"] == "test-key"
    b = call["body"]
    assert b["model"] == "sarvam-105b" and b["temperature"] == 0.2 and b["reasoning_effort"] == "none"
    assert b["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]


@pytest.mark.parametrize("first", [err(429, "rate_limit_exceeded_error"), err(503, "server_busy")])
def test_one_retry_on_429_503(first):
    sleeps = []
    c, t = client(first, ok("Fine."), sleeps=sleeps)
    assert c.complete("S", "U") == "Fine." and len(t.calls) == 2 and sleeps == [1.0]
    c2, t2 = client(first, first)
    with pytest.raises(LLMUnavailable):
        c2.complete("S", "U")
    assert len(t2.calls) == 2  # exactly one retry


def test_402_timeout_and_bad_response_are_unavailable():
    for resp, code in [(err(402, "insufficient_quota_error"), "insufficient_quota"),
                       (TimeoutError("t"), "timeout"), ((200, {"nope": 1}), "bad_response"),
                       (err(500, "x"), "http_500")]:
        c, _ = client(resp)
        with pytest.raises(LLMUnavailable) as e:
            c.complete("S", "U")
        assert e.value.code == code


def test_reasoning_effort_fallback():
    c, t = client(err(422, "reasoning_effort is not supported"), ok("Done."))
    assert c.complete("S", "U") == "Done."
    assert "reasoning_effort" in t.calls[0]["body"] and "reasoning_effort" not in t.calls[1]["body"]


def test_never_logs_prompt_or_response(caplog):
    caplog.set_level(logging.DEBUG)
    c, _ = client(ok("SECRET-RESPONSE-CONTENT"))
    c.complete("SECRET-SYSTEM", "SECRET-USER-PROMPT")
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "SECRET" not in text and "test-key" not in text


def test_client_from_env(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    assert isinstance(client_from_env(), OfflineStubClient)
    monkeypatch.setenv("SARVAM_API_KEY", "k")
    monkeypatch.setenv("SARVAM_MODEL", "sarvam-105b-conversations")
    c = client_from_env(transport=FakeTransport())
    assert isinstance(c, SarvamClient) and c.model == "sarvam-105b-conversations"


def test_sarvam_can_never_drive_patient_text(authority):
    # P-21 / DECISIONS #37: the patient Runtime refuses any LLM unless paraphrase is authorized (it is not)
    with pytest.raises(policy.LLMPolicyError):
        Runtime(authority=authority, llm=SarvamClient("k", transport=FakeTransport()))


# --------------------------------------------------------------------- counselor draft
def _case(rt, cid):
    consent_both(rt, cid)
    rt.run_compatibility(cid)
    return next(c for c in rt.cases.values() if c["couple_id"] == cid)


def test_prompt_is_minimized_consented_scope(rt):
    case = _case(rt, "V3")
    rt.workbench.add_note(case["case_id"], "c1", "PRIVATE-NOTE-TEXT about the family")
    c, t = client(ok("The case concerns SMN1 with a chance per pregnancy of 1 in 321."))
    out = counselor_draft.summary_draft(rt, case["case_id"], c)
    sent = json.dumps(t.calls[0]["body"])
    for forbidden in ("V3A", "V3B", "PRIVATE-NOTE", "Patient/", "consent-", "c.", "p.("):
        assert forbidden not in sent, forbidden
    assert "1 in 321" in sent and "first cousins" in sent
    assert out["draft"] and out["gate"]["passed"] and out["provider"] == "sarvam" and out["ai_generated"] is True
    assert "variants[].offspring_risk_one_in" in out["input_fields"]


def test_out_of_scope_gene_never_in_prompt(rt):
    consent_both(rt, "V4")
    rt.run_compatibility("V4")
    rt.teachback("V4A", [True, True, True, True])  # (d) case for V4A only; V4B's ABCA4 is outside its scope
    case = next(c for c in rt.cases.values() if c["couple_id"] == "V4")
    c, t = client(ok("Two private carrier findings need a conversation."))
    counselor_draft.summary_draft(rt, case["case_id"], c)
    assert "ABCA4" not in json.dumps(t.calls[0]["body"])
    leaky, _ = client(ok("The other partner carries ABCA4."))
    out = counselor_draft.summary_draft(rt, case["case_id"], leaky)
    assert out["draft"] is None and any(v["rule"] == "leakage" for v in out["gate"]["violations"])


@pytest.mark.parametrize("bad,rule", [
    ("The chance per pregnancy is 1 in 50.", "numeric_drift"),
    ("The couple " + "should " + "not marry.", "directive"),
    ("They could consider " + "donor " + "eggs.", "uae_law"),
    ("Their children will be completely safe.", "false_reassurance"),
])
def test_gate_blocks_bad_drafts(rt, bad, rule):
    case = _case(rt, "V3")
    c, _ = client(ok(bad))
    out = counselor_draft.summary_draft(rt, case["case_id"], c)
    assert out["draft"] is None and out["gate"]["passed"] is False
    assert rule in {v["rule"] for v in out["gate"]["violations"]}


def test_offline_stub_draft_passes_and_is_not_stored(rt):
    case = _case(rt, "V1")
    before = json.dumps(rt.workbench.case_view(case["case_id"], "c1", True)["notes"])
    out = counselor_draft.summary_draft(rt, case["case_id"], OfflineStubClient())
    assert out["provider"] == "offline-stub" and out["gate"]["passed"] and "1 in 4" in out["draft"]
    assert json.dumps(rt.workbench.case_view(case["case_id"], "c1", True)["notes"]) == before
    assert not any(out["draft"] in json.dumps(e) for e in rt.audit.events())
