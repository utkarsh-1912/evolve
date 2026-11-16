"""Read-only access to contracts/gene_panel.json (orchestrator-owned contract)."""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache

ROOT = pathlib.Path(__file__).resolve().parents[3]
PANEL_PATH = ROOT / "contracts" / "gene_panel.json"
COHORT_SCHEMA_PATH = ROOT / "contracts" / "cohort.schema.json"


@lru_cache(maxsize=1)
def panel_by_hgnc() -> dict[int, dict]:
    data = json.loads(PANEL_PATH.read_text(encoding="utf-8"))
    return {g["hgnc_id"]: g for g in data["genes"]}


def gene_info(hgnc_id: int, fallback_symbol: str) -> dict:
    """Panel entry for an HGNC ID. Unknown IDs get no condition text and are never complex loci."""
    g = panel_by_hgnc().get(hgnc_id)
    if g is None:
        return {"symbol": fallback_symbol, "hgnc_id": hgnc_id, "condition": None, "complex_locus": False}
    return g


@lru_cache(maxsize=1)
def cohort_schema() -> dict:
    return json.loads(COHORT_SCHEMA_PATH.read_text(encoding="utf-8"))


def is_synthetic_hgvs(hgvs: str | None) -> bool:
    """Made-up variants from data-synth carry 'SYN' (e.g. c.SYN123A>G); they are never emitted as HGVS."""
    return bool(hgvs) and "SYN" in hgvs


def coding_transcript(call: dict) -> str | None:
    """Transcript accession for a call's c.HGVS (DECISIONS #39).

    1. call.refseq if it is an NM_/NR_ transcript;
    2. else the panel `refseq_transcript` (MANE Select, TODO(verify) unless refseq_verified_from_source),
       but only when the call's c.HGVS is a panel founder variant;
    3. else None (no HGVS is emitted - no accession is ever invented).
    """
    hgvs_c = call.get("hgvs_c")
    if not hgvs_c or is_synthetic_hgvs(hgvs_c):
        return None
    refseq = call.get("refseq")
    if refseq and refseq.startswith(("NM_", "NR_")):
        return refseq
    g = panel_by_hgnc().get(call["hgnc_id"])
    if g and g.get("refseq_transcript") and any(f.get("hgvs_c") == hgvs_c for f in g.get("founder_variants", [])):
        return g["refseq_transcript"]
    return None
