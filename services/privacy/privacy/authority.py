"""Certifying authority for carrier sets (R-PRIV-1, guardrail P-09; DECISIONS #5).

The authority (DoH/M42 FHIR server in the source doc §3.2) signs each numeric HGNC ID in a
partner's carrier set with an RSA **full-domain-hash** (FDH) signature:

    sig(i) = FDH(i) ^ d  mod n

FDH signatures are deterministic, so the same gene yields the same signature for both partners,
which is what lets the PSI step (privacy.apsi) match them. Because a client cannot produce
FDH(i)^d without the private exponent, it cannot fabricate set elements to probe its partner.

Per-element signatures alone are transferable between sets, so every set is additionally bound
to ``partner_id``, a single-use ``set_id`` and an ``expiry`` by an **envelope** signed with a
separate Ed25519 key. The envelope commits to the exact list of (hgnc_id, signature) pairs.

Keys are generated in memory at runtime and are never written to disk (P-11).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

from ._common import Clock, b64u, b64u_dec, canonical, hgnc_universe, iso, parse_iso, utcnow

log = logging.getLogger("privacy.authority")

FDH_DOMAIN = b"IDR-APSI-RSA-FDH-v1|"
DEFAULT_SET_TTL = timedelta(hours=1)


class SignatureError(Exception):
    """A carrier set or element failed authority verification."""


def _fdh(hgnc_id: int, n: int) -> int:
    """Full-domain hash of an HGNC ID into Z_n (SHA-256 in counter mode, 128 extra bits to kill bias)."""
    k = (n.bit_length() + 128 + 7) // 8
    msg = FDH_DOMAIN + str(int(hgnc_id)).encode("ascii")
    out = b"".join(hashlib.sha256(ctr.to_bytes(4, "big") + msg).digest() for ctr in range(-(-k // 32)))
    return int.from_bytes(out[:k], "big") % n


def _commitment(elements: Iterable[tuple[int, int]], modulus_len: int) -> str:
    h = hashlib.sha256()
    for hid, sig in sorted(elements):
        h.update(str(hid).encode("ascii") + b":" + sig.to_bytes(modulus_len, "big") + b";")
    return h.hexdigest()


@dataclass(frozen=True)
class AuthorityPublicKey:
    n: int
    e: int
    envelope_key: bytes  # raw Ed25519 public key

    @property
    def modulus_len(self) -> int:
        return (self.n.bit_length() + 7) // 8

    def verify_element(self, hgnc_id: int, sig: int) -> bool:
        if not (0 < sig < self.n):
            return False
        lhs = pow(sig, self.e, self.n).to_bytes(self.modulus_len, "big")
        rhs = _fdh(hgnc_id, self.n).to_bytes(self.modulus_len, "big")
        return hmac.compare_digest(lhs, rhs)  # constant-time compare


@dataclass(frozen=True)
class SignedCarrierSet:
    """A partner's authority-certified carrier set. Held by that partner's own client only."""

    partner_id: str
    set_id: str
    issued_at: str
    expiry: str
    elements: tuple[tuple[int, int], ...]  # (hgnc_id, FDH signature)
    envelope_signature: str
    commitment: str = field(default="")

    def envelope(self) -> dict:
        return {
            "partner_id": self.partner_id,
            "set_id": self.set_id,
            "issued_at": self.issued_at,
            "expiry": self.expiry,
            "commitment": self.commitment,
            "size": len(self.elements),
        }

    @property
    def hgnc_ids(self) -> frozenset[int]:
        return frozenset(h for h, _ in self.elements)


class Authority:
    """Dev certifying authority. Private keys live only in this object's memory."""

    def __init__(self, *, key_size: int = 2048, clock: Clock = utcnow, universe: frozenset[int] | None = None):
        self._rsa = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        self._ed = ed25519.Ed25519PrivateKey.generate()
        self._clock = clock
        self._universe = hgnc_universe() if universe is None else universe
        pn = self._rsa.private_numbers()
        self._p, self._q, self._dp, self._dq, self._qinv = pn.p, pn.q, pn.dmp1, pn.dmq1, pn.iqmp
        pub = pn.public_numbers
        from cryptography.hazmat.primitives import serialization

        raw = self._ed.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.public_key = AuthorityPublicKey(n=pub.n, e=pub.e, envelope_key=raw)

    def _rsa_sign_raw(self, m: int) -> int:
        # CRT exponentiation (fast path for d); result is m^d mod n
        s1 = pow(m, self._dp, self._p)
        s2 = pow(m, self._dq, self._q)
        h = (self._qinv * (s1 - s2)) % self._p
        return s2 + h * self._q

    def sign_element(self, hgnc_id: int) -> int:
        return self._rsa_sign_raw(_fdh(hgnc_id, self.public_key.n))

    def sign_carrier_set(self, partner_id: str, hgnc_ids: Iterable[int], *, ttl: timedelta = DEFAULT_SET_TTL) -> SignedCarrierSet:
        ids = sorted({int(h) for h in hgnc_ids})
        unknown = [h for h in ids if h not in self._universe]
        if unknown:
            # count only - never echo identifiers into logs or messages (P-12)
            raise ValueError(f"{len(unknown)} id(s) outside the certified panel universe")
        if not partner_id:
            raise ValueError("partner_id required")
        now = self._clock()
        elements = tuple((h, self.sign_element(h)) for h in ids)
        commitment = _commitment(elements, self.public_key.modulus_len)
        unsigned = SignedCarrierSet(
            partner_id=partner_id, set_id=secrets.token_hex(16), issued_at=iso(now), expiry=iso(now + ttl),
            elements=elements, envelope_signature="", commitment=commitment,
        )
        sig = self._ed.sign(canonical(unsigned.envelope()))
        log.info("carrier set certified set_id=%s size=%d", unsigned.set_id, len(elements))
        return SignedCarrierSet(**{**unsigned.__dict__, "envelope_signature": b64u(sig)})


def verify_signed_set(pub: AuthorityPublicKey, s: SignedCarrierSet, *, now) -> None:
    """Raise SignatureError unless envelope + every element verify and the set is unexpired."""
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(pub.envelope_key).verify(
            b64u_dec(s.envelope_signature), canonical(s.envelope()))
    except (InvalidSignature, ValueError) as exc:
        raise SignatureError("envelope signature invalid") from exc
    expected = _commitment(s.elements, pub.modulus_len)
    if not hmac.compare_digest(expected, s.commitment):
        raise SignatureError("element list does not match envelope commitment")
    if len({h for h, _ in s.elements}) != len(s.elements):
        raise SignatureError("duplicate element")
    try:
        if not (parse_iso(s.issued_at) <= now < parse_iso(s.expiry)):
            raise SignatureError("carrier set expired or not yet valid")
    except ValueError as exc:
        raise SignatureError("bad timestamp") from exc
    ok = True
    for hid, sig in s.elements:  # check all, no early exit
        ok &= pub.verify_element(hid, sig)
    if not ok:
        raise SignatureError("element signature invalid")


_default: Authority | None = None


def default_authority() -> Authority:
    """Process-wide dev authority, created lazily with a fresh in-memory key."""
    global _default
    if _default is None:
        _default = Authority()
    return _default


def sign_carrier_set(partner_id: str, hgnc_ids: Iterable[int]) -> SignedCarrierSet:
    """Module-level convenience using the default dev authority."""
    return default_authority().sign_carrier_set(partner_id, hgnc_ids)
