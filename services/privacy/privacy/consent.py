"""Consent store + couple workspace (R-PRIV-2, guardrails P-07, P-08).

* Consent resources follow ``contracts/consent.schema.json`` and are signed with HMAC-SHA256 by the
  consent service over the canonical JSON of every field except ``signature``.
* Validity = schema-valid + signature valid + ``status == "active"`` + ``start <= now < end`` +
  not in the revocation registry. The registry makes a stale, still-"active" copy of a revoked
  consent useless (replay of an old consent blob is refused).
* Two purposes (DECISIONS #16, #40): ``apsi-couple-compatibility`` (default; no ``scope`` key, so
  records are byte-identical to the original P1 format) and ``disclose-gene-to-partner``, which must
  carry ``scope = {"hgnc_id": <int>}`` naming exactly one panel gene. ``scope`` is part of the
  signed body. APSI accepts only ``apsi-couple-compatibility`` consents (``check_pair``).
* A ``CoupleWorkspace`` holds ONLY an ``ok`` APSI result (schema-validated, so nothing but the
  intersection can be stored). ``ConsentService.revoke`` purges every workspace that references
  the consent and invalidates its token synchronously, well inside the 5 s budget.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import logging
import pathlib
import secrets
import threading
from datetime import datetime, timedelta

import jsonschema

from ._common import Clock, canonical, hgnc_universe, iso, parse_iso, utcnow
from .audit import AuditLog, default_audit_log

log = logging.getLogger("privacy.consent")

_CONTRACTS = pathlib.Path(__file__).resolve().parents[3] / "contracts"
CONSENT_SCHEMA = json.loads((_CONTRACTS / "consent.schema.json").read_text(encoding="utf-8"))
APSI_SCHEMA = json.loads((_CONTRACTS / "apsi_result.schema.json").read_text(encoding="utf-8"))
PURPOSE = "apsi-couple-compatibility"
DISCLOSE_PURPOSE = "disclose-gene-to-partner"
PURPOSES = frozenset({PURPOSE, DISCLOSE_PURPOSE})
DEFAULT_CONSENT_TTL = timedelta(days=30)


class WorkspaceError(Exception):
    """Unknown, revoked or purged workspace token."""


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class WorkspaceStore:
    """Couple workspaces. Each holds exactly one schema-valid ``ok`` APSI result and nothing else."""

    def __init__(self, audit: AuditLog):
        self._audit = audit
        self._lock = threading.Lock()
        self._by_token: dict[str, dict] = {}            # sha256(token) -> {"workspace_id", "result"}
        self._by_consent: dict[str, set[str]] = {}       # consent_id -> {sha256(token)}

    def open(self, apsi_result: dict) -> str:
        jsonschema.validate(apsi_result, APSI_SCHEMA)
        if apsi_result["status"] != "ok":
            raise WorkspaceError("only a completed APSI result may enter the couple workspace")
        token = secrets.token_urlsafe(32)
        key = _token_key(token)
        ws_id = "ws-" + secrets.token_hex(8)
        with self._lock:
            self._by_token[key] = {"workspace_id": ws_id, "result": copy.deepcopy(apsi_result)}
            for cid in apsi_result["consent_ids"]:
                self._by_consent.setdefault(cid, set()).add(key)
        self._audit.append("workspace.create", "success", entity=[ws_id, *apsi_result["consent_ids"]])
        return token

    def read(self, token: str) -> dict:
        key = _token_key(token)
        with self._lock:
            entry = self._by_token.get(key)
            entry = copy.deepcopy(entry) if entry else None
        if entry is None:
            self._audit.append("workspace.read", "denied", detail={"reason": "invalid_token"})
            raise WorkspaceError("workspace token invalid or revoked")
        self._audit.append("workspace.read", "success", entity=[entry["workspace_id"]])
        return entry["result"]

    def purge_for_consent(self, consent_id: str) -> int:
        with self._lock:
            keys = self._by_consent.pop(consent_id, set())
            n = 0
            for key in keys:
                entry = self._by_token.pop(key, None)
                if entry is None:
                    continue
                n += 1
                for cid in entry["result"]["consent_ids"]:
                    self._by_consent.get(cid, set()).discard(key)
            return n

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_token)


class ConsentService:
    def __init__(self, *, audit: AuditLog | None = None, clock: Clock = utcnow, key: bytes | None = None):
        self._key = key or secrets.token_bytes(32)  # in-memory dev key, never persisted
        self._audit = audit if audit is not None else default_audit_log()
        self._clock = clock
        self._revoked: set[str] = set()
        self._lock = threading.Lock()
        self.workspaces = WorkspaceStore(self._audit)

    # --- signing -------------------------------------------------------------------------
    def _sign(self, body: dict) -> str:
        mac = hmac.new(self._key, canonical(body), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(mac).decode("ascii").rstrip("=")

    def verify_signature(self, consent: dict) -> bool:
        body = {k: v for k, v in consent.items() if k != "signature"}
        return hmac.compare_digest(self._sign(body), str(consent.get("signature", "")))

    # --- lifecycle -----------------------------------------------------------------------
    @staticmethod
    def _scope_problem(purpose, scope) -> str | None:
        """None if (purpose, scope) is a legal combination, else a reason code."""
        if purpose not in PURPOSES:
            return "unknown_purpose"
        if purpose == PURPOSE:
            return None if scope is None else "scope_not_allowed"
        if not isinstance(scope, dict) or set(scope) != {"hgnc_id"}:
            return "scope_must_name_one_gene"
        hid = scope["hgnc_id"]
        if isinstance(hid, bool) or not isinstance(hid, int) or hid not in hgnc_universe():
            return "scope_gene_not_in_panel"
        return None

    def create(self, patient: str, counterpart: str, *, start: datetime | None = None,
               end: datetime | None = None, status: str = "active", purpose: str = PURPOSE,
               scope: dict | None = None) -> dict:
        """Create and sign a Consent. ``scope`` is required (exactly ``{"hgnc_id": int}``) for
        ``disclose-gene-to-partner`` and forbidden for ``apsi-couple-compatibility``."""
        problem = self._scope_problem(purpose, scope)
        if problem:
            raise ValueError(f"invalid consent purpose/scope: {problem}")
        start = start or self._clock()
        end = end or start + DEFAULT_CONSENT_TTL
        body = {
            "resourceType": "Consent",
            "id": "consent-" + secrets.token_hex(12),
            "status": status,
            "patient": patient,
            "purpose": purpose,
            "counterpart": counterpart,
            "period": {"start": iso(start), "end": iso(end)},
        }
        if purpose == DISCLOSE_PURPOSE:
            body["scope"] = {"hgnc_id": int(scope["hgnc_id"])}  # inside the signed body
        consent = {**body, "signature": self._sign(body)}
        jsonschema.validate(consent, CONSENT_SCHEMA)
        self._audit.append("consent.create", "success", entity=[consent["id"]], detail={"status": status, "purpose": purpose})
        return consent

    def revoke(self, consent: dict | str) -> dict | None:
        """Revoke by consent (or id). Purges couple workspaces, kills tokens, writes one AuditEvent."""
        cid = consent if isinstance(consent, str) else consent["id"]
        with self._lock:
            self._revoked.add(cid)
        purged = self.workspaces.purge_for_consent(cid)
        self._audit.append("consent.revoke", "success", entity=[cid], detail={"purged_workspaces": purged})
        log.info("consent revoked id=%s purged_workspaces=%d", cid, purged)
        if isinstance(consent, dict):
            body = {k: v for k, v in consent.items() if k != "signature"}
            body["status"] = "inactive"
            return {**body, "signature": self._sign(body)}
        return None

    def is_revoked(self, consent_id: str) -> bool:
        with self._lock:
            return consent_id in self._revoked

    def check(self, consent: dict | None, now: datetime | None = None, *, purpose: str | None = None) -> str | None:
        """Return None if valid, else a short non-identifying reason code.

        If ``purpose`` is given, the consent must be for exactly that purpose.
        """
        now = now or self._clock()
        if not consent:
            return "missing"
        try:
            jsonschema.validate(consent, CONSENT_SCHEMA)
        except jsonschema.ValidationError:
            return "malformed"
        if not self.verify_signature(consent):
            return "bad_signature"
        if self._scope_problem(consent["purpose"], consent.get("scope")):
            return "malformed"
        if purpose is not None and consent["purpose"] != purpose:
            return "wrong_purpose"
        if self.is_revoked(consent["id"]):
            return "revoked"
        if consent["status"] != "active":
            return "not_active"
        try:
            start, end = parse_iso(consent["period"]["start"]), parse_iso(consent["period"]["end"])
        except (ValueError, KeyError):
            return "malformed"
        if not (start <= now < end):
            return "expired_or_not_started"
        return None

    def check_pair(self, a: dict | None, b: dict | None, now: datetime | None = None) -> str | None:
        for c in (a, b):
            reason = self.check(c, now, purpose=PURPOSE)  # APSI accepts only APSI consents
            if reason:
                return reason
        if a["id"] == b["id"] or a["patient"] == b["patient"]:
            return "not_two_partners"
        if a["counterpart"] != b["patient"] or b["counterpart"] != a["patient"]:
            return "not_mutual"
        return None


_default: ConsentService | None = None


def default_consent_service() -> ConsentService:
    global _default
    if _default is None:
        _default = ConsentService()
    return _default
