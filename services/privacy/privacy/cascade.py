"""Single-locus Cascade Screening Token (R-PRIV-4; source doc §3.2).

Token payload is exactly ``{hgnc_id, variant_digest, issued_at, expiry}``; the issuer API takes no
partner, index-patient or family identifier, so none can end up in the token. The variant itself is
never carried, only ``variant_digest = sha256(normalized variant)`` (hex). Signed with an in-memory
Ed25519 issuer key.

Note: the source doc names a GA4GH VRS digest; the task card fixes sha256 of the normalized
variant for P1. TODO(verify): switch to a VRS-computed digest if/when the orchestrator decides.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ._common import Clock, b64u, b64u_dec, canonical, hgnc_universe, iso, parse_iso, utcnow

PAYLOAD_KEYS = frozenset({"hgnc_id", "variant_digest", "issued_at", "expiry"})
TOKEN_KEYS = PAYLOAD_KEYS | {"signature"}
DEFAULT_TOKEN_TTL = timedelta(days=180)


class CascadeTokenError(Exception):
    pass


def normalize_variant(variant: str | dict) -> str:
    """Normalize a variant description before hashing.

    * dict ``{chrom, pos, ref, alt}`` -> ``"<chrom>:<pos>:<REF>:<ALT>"`` (``chr`` prefix dropped,
      alleles upper-cased)
    * string -> all whitespace removed (case preserved: HGVS is case-sensitive)
    """
    if isinstance(variant, dict):
        chrom = str(variant["chrom"]).strip()
        if chrom.lower().startswith("chr"):
            chrom = chrom[3:]
        return f"{chrom.upper()}:{int(variant['pos'])}:{str(variant['ref']).strip().upper()}:{str(variant['alt']).strip().upper()}"
    if isinstance(variant, str):
        s = "".join(variant.split())
        if not s:
            raise ValueError("empty variant")
        return s
    raise TypeError("variant must be str or dict")


def variant_digest(variant: str | dict) -> str:
    return hashlib.sha256(normalize_variant(variant).encode("utf-8")).hexdigest()


class CascadeIssuer:
    def __init__(self, *, clock: Clock = utcnow, universe: frozenset[int] | None = None):
        self._key = ed25519.Ed25519PrivateKey.generate()  # in memory only
        self._clock = clock
        self._universe = hgnc_universe() if universe is None else universe
        self.public_key = self._key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    def issue(self, hgnc_id: int, variant: str | dict, *, ttl: timedelta = DEFAULT_TOKEN_TTL) -> dict:
        if int(hgnc_id) not in self._universe:
            raise ValueError("id outside the certified panel universe")
        now = self._clock()
        payload = {"hgnc_id": int(hgnc_id), "variant_digest": variant_digest(variant),
                   "issued_at": iso(now), "expiry": iso(now + ttl)}
        return {**payload, "signature": b64u(self._key.sign(canonical(payload)))}


def verify_token(token: dict, issuer_public_key: bytes, *, now=None) -> dict:
    """Return the payload if the token is well-formed, authentic and unexpired; else raise."""
    if not isinstance(token, dict) or set(token) != TOKEN_KEYS:
        raise CascadeTokenError("token fields must be exactly the single-locus payload + signature")
    payload = {k: token[k] for k in PAYLOAD_KEYS}
    if not isinstance(payload["hgnc_id"], int) or not isinstance(payload["variant_digest"], str) \
            or len(payload["variant_digest"]) != 64:
        raise CascadeTokenError("malformed token")
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(issuer_public_key).verify(
            b64u_dec(str(token["signature"])), canonical(payload))
    except (InvalidSignature, ValueError) as exc:
        raise CascadeTokenError("bad signature") from exc
    now = now or utcnow()
    if not (parse_iso(payload["issued_at"]) <= now < parse_iso(payload["expiry"])):
        raise CascadeTokenError("token expired or not yet valid")
    return payload
