# privacy-apsi threat model (P1)

Scope: `services/privacy` (R-PRIV-1, R-PRIV-2, R-PRIV-4). Synthetic data only. This is a demo-grade
implementation of a standard construction, not an audited production cryptosystem.

## Construction (DECISIONS #5)
1. **Authority signing** (`authority.py`): the authority signs every HGNC ID of a partner's carrier
   set with RSA-2048 full-domain-hash, `sig(i) = FDH(i)^d mod n`. FDH is deterministic, so equal
   genes give equal signatures. Each set is bound to `partner_id`, a single-use `set_id`,
   `issued_at` and `expiry` by an Ed25519-signed envelope that commits (SHA-256) to the exact
   `(hgnc_id, signature)` list. The authority only certifies IDs in `contracts/gene_panel.json`.
2. **DH-commutative PSI** (`apsi.py`): RFC 3526 group 14 (2048-bit safe prime p), working in the
   prime-order quadratic-residue subgroup G (order q = (p-1)/2). `h(s) = (SHA-256-expand(s) mod p)^2`.
   Per-session secret exponents a, b (320-bit short exponents, per the RFC 3526 strength table).
   Messages: A->B `{h(s)^a}`, B->A `{h(t)^b}` and `[x^b]`, A->B `[y^a]`; each side matches
   double-blinded values. Both sides learn the same intersection; the run fails closed if they differ.
3. **Authorization gate** (`ApsiService.run`): before any group operation, require two consents that
   are schema-valid, HMAC-valid, `active`, inside their period, not revoked, distinct and mutually
   referencing; then two signed sets that verify (envelope, commitment, every element, expiry), are
   bound to the consenting partners, and have not been used before. Otherwise `refused_*`,
   `compatible: null`, and `execute_psi` is never called (spy-tested).

## Adversary model
- **Semi-honest partners** (follow the protocol, try to learn more from what they see). Main model.
- **Malicious client input** at the gate: fabricated, tampered, spliced, re-bound, expired, rogue-
  authority or replayed sets are rejected (P-09). Received protocol elements are checked to be in G
  (Jacobi symbol + range) to block small-subgroup tricks; messages are bound to a session id and a
  strict per-sender sequence, so cross-session or duplicate messages are rejected.
- **Trusted**: the authority and consent service (they hold the signing keys and the revocation
  registry), and the in-process transport between the two parties.

## What leaks
- **Set sizes**: each party learns how many certified carrier genes the other has (|A|, |B|).
- **The intersection** (to both parties and to the couple workspace) - by design, and only after
  both consents. An empty intersection yields `compatible: true` and nothing else.
- **Timing/metadata**: that a check happened, when, and its outcome (recorded in the AuditEvent log
  with opaque ids only).

## What does not leak (under DDH in G, random-oracle hashing)
- Any HGNC ID, signature or hash of a non-shared gene: the other side sees only `h(s)^a`, which is
  pseudorandom without `a`. Blinding is fresh per session, so runs are unlinkable.
- Probing: a partner cannot test genes it is not certified for, because it cannot compute an FDH
  signature without the authority key, and every set is bound to the consenting partner.
- Logs and audit events carry no gene symbols, HGNC IDs or variant strings (P-12, tested).

## Not covered / residual items
- **Malicious parties inside the protocol** (e.g., a party sending a different set than the one it
  was certified for in step 1, or aborting after learning the result first) are out of model; the
  in-process demo has both parties driven by `execute_psi`. A deployed version needs authenticated
  channels and a zero-knowledge proof (or server-assisted mode) that blinded values derive from the
  certified set.
- **Set-size hiding** (padding to a fixed size) is not implemented.
- **Bloom filter variant** is not implemented (optional per DECISIONS #5). Matching is exact on
  double-blinded group elements, and every released positive is re-checked to be a member of both
  verified signed sets, so there are no Bloom false positives to bound.
- **Side channels**: Python big-int `pow` is not constant time. Signature, MAC and hash-chain
  comparisons use `hmac.compare_digest`.
- **Keys** are generated in memory per process and never persisted; restart = new keys (all prior
  signed sets, consents and cascade tokens become unverifiable). Production key custody (HSM) is out
  of scope.
- **Small-cell suppression** is primary suppression only (cells < k=10 hidden); complementary
  suppression against back-calculation from totals is the caller's job.
- **Cascade token** digest is SHA-256 of a normalized variant, not a GA4GH VRS digest
  (TODO(verify) with orchestrator if VRS is required).
