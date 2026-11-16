import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # services/api

from evolve_api import bootstrap  # noqa: E402,F401


@pytest.fixture(scope="session")
def authority():
    from privacy.authority import Authority
    return Authority()


@pytest.fixture
def client(authority):
    from fastapi.testclient import TestClient
    from evolve_api.main import create_app
    from runtime.orchestrator import Runtime
    app = create_app(Runtime(authority=authority))
    with TestClient(app) as c:
        c.rt = app.state.runtime
        yield c


def login(client, partner_id=None, role=None):
    body = {"role": role} if role else {"partner_id": partner_id}
    r = client.post("/api/session", json=body)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def consent_both(client, couple_id):
    ha, hb = login(client, f"{couple_id}A"), login(client, f"{couple_id}B")
    ca = client.post("/api/consents", json={"counterpart": f"{couple_id}B"}, headers=ha).json()
    cb = client.post("/api/consents", json={"counterpart": f"{couple_id}A"}, headers=hb).json()
    return ha, hb, ca, cb
