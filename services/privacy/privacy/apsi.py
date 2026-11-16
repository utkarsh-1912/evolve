"""Authorized Private Set Intersection (R-PRIV-1, guardrails P-06, P-07, P-09; DECISIONS #5).

Protocol (two semi-honest parties A and B, in-process, explicit message objects):

  Setup   Group G = quadratic-residue subgroup (prime order q = (p-1)/2) of the RFC 3526 group 14
          2048-bit MODP prime p. Hash-to-group: h(s) = (SHA-256-expand(s) mod p)^2 mod p, where s is
          the authority's RSA-FDH signature on an HGNC ID (privacy.authority). Each party draws a
          fresh secret exponent (a or b) per session.
  1. A -> B  blinded_set  X_A = shuffle{ h(s)^a }
  2. B -> A  blinded_set  X_B = shuffle{ h(t)^b }
  3. B -> A  reblinded    Z_A = [ x^b for x in X_A ]      (same order as X_A)
  4. A -> B  reblinded    Z_B = [ y^a for y in X_B ]      (same order as X_B)
  A: element i of its set is shared iff Z_A[i] in Z_B.   B: element j shared iff Z_B[j] in Z_A.

Both parties learn the intersection and the other's set size, nothing else (see THREAT_MODEL.md).
Every received element is checked to be in G (range + Jacobi symbol), every message is bound to a
session id and a strict per-sender sequence, so replayed or cross-session messages are rejected.

``run()`` authorizes first (two valid mutually-referencing consents, two authority-verified,
unexpired, unused signed sets bound to the consenting partners) and only then calls
``execute_psi``. On refusal nothing is computed and ``compatible`` is ``null``.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import threading
from dataclasses import dataclass, field

import jsonschema

from ._common import CONTRACT_VERSION, Clock, utcnow
from .audit import AuditLog, default_audit_log
from .authority import AuthorityPublicKey, SignatureError, SignedCarrierSet, default_authority, verify_signed_set
from .consent import APSI_SCHEMA, ConsentService, default_consent_service

log = logging.getLogger("privacy.apsi")

# RFC 3526 section 3, 2048-bit MODP group (id 14). Safe prime: q = (p - 1) / 2 is prime.
P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74"
    "020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F1437"
    "4FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF05"
    "98DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB"
    "9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
    "3995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF", 16)
Q = (P - 1) // 2
P_BYTES = 256
# Short exponents (RFC 3526 table: 320 bits for the 2048-bit group) keep 2048-bit modexp cheap.
EXPONENT_BITS = 320
H2G_DOMAIN = b"IDR-APSI-H2G-v1|"


class ProtocolError(Exception):
    """Malformed, out-of-order or out-of-group message."""


class ReplayError(ProtocolError):
    """Message from another session, or a message already processed in this session."""


def hash_to_group(signature: int, modulus_len: int = P_BYTES) -> int:
    """Map an authority signature into G: square of a uniform-ish element of Z_p^*."""
    msg = H2G_DOMAIN + signature.to_bytes(max(modulus_len, (signature.bit_length() + 7) // 8), "big")
    k = P_BYTES + 16
    out = b"".join(hashlib.sha256(c.to_bytes(4, "big") + msg).digest() for c in range(-(-k // 32)))
    x = int.from_bytes(out[:k], "big") % P
    if x in (0, 1, P - 1):  # negligible; avoid trivial elements
        x = 2
    return pow(x, 2, P)


def _jacobi(a: int, n: int) -> int:
    a %= n
    result = 1
    while a:
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            result = -result
        a %= n
    return result if n == 1 else 0


def in_group(x: int) -> bool:
    """x in the order-q subgroup G (for a safe prime p, G = quadratic residues; Jacobi == Legendre)."""
    return isinstance(x, int) and 1 < x < P - 1 and _jacobi(x, P) == 1


@dataclass(frozen=True)
class Message:
    session_id: str
    seq: int
    sender: str
    recipient: str
    kind: str  # "blinded_set" | "reblinded"
    payload: tuple[int, ...]


class PsiParty:
    """One side of the DH-commutative PSI. Holds its own (hgnc_id, signature) pairs privately."""

    _EXPECTED = ("blinded_set", "reblinded")

    def __init__(self, name: str, peer: str, elements, session_id: str, *, initiator: bool):
        self.name, self.peer, self.session_id, self.initiator = name, peer, session_id, initiator
        self._k = secrets.randbits(EXPONENT_BITS) | (1 << (EXPONENT_BITS - 1))  # secret exponent
        hashed = [(hid, hash_to_group(sig)) for hid, sig in elements]
        secrets.SystemRandom().shuffle(hashed)
        self._ids = [hid for hid, _ in hashed]
        self._mine_blinded = tuple(pow(h, self._k, P) for _, h in hashed)
        self._sent = 0
        self._next_in = 0
        self._peer_blinded: tuple[int, ...] | None = None
        self._mine_double: tuple[int, ...] | None = None    # my elements, blinded by both (Z_mine)
        self._peer_double: tuple[int, ...] | None = None    # peer elements, blinded by both
        self.result: frozenset[int] | None = None

    def _msg(self, kind: str, payload) -> Message:
        m = Message(self.session_id, self._sent, self.name, self.peer, kind, tuple(payload))
        self._sent += 1
        return m

    def start(self) -> list[Message]:
        if not self.initiator or self._sent:
            raise ProtocolError("only the initiator starts, once")
        return [self._msg("blinded_set", self._mine_blinded)]

    def receive(self, m: Message) -> list[Message]:
        if m.session_id != self.session_id:
            raise ReplayError("message from a different session")
        if m.sender != self.peer or m.recipient != self.name:
            raise ProtocolError("misaddressed message")
        if m.seq != self._next_in:
            raise ReplayError("out-of-sequence or replayed message")
        if self._next_in >= len(self._EXPECTED) or m.kind != self._EXPECTED[self._next_in]:
            raise ProtocolError("unexpected message kind")
        if not all(in_group(x) for x in m.payload):
            raise ProtocolError("element outside the prime-order subgroup")
        self._next_in += 1
        out: list[Message] = []
        if m.kind == "blinded_set":
            self._peer_blinded = m.payload
            self._peer_double = tuple(pow(y, self._k, P) for y in m.payload)
            if not self.initiator:
                out.append(self._msg("blinded_set", self._mine_blinded))
            out.append(self._msg("reblinded", self._peer_double))
        else:  # reblinded: my own elements, now carrying both exponents
            if len(m.payload) != len(self._mine_blinded):
                raise ProtocolError("reblinded set size mismatch")
            self._mine_double = m.payload
        if self._mine_double is not None and self._peer_double is not None:
            peer = set(self._peer_double)
            self.result = frozenset(hid for hid, z in zip(self._ids, self._mine_double) if z in peer)
        return out


@dataclass
class PsiOutcome:
    shared: frozenset[int]
    transcript: list[Message] = field(default_factory=list)

    def received_by(self, name: str) -> list[Message]:
        return [m for m in self.transcript if m.recipient == name]


def execute_psi(set_a: SignedCarrierSet, set_b: SignedCarrierSet) -> PsiOutcome:
    """Run the two in-process parties to completion, delivering messages in order."""
    sid = secrets.token_hex(16)
    a = PsiParty("A", "B", set_a.elements, sid, initiator=True)
    b = PsiParty("B", "A", set_b.elements, sid, initiator=False)
    parties = {"A": a, "B": b}
    transcript: list[Message] = []
    queue = a.start()
    while queue:
        m = queue.pop(0)
        transcript.append(m)
        queue.extend(parties[m.recipient].receive(m))
    if a.result is None or b.result is None or a.result != b.result:
        raise ProtocolError("parties did not reach the same intersection")  # fail closed
    return PsiOutcome(shared=a.result, transcript=transcript)


class ApsiService:
    def __init__(self, *, authority: AuthorityPublicKey | None = None, consents: ConsentService | None = None,
                 audit: AuditLog | None = None, clock: Clock = utcnow):
        self.authority = authority or default_authority().public_key
        self.consents = consents if consents is not None else default_consent_service()
        self.audit = audit if audit is not None else default_audit_log()
        self.clock = clock
        self._used_sets: set[str] = set()
        self._lock = threading.Lock()

    def _result(self, status: str, compatible, shared, consent_ids, reason: str | None) -> dict:
        detail = {"status": status} | ({"reason": reason} if reason else {})
        event_id = self.audit.append("apsi.run", "success" if status == "ok" else "refused",
                                     entity=list(consent_ids), detail=detail)
        res = {
            "contract_version": CONTRACT_VERSION,
            "status": status,
            "compatible": compatible,
            "shared_hgnc_ids": sorted(shared),
            "consent_ids": list(consent_ids),
            "audit_event_id": event_id,
        }
        jsonschema.validate(res, APSI_SCHEMA)
        return res

    def run(self, consent_a: dict | None, consent_b: dict | None,
            signed_a: SignedCarrierSet | None, signed_b: SignedCarrierSet | None) -> dict:
        now = self.clock()
        ids = [c["id"] for c in (consent_a, consent_b) if isinstance(c, dict) and isinstance(c.get("id"), str)][:2]

        reason = self.consents.check_pair(consent_a, consent_b, now)
        if reason:
            log.info("apsi refused: consent (%s)", reason)
            return self._result("refused_no_consent", None, [], ids, reason)

        try:
            if not isinstance(signed_a, SignedCarrierSet) or not isinstance(signed_b, SignedCarrierSet):
                raise SignatureError("missing signed set")
            for s in (signed_a, signed_b):
                verify_signed_set(self.authority, s, now=now)
            if signed_a.partner_id != consent_a["patient"] or signed_b.partner_id != consent_b["patient"]:
                raise SignatureError("signed set not bound to the consenting partner")
            with self._lock:
                if signed_a.set_id == signed_b.set_id or {signed_a.set_id, signed_b.set_id} & self._used_sets:
                    raise SignatureError("signed set already used (replay)")
                self._used_sets.update({signed_a.set_id, signed_b.set_id})
        except SignatureError as exc:
            log.info("apsi refused: authorization (%s)", type(exc).__name__)
            return self._result("refused_invalid_signature", None, [], ids, "authorization_failed")

        try:
            outcome = execute_psi(signed_a, signed_b)
        except Exception:
            self.audit.append("apsi.run", "error", entity=ids)
            raise
        shared = outcome.shared
        # A positive is released only if it is an exact, verified member of BOTH signed sets.
        if not shared <= (signed_a.hgnc_ids & signed_b.hgnc_ids):
            self.audit.append("apsi.run", "error", entity=ids)
            raise ProtocolError("intersection not contained in both verified sets")
        return self._result("ok", len(shared) == 0, shared, ids, None)


_default: ApsiService | None = None


def default_service() -> ApsiService:
    global _default
    if _default is None:
        _default = ApsiService()
    return _default


def run(consent_a, consent_b, signed_a, signed_b) -> dict:
    """Contract entry point (docs/08): returns a dict valid against apsi_result.schema.json."""
    return default_service().run(consent_a, consent_b, signed_a, signed_b)
