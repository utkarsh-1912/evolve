#!/usr/bin/env python3
"""Rebuild apps/counselor/messages/ar.json from en.json (R-UX-2).

Arabic copy is not written yet: every value is the English placeholder, flagged TODO(ar) and pending native
clinical review (docs/03 §8, TODO(native-review)). Keys already translated in ar.json (values containing Arabic script)
are kept. The language switch is mirrored (AR page links to English). 0 missing keys.
Usage: python apps/counselor/scripts/sync_ar_placeholders.py
"""
from __future__ import annotations

import json
import pathlib

MSG = pathlib.Path(__file__).resolve().parents[1] / "messages"


def merge(en, ar):
    if isinstance(en, dict):
        ar = ar if isinstance(ar, dict) else {}
        return {k: merge(v, ar.get(k)) for k, v in en.items()}
    # Keep only real Arabic translations; stale English copies are refreshed from en.json.
    is_ar = isinstance(ar, str) and any(0x0600 <= ord(ch) <= 0x06FF for ch in ar)
    return ar if is_ar else en


def main() -> None:
    en = json.loads((MSG / "en.json").read_text(encoding="utf-8"))
    path = MSG / "ar.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    out = {"_todo": "TODO(ar): English placeholders pending Arabic translation and native clinical review."}
    out.update(merge(en, old))
    out["chrome"]["lang"] = {"switchTo": "English", "switchToLang": "en"}
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.name}")


if __name__ == "__main__":
    main()
