# 07 — Risk Math Spec (single source for `services/risk_engine`)

Notation: q = population carrier frequency of the gene (Emirati table); d = assay detection rate for the variant class/locus; R = coefficient of relationship between partners; F = offspring inbreeding coefficient.
All arithmetic uses exact `fractions.Fraction`; floats only for display. Inputs that arrive as floats are converted via `Fraction(str(x))`.

## 1. Wright (source §2.3)
Kinship of partners φ = Σ over common ancestors A and paths p of `(1/2)^(n1+n2+1) · (1 + F_A)`, where n1, n2 = meioses from each partner up to A.
- F (offspring) = φ.  R = 2φ.
- First cousins: 2 paths, n1+n2 = 4 → φ = 2·(1/2)^5 = 1/16 → **F = 1/16, R = 1/8**.
- Double first cousins: 4 paths → **F = 1/8, R = 1/4**.
- F_A > 0 scales each path term by (1+F_A).
- F is **genome-wide context** (ROH, empirical anomaly background 1.7–2.8% above 2–3% baseline for first cousins). It must never be used alone for gene-specific counseling when molecular results exist (P-03).

## 2. Bayesian residual risk (source §2.3)
Per autosomal-recessive gene, three scenarios:
1. **Concordant positive** (both carry P/LP in same gene): offspring risk = 1/4.
2. **Discordant** (A confirmed carrier, B screen-negative):
   - prior_B = R + (1 − R)·q   (R=0 ⇒ q)
   - posterior_B = prior·(1 − d) / ( prior·(1 − d) + (1 − prior) )
   - offspring risk = posterior_B / 4   (A is a confirmed carrier, transmits w.p. 1/2; B w.p. 1/2)
3. **Concordant negative** (both negative):
   - unrelated: p_X = q(1−d) / (q(1−d) + 1 − q) for each; offspring risk = p_A · p_B / 4.
   - related (R>0): **TODO(verify)** — source states the principle but the formula is not legible in the extracted text. Until the orchestrator logs a decision in `docs/DECISIONS.md`, the engine returns `status="needs_counselor"` and **no number** for this case (P-20). Do not guess.

## 3. Golden vectors (reproduced from the source; assay d values inferred from the doc's stated outputs → confirm with source authors, TODO(verify))
| Case | q | d | R | prior | posterior | "1 in" (carrier) | offspring "1 in" |
|---|---|---|---|---|---|---|---|
| V2 CYP21A2, initial | 0.106 | 0.92 | 0 | 0.106 | 0.0094 | 106.4 | 425.7 |
| V2 CYP21A2, confirmatory | 0.106 | 0.99 | 0 | 0.106 | 0.00118 | 844.4 | 3,377.6 |
| V3 SMN1, cousins | 0.013 | 0.92 | 1/8 | 0.13637 | 0.01248 | 80.2 | 320.6 |
| V3 SMN1, unrelated ref | 0.013 | 0.92 | 0 | 0.013 | 0.00105 | 950.0 | 3,800.2 |
| V1 HBB concordant | – | – | – | – | – | – | 4.0 (25%) |
Doc's published figures (1 in 106, 426, 844, 3,378, 80.2, 321, 3,800) match to rounding.

## 4. Display rules
Show both absolute ("about 1 in 321") and relative ("about 12× the 1 in 3,800 for unrelated couples") — relative values are also computed in the engine and locked. Rounding: "1 in N" to 3 significant figures; percentages to 2 decimal places or 3 s.f.; rounding done once, in `lock()`.

## 5. Locked output
`lock()` returns an immutable (frozen) object validated against `contracts/risk_output.schema.json`, with a SHA-256 digest. Every downstream message carries the digest; BioethicsSupervisor rule1 recomputes the allowed-number set from it.
