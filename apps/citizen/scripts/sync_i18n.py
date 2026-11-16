#!/usr/bin/env python3
"""i18n build for apps/citizen (docs/09 §7).

en.json : UI strings (hand-edited) + `api` = backend EN key table (messages/_api.en.json).
ar.json : UI strings from scripts/ar_ui.py (Modern Standard Arabic) + `api` = backend AR key table
          (messages/_api.ar.json, runtime/i18n_ar.py). No English placeholders: a key missing in Arabic FAILS the build.
Review status lives in messages/AR-REVIEW.md, never inside the strings.

Usage: python apps/citizen/scripts/sync_i18n.py
"""
import json
import pathlib
import sys

APP = pathlib.Path(__file__).resolve().parents[1]
HERE = APP / "messages"
sys.path.insert(0, str(APP / "scripts"))
from ar_ui import AR  # noqa: E402


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def dump(name: str, data) -> None:
    (HERE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def leaves(d, p=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from leaves(v, f"{p}{k}.")
        else:
            yield f"{p}{k}", v


en = load("en.json")
en["api"] = load("_api.en.json")
dump("en.json", en)

ar = json.loads(json.dumps(AR))
ar["api"] = load("_api.ar.json")
en_keys = {k for k, _ in leaves(en)}
ar_keys = {k for k, _ in leaves(ar)}
missing = sorted(en_keys - ar_keys)
extra = sorted(ar_keys - en_keys)
if missing or extra:
    sys.exit(f"i18n key mismatch. missing in ar: {missing[:20]} extra in ar: {extra[:20]}")
dump("ar.json", ar)
print(f"i18n synced: {len(en_keys)} keys, en/ar parity OK")
