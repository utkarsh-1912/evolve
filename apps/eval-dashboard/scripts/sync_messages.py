#!/usr/bin/env python3
"""Keep messages/{en,ar}.json in step (docs/09 §7 i18n).

1. `ui` (the @evolve/ui component labels) is copied from apps/citizen/messages/en.json into en.json, so the design
   system reads the same in every app.
2. ar.json is AUTHORED (Modern Standard Arabic, terminology from handoffs/AR-REVIEW-SHEET.md; review status in
   messages/AR-REVIEW.md). This script never overwrites a translation: it only mirrors en.json's key structure,
   drops keys that no longer exist, and inserts the English text for NEW keys, listing them so they get translated.
   e2e/i18n.spec.ts fails while any Arabic value lacks Arabic script (outside the token allowlist).
Run after editing en.json:  python apps/eval-dashboard/scripts/sync_messages.py
"""
import json
import pathlib

APP = pathlib.Path(__file__).resolve().parents[1]
MSG = APP / "messages"
CITIZEN = APP.parent / "citizen" / "messages" / "en.json"

en = json.loads((MSG / "en.json").read_text(encoding="utf-8"))
en["ui"] = json.loads(CITIZEN.read_text(encoding="utf-8"))["ui"]
(MSG / "en.json").write_text(json.dumps(en, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

ar_path = MSG / "ar.json"
old = json.loads(ar_path.read_text(encoding="utf-8")) if ar_path.exists() else {}
missing: list[str] = []


def merge(e, a, path=""):
    if isinstance(e, dict):
        return {k: merge(v, a.get(k) if isinstance(a, dict) else None, f"{path}{k}.") for k, v in e.items()}
    if isinstance(a, str):
        return a
    missing.append(path.rstrip("."))
    return e


ar = merge(en, old)
ar_path.write_text(json.dumps(ar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"messages synced: en + ar ({len(missing)} new key(s) need Arabic)")
for k in missing:
    print("  TODO(ar):", k)
