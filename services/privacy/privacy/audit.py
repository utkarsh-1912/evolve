"""Append-only, hash-chained AuditEvent log (R-PRIV-1/2, guardrail P-10, P-12).

Each event carries ``prev_hash`` and ``hash = sha256(prev_hash || canonical(event_without_hash))``.
Altering, deleting, inserting or reordering any event breaks the chain (``verify_chain``).
Events reference only opaque identifiers (consent ids, set ids, workspace ids); they never carry
gene symbols, HGNC IDs or variant strings.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import pathlib
import secrets
import threading

from ._common import Clock, canonical, iso, utcnow

GENESIS = "0" * 64
ALLOWED_DETAIL_KEYS = {"reason", "purged_workspaces", "status", "purpose"}


def _event_hash(prev_hash: str, body: dict) -> str:
    return hashlib.sha256(prev_hash.encode("ascii") + canonical(body)).hexdigest()


class AuditLog:
    def __init__(self, path: str | pathlib.Path | None = None, *, clock: Clock = utcnow):
        self._events: list[dict] = []
        self._lock = threading.Lock()
        self._clock = clock
        self._path = pathlib.Path(path) if path else None

    def append(self, action: str, outcome: str, *, entity: list[str] | None = None, agent: str = "privacy-service",
               detail: dict | None = None) -> str:
        detail = dict(detail or {})
        if set(detail) - ALLOWED_DETAIL_KEYS:
            raise ValueError("audit detail may carry only opaque, non-genomic fields")
        with self._lock:
            prev = self._events[-1]["hash"] if self._events else GENESIS
            body = {
                "resourceType": "AuditEvent",
                "id": "audit-" + secrets.token_hex(8),
                "seq": len(self._events),
                "recorded": iso(self._clock()),
                "action": action,
                "outcome": outcome,
                "agent": agent,
                "entity": list(entity or []),
                "detail": detail,
                "prev_hash": prev,
            }
            event = {**body, "hash": _event_hash(prev, body)}
            self._events.append(event)
            if self._path:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event, sort_keys=True) + "\n")
            return event["id"]

    def events(self) -> list[dict]:
        """Copies only: callers cannot mutate the stored chain."""
        with self._lock:
            return copy.deepcopy(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def verify(self) -> bool:
        with self._lock:
            return verify_chain(self._events)

    @staticmethod
    def verify_file(path: str | pathlib.Path) -> bool:
        lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        try:
            events = [json.loads(line) for line in lines if line.strip()]
        except json.JSONDecodeError:
            return False
        return verify_chain(events)


def verify_chain(events: list[dict]) -> bool:
    prev = GENESIS
    for i, ev in enumerate(events):
        body = {k: v for k, v in ev.items() if k != "hash"}
        if body.get("seq") != i or body.get("prev_hash") != prev:
            return False
        if not hmac.compare_digest(_event_hash(prev, body), str(ev.get("hash", ""))):
            return False
        prev = ev["hash"]
    return True


_default: AuditLog | None = None


def default_audit_log() -> AuditLog:
    global _default
    if _default is None:
        _default = AuditLog()
    return _default
