"""Gene-panel lookup (q = carrier frequency, d = assay detection rate) from contracts/gene_panel.json.

R-RISK-2. The only file in the engine that does I/O; it reads the orchestrator-owned contract and
returns exact Fractions. No clinical numbers are hard-coded here: a null in the contract stays None,
and callers must then return status "needs_counselor" with no number (gene_panel.rules).
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from types import MappingProxyType
from typing import Mapping, Optional, Union

DEFAULT_PANEL_PATH = pathlib.Path(__file__).resolve().parents[3] / "contracts" / "gene_panel.json"
SUPPORTED_CONTRACT = "1.0.0"
ASSAY_STAGES = ("initial", "confirmatory")


def _opt_fr(x) -> Optional[Fraction]:
    if x is None:
        return None
    if isinstance(x, bool) or not isinstance(x, (int, float, str)):
        raise ValueError(f"panel value must be a number or null, got {x!r}")
    v = Fraction(str(x))  # str() so 0.106 means exactly 106/1000
    if not (0 <= v <= 1):
        raise ValueError(f"panel probability must be in [0,1], got {x!r}")
    return v


@dataclass(frozen=True)
class GeneInfo:
    symbol: str
    hgnc_id: int
    carrier_freq: Optional[Fraction]
    complex_locus: bool
    detection: Mapping[str, Optional[Fraction]]  # assay stage -> d (None = not curated)


@dataclass(frozen=True)
class Panel:
    contract_version: str
    genes: Mapping[int, GeneInfo]

    def gene(self, hgnc_id: int) -> Optional[GeneInfo]:
        return self.genes.get(hgnc_id)

    def carrier_freq(self, hgnc_id: int) -> Optional[Fraction]:
        g = self.gene(hgnc_id)
        return None if g is None else g.carrier_freq

    def detection_rate(self, hgnc_id: int, stage: Optional[str]) -> Optional[Fraction]:
        """d for (gene, assay stage). Unknown gene, unknown/missing stage or null in the contract -> None."""
        g = self.gene(hgnc_id)
        if g is None or stage not in ASSAY_STAGES:
            return None
        return g.detection.get(stage)


def panel_from_dict(doc: dict) -> Panel:
    if doc.get("contract_version") != SUPPORTED_CONTRACT:
        raise ValueError(f"unsupported gene_panel contract_version {doc.get('contract_version')!r}")
    genes: dict[int, GeneInfo] = {}
    for g in doc["genes"]:
        hid = g["hgnc_id"]
        if hid in genes:
            raise ValueError(f"duplicate hgnc_id {hid} in gene panel")
        det = {stage: _opt_fr(v) for stage, v in (g.get("detection") or {}).items() if stage in ASSAY_STAGES}
        genes[hid] = GeneInfo(
            symbol=g["symbol"],
            hgnc_id=hid,
            carrier_freq=_opt_fr(g.get("carrier_freq")),
            complex_locus=bool(g.get("complex_locus", False)),
            detection=MappingProxyType(det),
        )
    return Panel(contract_version=doc["contract_version"], genes=MappingProxyType(genes))


@lru_cache(maxsize=8)
def _load_cached(path: str) -> Panel:
    return panel_from_dict(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))


def load_panel(path: Union[str, pathlib.Path, None] = None) -> Panel:
    """Load (and cache) the gene panel contract. Returns an immutable Panel."""
    return _load_cached(str(pathlib.Path(path) if path is not None else DEFAULT_PANEL_PATH))
