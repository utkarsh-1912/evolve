import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def run(*a):
    return subprocess.run([sys.executable, str(ROOT / "scripts/guardrail_check.py"), *a], capture_output=True, text=True)


def test_repo_is_clean():
    assert run().returncode == 0


def test_detects_risk_arithmetic_and_wildcard_scope():
    d = ROOT / "services" / "agents"
    d.mkdir(parents=True, exist_ok=True)
    bad = d / "_tmp_bad.py"
    bad.write_text('scope = "patient/*.rs"\ndef f(risk, q):\n    return risk * q\n')
    try:
        r = run()
        assert r.returncode == 1 and "P-02" in r.stdout and "P-10" in r.stdout
    finally:
        bad.unlink()


def test_pr_body_requires_requirement_id(tmp_path):
    f = tmp_path / "b.md"
    f.write_text("no ids here")
    assert run("--pr-body", str(f)).returncode == 1
    f.write_text("R-RISK-2\n## Guardrail Attestation\n")
    assert run("--pr-body", str(f)).returncode == 0
