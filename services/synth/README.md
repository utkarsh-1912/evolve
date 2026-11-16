# services/synth — synthetic cohort + vignettes (data-synth)

Reqs: R-DATA-1, R-DATA-2, R-DATA-3. **Synthetic data only. No risk outputs are computed here (P-02).**

```
cd services/synth
python -m synth --seed 42 --n 1000 --out ../../services/synth/out/cohort.json --vignettes-dir ../../tests/golden/cohort
python -m pytest -q
```
Outputs: `out/cohort.json` (cohort.schema.json 1.0.0), `out/cohort_report.json`, `tests/golden/cohort/V1..V5.json`.
API: `synth.generate_cohort(seed, n=1000) -> dict`, `synth.build_vignettes()`, `synth.build_report(doc)`, `synth.dumps(doc)` (canonical bytes).

## Model
- **Genes sampled**: the 8 panel genes with non-null `carrier_freq` (source §2.1). TPO, CYP1B1, GJB2 have no frequency → vignettes only (gene_panel.rules).
- **Carrier state**: per partner, per gene Bernoulli(carrier_freq) → one het P/LP call.
- **IBD for related couples**: with probability R (unrelated 0, second cousins 1/32, first cousins 1/8, double first cousins 1/4) partner B's state at that locus is copied from A (same allele and flags); otherwise an independent population draw. This preserves each partner's marginal carrier rate and gives P(B carrier | A carrier) = R + (1−R)·q, consistent with docs/07 §2.
- **Allele choice**: founder variant weight = af / (carrier_freq/2); remainder to founder variants with af=null (CYP21A2 c.844G>T, SMN1 exon-7 deletion) or else to 3 synthetic alleles `c.SYN<hgnc><k>A>G` (HBA2 synthetic alleles are `cnv_deletion`, source §2.1 "requires CNV/deletion calling"). Founder calls are P; synthetic calls P (80%) / LP (20%, TODO(verify), not in source).
- **Novelty gap (R-DATA-3)**: documented founder variants are never flagged novel (DECISIONS #12). Synthetic non-founder calls get independent Bernoulli flags (absent_gnomad 0.52, absent_clinvar 0.30). Overall realized rates are reported, not forced.
- **Assays**: every partner has `initial` for the 8 sampled genes; in discordant CYP21A2 couples the negative partner gets `confirmatory` with probability 0.30.
- **Demographics**: sex A random, B opposite; age uniform 18–45; BMI uniform 19–40 (1 dp).
- **Relationship mix**: unrelated 50%, first cousins 33%, double first cousins 7%, second cousins 10% (source-realistic, DECISIONS #10). The 8-gene couple concordance (~4–5% expected) is reported with a CI as a floor. The 4.8–13.1% band (570 genes) is not targeted.
- **Determinism**: `random.Random(seed)`; `dumps()` is canonical; same seed ⇒ identical bytes (tested).

## Vignettes
Hand-authored per source §2.4; `expected` blocks copy numbers from docs/07 §3 / tests/golden/risk_vectors.json (tested for equality, never computed). V5 HPO `HP:0001522` is TODO(verify).
