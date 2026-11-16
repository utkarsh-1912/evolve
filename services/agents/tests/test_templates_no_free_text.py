"""G2 (b), DECISIONS #37: no code path delivers non-template text to a patient.

1. LLM paraphrase is off by default and refused at startup unless env EVOLVE_ALLOW_LLM_PARAPHRASE=1 AND a recorded
   held-out pass file shows >= 2 fresh sets at >= 95% catch / <= 5% FP (runtime/policy.py, read-only here).
2. Structural: the only writer of a patient's message list is Runtime._deliver, and _deliver takes a Draft rendered
   by CulturalCommunicator; with the flag off the communicator's paraphrase hook is never called.
3. Counselor notes / closure summaries never reach a patient-facing surface (messages, notifications, home, care plan,
   activity, vault) and gate-probe drafts are never delivered.
"""
import ast
import json
import pathlib

import pytest

from conftest import consent_both
from runtime import policy
from runtime.llm import StubLLM
from runtime.orchestrator import Runtime

RUNTIME_DIR = pathlib.Path(__file__).resolve().parents[1] / "runtime"
API_DIR = pathlib.Path(__file__).resolve().parents[2] / "api"


@pytest.fixture
def pass_file(tmp_path, monkeypatch):
    f = tmp_path / "holdout_pass.json"
    monkeypatch.setattr(policy, "HOLDOUT_PASS_FILE", f)
    monkeypatch.delenv(policy.ENV_FLAG, raising=False)
    return f


def _write(f, sets):
    f.write_text(json.dumps({"sets": sets}), encoding="utf-8")


def test_paraphrase_flag_defaults_off(authority, pass_file):
    rt = Runtime(authority=authority)
    assert rt.use_llm is False
    assert policy.llm_paraphrase_allowed() is False


@pytest.mark.parametrize("env,sets", [
    (None, None),                                                    # nothing
    ("1", None),                                                     # env only, no pass file
    (None, [{"name": "v2", "catch": 0.99, "fp": 0.01}, {"name": "v3", "catch": 0.99, "fp": 0.01}]),  # file only
    ("1", [{"name": "v2", "catch": 0.99, "fp": 0.01}]),              # one passing set is not enough
    ("1", [{"name": "v2", "catch": 0.94, "fp": 0.01}, {"name": "v3", "catch": 0.99, "fp": 0.01}]),  # catch < 95%
    ("1", [{"name": "v2", "catch": 0.99, "fp": 0.06}, {"name": "v3", "catch": 0.99, "fp": 0.01}]),  # FP > 5%
    ("true", [{"name": "v2", "catch": 0.99, "fp": 0.01}, {"name": "v3", "catch": 0.99, "fp": 0.01}]),  # env must be "1"
])
def test_llm_refused_at_startup_unless_env_and_pass_file(authority, pass_file, monkeypatch, env, sets):
    if env is not None:
        monkeypatch.setenv(policy.ENV_FLAG, env)
    if sets is not None:
        _write(pass_file, sets)
    with pytest.raises(policy.LLMPolicyError):
        Runtime(authority=authority, llm=StubLLM())
    with pytest.raises(policy.LLMPolicyError):
        Runtime(authority=authority, use_llm=True)


def test_corrupt_pass_file_fails_closed(authority, pass_file, monkeypatch):
    monkeypatch.setenv(policy.ENV_FLAG, "1")
    pass_file.write_text("{not json", encoding="utf-8")
    with pytest.raises(policy.LLMPolicyError):
        Runtime(authority=authority, llm=StubLLM())


def test_llm_allowed_only_with_env_and_two_passing_sets(authority, pass_file, monkeypatch):
    monkeypatch.setenv(policy.ENV_FLAG, "1")
    _write(pass_file, [{"name": "v2", "catch": 0.96, "fp": 0.04}, {"name": "v3", "catch": 0.95, "fp": 0.05}])
    assert Runtime(authority=authority, llm=StubLLM()).use_llm is True


def test_no_real_pass_file_is_committed():
    """The pass file is qa-redteam's evidence; while held-out v2/v3 are not both passed it must not exist."""
    f = RUNTIME_DIR / "templates_verify" / "holdout_pass.json"
    if f.exists():
        data = json.loads(f.read_text(encoding="utf-8"))
        assert all(isinstance(s, dict) and {"name", "catch", "fp"} <= set(s) for s in data.get("sets", [])), \
            "holdout_pass.json exists but is malformed"


