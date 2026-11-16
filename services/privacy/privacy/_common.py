"""Shared helpers for the privacy package (R-PRIV-1/2/4). No secrets, no gene symbols here."""
from __future__ import annotations

import base64
import json
import pathlib
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Callable

Clock = Callable[[], datetime]

_PANEL = pathlib.Path(__file__).resolve().parents[3] / "contracts" / "gene_panel.json"
CONTRACT_VERSION = "1.0.0"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must carry a timezone")
    return dt


def canonical(obj: Any) -> bytes:
    """Deterministic JSON encoding used for every signature / hash in this package."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@lru_cache(maxsize=1)
def hgnc_universe() -> frozenset[int]:
    """HGNC ID universe the authority will certify (contracts/gene_panel.json, read-only)."""
    panel = json.loads(_PANEL.read_text(encoding="utf-8"))
    return frozenset(int(g["hgnc_id"]) for g in panel["genes"])
