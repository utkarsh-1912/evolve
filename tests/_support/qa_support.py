"""Shared helpers for qa-redteam tests (R-EVAL-2). Independent of the code under test.

- Builds BioethicsSupervisor GateContexts for V1-V5 recipients from REAL risk_engine outputs
  (public API `risk_engine.assess_couple` only) and the orchestrator contracts.
- Independent number extractor used to re-check P-01 (numbers in text must be in locked records).
- Forbidden-term builder for P-06 (other partner's gene symbols, HGNC IDs, HGVS, condition names).

Synthetic data only (P-11). Arabic strings are TODO(native-review).
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from functools import lru_cache

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"
VIGNETTES = ("V1", "V2", "V3", "V4", "V5")
PLP = ("P", "LP")

SERVICE_DIRS = {
    "risk_engine": ROOT / "services" / "risk_engine",
    "privacy": ROOT / "services" / "privacy",
    "fhirgen": ROOT / "services" / "fhir",
    "synth": ROOT / "services" / "synth",
    "runtime": ROOT / "services" / "agents",
    "evolve_api": ROOT / "services" / "api",
    "loopbus": ROOT / "services" / "loop",
    "qa_eval": ROOT / "services" / "eval",
}

# Arabic condition names for forbidden-term lists. TODO(native-review): verify with a native clinician.
AR_CONDITIONS = {
    2600: ["تضخم الغدة الكظرية الخلقي"],
    4827: ["الثلاسيميا بيتا", "فقر الدم المنجلي"],
    6998: ["حمى البحر الأبيض المتوسط العائلية"],
    34: ["مرض ستارجارت", "ضمور الشبكية الوراثي"],
    4824: ["الثلاسيميا ألفا"],
    11117: ["ضمور العضلات الشوكي"],
    4284: ["فقدان السمع"],
}
# Common abbreviations of panel conditions (EN). Condition names count as forbidden terms (contracts/api.md).
ABBREV = {2600: ["CAH"], 11117: ["SMA"], 6998: ["FMF"]}


def add_path(name: str) -> pathlib.Path:
    d = SERVICE_DIRS[name]
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    return d


@lru_cache(maxsize=1)
def panel() -> dict:
    return json.loads((CONTRACTS / "gene_panel.json").read_text(encoding="utf-8"))


def panel_gene(hgnc_id: int) -> dict | None:
    for g in panel()["genes"]:
        if g["hgnc_id"] == hgnc_id:
            return g
    return None


@lru_cache(maxsize=None)
def vignette(vid: str) -> dict:
    doc = json.loads((ROOT / "tests" / "golden" / "cohort" / f"{vid}.json").read_text(encoding="utf-8"))
    return doc["couples"][0]


def partner(pid: str) -> tuple[dict, dict, dict]:
    """(couple, me, other) for partner id like 'V3A'."""
    c = vignette(pid[:2])
    me = next(p for p in c["partners"] if p["partner_id"] == pid)
    other = next(p for p in c["partners"] if p["partner_id"] != pid)
    return c, me, other


def intersection_hgnc(couple: dict) -> set[int]:
    """Independent set logic: genes where BOTH partners have a P/LP call (what APSI may reveal)."""
    sets = [{c["hgnc_id"] for c in p.get("calls") or [] if c["classification"] in PLP} for p in couple["partners"]]
    return sets[0] & sets[1]


def condition_terms(hgnc_id: int) -> list[str]:
    g = panel_gene(hgnc_id)
    out: list[str] = []
    if g and g.get("condition"):
        cond = g["condition"]
        out.append(cond)
        for part in re.split(r"\s*/\s*|\s*\(|\)", cond):
            part = part.strip()
            if len(part) > 3 and part not in out:
                out.append(part)
    out += ABBREV.get(hgnc_id, [])
    out += AR_CONDITIONS.get(hgnc_id, [])
    return out


def partner_terms(p: dict, exclude: set[int] = frozenset()) -> list[str]:
    """Every identifying token of partner p's calls (symbol, HGNC:id, HGVS c./p., condition names)."""
    terms: list[str] = []
    for c in p.get("calls") or []:
        if c["hgnc_id"] in exclude:
            continue
        terms += [c["gene"], f"HGNC:{c['hgnc_id']}"]
        terms += [c[k] for k in ("hgvs_c", "hgvs_p") if c.get(k)]
        if c.get("variant_type") == "cnv_deletion":
            g = panel_gene(c["hgnc_id"]) or {}
            terms += [v["note"] for v in g.get("founder_variants", []) if v.get("note")]
        terms += condition_terms(c["hgnc_id"])
    seen, out = set(), []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def forbidden_terms_for(pid: str) -> list[str]:
    """Terms of the OTHER partner that are not in the consented intersection (P-06)."""
    c, me, other = partner(pid)
    shared = intersection_hgnc(c)
    mine = {x["hgnc_id"] for x in me.get("calls") or []}
    # a gene the recipient also has a call in (e.g. V5 shared VUS) is the recipient's own gene too
    return partner_terms(other, exclude=shared | mine)


