#!/usr/bin/env python3
"""Keep messages/{en,ar}.json in step (docs/09 §7 i18n: 0 missing EN keys, AR keys present and flagged).

1. `ui` (the @evolve/ui component labels) is copied from apps/citizen/messages/en.json, so the design system
   reads the same in every app.
2. ar.json is rebuilt from en.json: English placeholders flagged TODO(ar), pending native clinical review.
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

ar = json.loads(json.dumps(en))
ar["chrome"]["switchTo"] = "English"
ar["chrome"]["switchToLang"] = "en"
ar["_todo"] = "TODO(ar): English placeholders pending native clinical Arabic review (TODO(native-review)). Keys mirror en.json."
(MSG / "ar.json").write_text(json.dumps(ar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("messages synced: en + ar")
