#!/usr/bin/env python3
"""i18n sync for apps/citizen (docs/09 §7: 0 missing keys in EN, AR keys present and flagged).

1. Merges the backend's gate-checked EN reference text for every key it returns (messages/_api.en.json, written by
   gen_mock_fixtures.py from runtime.templates.I18N_EN; DECISIONS #37) into en.json["api"].
2. Rebuilds messages/ar.json from en.json. Real translations are kept only for dotted keys listed in TRANSLATED
   (none yet; all pending native clinical review), so stale copies can never survive an EN edit.

Usage: python apps/citizen/scripts/sync_i18n.py
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parents[1] / "messages"
TRANSLATED: set[str] = set()  # e.g. {"chrome.nav.home"} once reviewed Arabic exists


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def dump(name: str, data) -> None:
    (HERE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge(e, a, path=""):
    if isinstance(e, dict):
        return {k: merge(v, a.get(k) if isinstance(a, dict) else None, f"{path}{k}.") for k, v in e.items()}
    return a if path.rstrip(".") in TRANSLATED and a is not None else e


en = load("en.json")
if (HERE / "_api.en.json").exists():
    en["api"] = load("_api.en.json")
    dump("en.json", en)

old = load("ar.json") if (HERE / "ar.json").exists() else {}
ar = merge(en, old)
ar["chrome"]["lang"] = {"switchTo": "English", "switchToLang": "en"}
ar["_todo"] = "TODO(ar): English placeholders pending native clinical Arabic review (docs/09 §5, TODO(native-review)). Keys mirror en.json."
dump("ar.json", ar)
print("i18n synced: en.json api keys merged; ar.json rebuilt")
