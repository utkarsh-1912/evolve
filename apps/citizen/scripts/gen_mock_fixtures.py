#!/usr/bin/env python3
"""Record the SIMULATED mock fixtures for apps/citizen by replaying the V1–V5 journeys through the REAL backend
(services/api FastAPI app, in-process via TestClient). R-UX-1; TASK-P3-UI-CIT.

Why record instead of hand-write: the mock then returns exactly what the live API returns (contracts/api.md v1.2.1),
including the closed template set (DECISIONS #37) and locked RiskOutputs from services/risk_engine. No number is
typed by hand. The backend is only imported and called in memory; nothing under services/ is written
(PYTHONDONTWRITEBYTECODE is forced).

Also writes apps/citizen/messages/_api.en.json: the backend's gate-checked EN reference text for every i18n key it
returns (title_key/body_key/note_key, teach-back statements), merged into messages/en.json by sync_i18n.py.

Usage: python apps/citizen/scripts/gen_mock_fixtures.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

APP = pathlib.Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "services" / "agents"))

from fastapi.testclient import TestClient  # noqa: E402
from evolve_api.main import app  # noqa: E402
from runtime import templates  # noqa: E402

VIGNETTES = ["V1", "V2", "V3", "V4", "V5"]
# Stable timestamps make screenshots and visual baselines deterministic; the mock shifts them to "now" at runtime.
VOLATILE = {"ts", "created_at", "expires_at", "issued_at", "expiry", "due", "start", "end"}


def dedupe(items: list[dict]) -> list[dict]:
    """Recording runs the check from both partners, which repeats loop notifications; keep the newest per key."""
    seen, out = set(), []
    for n in items:  # newest first
        k = (n["kind"], n["title_key"])
        if k not in seen:
            seen.add(k)
            out.append(n)
    return out


def main() -> None:
    c = TestClient(app)
    c.post("/api/demo/reset")
    vignettes = c.get("/api/demo/vignettes").json()
    out: dict = {
        "_label": "SIMULATED. Synthetic data only. Recorded by apps/citizen/scripts/gen_mock_fixtures.py from the real "
                  "backend (services/api, in-process) over V1..V5. Numbers come from services/risk_engine. Do not edit by hand.",
        "vignettes": vignettes, "partners": {}, "teachback_key": {t["id"]: t["answer"] for t in templates.TEACHBACK},
    }

    def session(pid: str) -> dict:
        tok = c.post("/api/session", json={"partner_id": pid}).json()["token"]
        return {"Authorization": f"Bearer {tok}"}

    for v in vignettes:
        a, b = v["partner_ids"]
        ha, hb = session(a), session(b)
        pre = {pid: {"vault": c.get("/api/me/vault", headers=h).json(),
                     "care_plan": c.get("/api/me/care-plan", headers=h).json(),
                     "notifications": c.get("/api/me/notifications", headers=h).json()}
               for pid, h in ((a, ha), (b, hb))}
        c.post("/api/consents", json={"counterpart": b}, headers=ha)
        c.post("/api/consents", json={"counterpart": a}, headers=hb)
        compat_a = c.post(f"/api/couples/{v['couple_id']}/compatibility", headers=ha).json()
        for pid, h, other in ((a, ha, b), (b, hb, a)):
            compat = compat_a if pid == a else c.post(f"/api/couples/{v['couple_id']}/compatibility", headers=h).json()
            vault = c.get("/api/me/vault", headers=h).json()
            fam = {}
            for call in vault["calls"]:
                if call["classification"] in ("P", "LP"):
                    r = c.post("/api/family/tokens", json={"hgnc_id": call["hgnc_id"]}, headers=h)
                    if r.status_code == 200:
                        fam[str(call["hgnc_id"])] = r.json()
            out["partners"][pid] = {
                "couple_id": v["couple_id"], "counterpart": other,
                "vault": vault,
                "compatibility": {"apsi": compat["apsi"], "records": compat["records"], "messages": compat["messages"],
                                  "review_required": compat["review_required"]},
                "messages": c.get("/api/me/messages", headers=h).json(),
                "care_plan_pre": pre[pid]["care_plan"],
                "care_plan_post": c.get("/api/me/care-plan", headers=h).json(),
                "notifications_pre": pre[pid]["notifications"],
                "notifications_post": dedupe(c.get("/api/me/notifications", headers=h).json()),
                "teachback": c.post("/api/me/teachback/start", headers=h).json(),
                "family_tokens": fam,
            }
        c.post("/api/demo/reset")

    dest = APP / "lib" / "mock" / "fixtures.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # Backend EN reference text for every key it returns (nested so next-intl can resolve "care.option.x.title").
    nested: dict = {}
    for key, text in templates.I18N_EN.items():
        node = nested
        *path, leaf = key.split(".")
        for p in path:
            node = node.setdefault(p, {})
        node[leaf] = text
    (APP / "messages" / "_api.en.json").write_text(json.dumps(nested, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {dest.relative_to(ROOT)} and messages/_api.en.json ({len(templates.I18N_EN)} keys)")


if __name__ == "__main__":
    main()