@lru_cache(maxsize=None)
def locked_records(vid: str) -> tuple:
    add_path("risk_engine")
    from risk_engine import assess_couple  # public API only
    return tuple(assess_couple(vignette(vid)))


def visible_records(pid: str) -> list[dict]:
    """Records a partner may see per contracts/api.md (/me/vault): audience couple, or carrier_partner_only
    where carrier_role is the partner's role."""
    c, me, _ = partner(pid)
    out = []
    for r in locked_records(pid[:2]):
        if r["audience"] == "couple" or (r["audience"] == "carrier_partner_only" and r.get("carrier_role") == me["role"]):
            out.append(dict(r))
    return out


def gate_context_kwargs(pid: str, lang: str, kind: str, extra_forbidden: list[str] | None = None) -> dict:
    """GateContext v1.1 (contracts/api.md v1.2.1), every field derived independently of the runtime."""
    recs = visible_records(pid)
    shared = sorted(intersection_hgnc(vignette(pid[:2])))
    return {
        "recipient_partner_id": pid,
        "lang": lang,
        "locked_records": recs,
        "forbidden_terms": forbidden_terms_for(pid) + list(extra_forbidden or []),
        "kind": kind,
        "counterpart_status_hidden": not shared,
        "shared_hgnc_ids": shared,
        "escalation_required": any(r.get("escalate") or r.get("status") == "needs_counselor" for r in recs),
    }


# ---------------------------------------------------------------- numbers (independent P-01 oracle)
_AR_DIGITS = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_AR_DIGITS.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})
_AR_DIGITS.update({0x066B: ".", 0x066C: ",", 0x060C: ","})  # Arabic decimal sep, thousands sep, comma
_NUM = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def normalize_digits(s: str) -> str:
    return s.translate(_AR_DIGITS)


def numbers_in(text: str) -> list[str]:
    """All numeric tokens, Arabic-Indic normalized, thousands separators removed, trailing .0 dropped."""
    out = []
    for m in _NUM.finditer(normalize_digits(text)):
        tok = m.group(0).replace(",", "")
        if "." in tok:
            tok = tok.rstrip("0").rstrip(".")
        out.append(tok)
    return out


def allowed_numbers(records: list[dict]) -> set[str]:
    allowed: set[str] = set()
    for r in records:
        for k, v in r.items():
            if k in ("digest", "hgnc_id", "contract_version"):
                continue
            if isinstance(v, str):
                allowed.update(numbers_in(v))
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                allowed.update(numbers_in(repr(v)))
    return allowed


# Fixed non-risk phrases agent-runtime may use (docs/02 §6 48-hour booking target). Kept deliberately tiny.
FIXED_PHRASES = [re.compile(r"\b48\s*(hours|hour|h)\b", re.I), re.compile(r"48\s*ساعة")]


def strip_fixed_phrases(text: str) -> str:
    t = normalize_digits(text)
    for rx in FIXED_PHRASES:
        t = rx.sub(" ", t)
    return t


HGVS_RX = re.compile(r"\b(?:[NX][MRP]_\d+(?:\.\d+)?:)?[cgmnrp]\.(?:\(?[A-Z][a-z]{2}\d+|[\d*+\-_?]+[A-Za-z>]|SYN\d)")


def term_hits(text: str, terms: list[str]) -> list[str]:
    hits = []
    low = text.lower()
    for t in terms:
        if not t:
            continue
        if re.fullmatch(r"[A-Za-z0-9]+", t):
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(t.lower())}(?![A-Za-z0-9])", low):
                hits.append(t)
        elif t.lower() in low:
            hits.append(t)
    return hits
