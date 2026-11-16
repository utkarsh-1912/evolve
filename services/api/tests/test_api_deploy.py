"""Deployment config (contracts/api.md v1.3.0, DECISIONS #62 item 2): GET /api/config, CORS from env, host/port."""
import pathlib


def test_config_ai_draft_disabled_and_environment(client, monkeypatch):
    monkeypatch.delenv("DEPLOY_TARGET", raising=False)
    assert client.get("/api/config").json() == {"ai_draft_enabled": False, "provider": None, "environment": "local"}
    for env in ("vm", "vercel-render"):
        monkeypatch.setenv("DEPLOY_TARGET", env)
        assert client.get("/api/config").json()["environment"] == env
    monkeypatch.setenv("DEPLOY_TARGET", "something-else")
    assert client.get("/api/config").json()["environment"] == "local"


def test_ai_draft_route_not_wired(client):
    h = client.post("/api/session", json={"role": "counselor"}).json()["token"]
    hc = {"Authorization": "Bearer " + h}
    client.post("/api/counselor/shift", json={"on": True}, headers=hc)
    assert client.post("/api/counselor/cases/any/summary-draft", headers=hc).status_code in (404, 405)
    import evolve_api.main as m
    assert not any(n in m.__dict__ for n in ("counselor_draft", "client_from_env", "LLMUnavailable"))


def test_cors_origins_from_env(authority, monkeypatch):
    from fastapi.testclient import TestClient
    from evolve_api.main import create_app
    from runtime.orchestrator import Runtime
    monkeypatch.setenv("CORS_ORIGINS", "https://evolve-demo.example.org, https://counselor.example.org/")
    c = TestClient(create_app(Runtime(authority=authority)))
    for origin in ("https://evolve-demo.example.org", "https://counselor.example.org", "http://localhost:3000",
                   "http://localhost:3001", "http://localhost:3002"):
        r = c.options("/api/config", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
        assert r.headers.get("access-control-allow-origin") == origin, origin
    r = c.options("/api/config", headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") is None


def test_entry_point_binds_all_interfaces_and_env_port():
    src = (pathlib.Path(__file__).resolve().parents[1] / "evolve_api" / "__main__.py").read_text(encoding="utf-8")
    assert 'os.environ.get("HOST", "0.0.0.0")' in src and 'int(os.environ.get("PORT", "8000"))' in src