def test_paraphrase_hook_never_called_when_flag_off(authority, monkeypatch):
    rt = Runtime(authority=authority)
    calls = []
    monkeypatch.setattr(rt.communicator, "paraphrase", lambda *a, **k: calls.append(1) or "free text")
    for cid in ("V1", "V3", "V5"):
        consent_both(rt, cid)
        rt.run_compatibility(cid)
    rt.teachback("V1A", [True, True, True, True])  # wrong answer -> escalation (d) message
    assert calls == []
    for pid in ("V1A", "V1B", "V3A", "V3B", "V5A", "V5B"):
        assert all(m["text"] != "free text" for m in rt.messages(pid))


def _message_writers(tree: ast.AST) -> list[str]:
    """Functions that append/extend/assign to a `.messages` attribute."""
    hits = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for n in ast.walk(fn):
            target = None
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "extend", "insert"):
                target = n.func.value
            elif isinstance(n, (ast.Assign, ast.AugAssign)):
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    if isinstance(t, ast.Attribute) and t.attr == "messages":
                        target = t
            if isinstance(target, ast.Attribute) and target.attr == "messages":
                hits.append(fn.name)
    return hits


def test_only_deliver_writes_patient_messages():
    writers = {}
    for p in list(RUNTIME_DIR.rglob("*.py")) + list(API_DIR.rglob("*.py")):
        if "tests" in p.parts:
            continue
        found = _message_writers(ast.parse(p.read_text(encoding="utf-8")))
        if found:
            writers[p.name] = sorted(set(found))
    # _deliver appends gate-passed template renders; _purge_couple only REMOVES messages (P-07 revocation)
    assert writers == {"orchestrator.py": ["_deliver", "_purge_couple"]}, writers


def test_purge_only_filters_existing_messages():
    src = (RUNTIME_DIR / "orchestrator.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "_purge_couple")
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == "messages" for t in n.targets):
            assert isinstance(n.value, ast.ListComp), "purge must only filter the existing list"
            assert isinstance(n.value.generators[0].iter, ast.Attribute) and n.value.generators[0].iter.attr == "messages"


def test_deliver_takes_a_communicator_draft():
    src = (RUNTIME_DIR / "orchestrator.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "_deliver":
            draft_arg = n.args[1]
            assert isinstance(draft_arg, ast.Call) or isinstance(draft_arg, ast.Name), ast.dump(draft_arg)
            if isinstance(draft_arg, ast.Call):
                f = draft_arg.func
                assert isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) and f.value.attr == "communicator", \
                    "every delivered draft must be built by CulturalCommunicator"


def _patient_surfaces(rt, pid):
    p = rt.portal
    return json.dumps([rt.messages(pid), p.notifications(pid), p.home(pid), p.care_plan(pid), p.activity(pid), rt.vault(pid)],
                      ensure_ascii=False, default=str)


def test_counselor_notes_never_reach_patients(authority):
    rt = Runtime(authority=authority)
    consent_both(rt, "V1")
    rt.run_compatibility("V1")
    case_id = next(c["case_id"] for c in rt.cases.values() if c["couple_id"] == "V1")
    marker = "ZQX-NOTE-CANARY-7731"
    before = {pid: (len(rt.messages(pid)), len(rt.portal.notifications(pid))) for pid in ("V1A", "V1B")}
    rt.workbench.add_note(case_id, "counselor-1", f"{marker} private counselor note")
    rt.workbench.closure(case_id, "counselor-1", f"{marker} closure summary")
    for pid in ("V1A", "V1B"):
        assert marker not in _patient_surfaces(rt, pid)
        assert len(rt.messages(pid)) == before[pid][0]
        assert all(n.get("title_key", "").startswith("notif.") for n in rt.portal.notifications(pid))
    assert all(n["visible_to_patient"] is False for n in rt.workbench.notes[case_id])


def test_gate_probe_never_delivers(authority):
    rt = Runtime(authority=authority)
    consent_both(rt, "V3")
    rt.run_compatibility("V3")
    before = len(rt.messages("V3B"))
    rt.gate_probe("V3B", "A benign probe sentence for the demo.", "en", "care")
    rt.gate_probe("V3B", "ZQX-PROBE-CANARY", "en", "care")
    assert len(rt.messages("V3B")) == before
    assert "ZQX-PROBE-CANARY" not in _patient_surfaces(rt, "V3B")
