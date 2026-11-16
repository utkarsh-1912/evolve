#!/usr/bin/env python3
"""Check/sync apps/counselor/messages/ar.json against en.json (R-UX-2).

Arabic is now real clinical MSA (review notes: messages/AR-REVIEW.md). This script:
  * adds any key that exists in en.json but not in ar.json (English value, reported as MISSING TRANSLATION),
  * drops keys that no longer exist in en.json,
  * keeps every existing Arabic value untouched,
  * reports values without Arabic script (except the allowlisted brand/code tokens) and placeholder mismatches.
Exit code 1 if anything needs translation. Usage: python apps/counselor/scripts/sync_ar_placeholders.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

MSG = pathlib.Path(__file__).resolve().parents[1] / "messages"
# Values that are legitimately Latin in the Arabic UI: brand/instrument/locale tokens (keep in sync with e2e/ar-messages.spec.ts).
ALLOW = {"English", "en", "SURE", "Sarvam"}
SLOT = re.compile(r"\{(\w+)\}")
problems: list[str] = []


def has_ar(s: str) -> bool:
    return any(0x0600 <= ord(ch) <= 0x06FF for ch in s)


def merge(en, ar, path=""):
    if isinstance(en, dict):
        ar = ar if isinstance(ar, dict) else {}
        return {k: merge(v, ar.get(k), f"{path}.{k}" if path else k) for k, v in en.items()}
    if not isinstance(ar, str):
        problems.append(f"MISSING TRANSLATION {path}")
        return en
    if not has_ar(ar) and ar not in ALLOW:
        problems.append(f"NOT ARABIC {path}: {ar!r}")
    if set(SLOT.findall(en)) != set(SLOT.findall(ar)):
        problems.append(f"PLACEHOLDER MISMATCH {path}")
    return ar


def main() -> None:
    en = json.loads((MSG / "en.json").read_text(encoding="utf-8"))
    path = MSG / "ar.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    out = merge(en, old)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in problems:
        print(p)
    print(f"ar.json: {'OK' if not problems else f'{len(problems)} problem(s)'}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
