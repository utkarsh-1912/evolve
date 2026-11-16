"""BioethicsSupervisor outbound gate (R-AGT-2; docs/01 P-01, P-06, P-13, P-14, P-16, P-17).

Contract interface (contracts/api.md):
    check(draft: str, ctx: GateContext) -> GateResult
    GateResult = {passed: bool, violations: [{rule, detail}]}
    rule in numeric_drift | leakage | directive | uae_law | missing_judicial_statement | stigma

Deterministic, stdlib only, no network. Any internal error is a FAIL (fail closed): the result carries a
single violation with rule "gate_error" (see handoffs/QUESTION-AR-1.md).

The gate never does arithmetic on probabilities (P-02). It only checks that every number in a draft is
*equal* to a value or display string already present in the locked RiskOutput records the recipient may
see. Percent tokens are compared by shifting the decimal point (Decimal.scaleb), never by computation.

Violation details never echo a forbidden term (the detail text itself could leak it, P-06/P-12).

Arabic phrase lists are first drafts: TODO(ar) native review (Gulf/MSA).
"""
from __future__ import annotations

import json
import pathlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

RULES = ("numeric_drift", "leakage", "directive", "uae_law", "missing_judicial_statement", "stigma",
         "false_reassurance")
GATE_ERROR = "gate_error"
FETAL_ROUTE = "fetal_anomaly_route"  # prefix of uae_law details that must route to MFM + counselor

_PANEL_PATH = pathlib.Path(__file__).resolve().parents[3] / "contracts" / "gene_panel.json"


# --------------------------------------------------------------------------------------------- types
@dataclass
class GateContext:
    recipient_partner_id: str
    lang: str = "en"
    locked_records: list = field(default_factory=list)
    forbidden_terms: list = field(default_factory=list)
    kind: str = "result"  # result | explainer | care | escalation; default is the strictest
    # contract v1.1.0 (DECISIONS #23-24). None = derive from locked_records (fail-safe defaults):
    counterpart_status_hidden: Optional[bool] = None  # derived: True unless a couple-audience record is visible
    shared_hgnc_ids: Optional[list] = None            # derived: hgnc_ids of visible couple-audience records
    escalation_required: Optional[bool] = None        # derived: any visible record escalates / needs_counselor

    FIELDS = ("recipient_partner_id", "lang", "locked_records", "forbidden_terms", "kind",
              "counterpart_status_hidden", "shared_hgnc_ids", "escalation_required")

    @classmethod
    def coerce(cls, ctx: Any) -> "GateContext":
        if isinstance(ctx, GateContext):
            return ctx
        if isinstance(ctx, dict):
            return cls(**{k: ctx[k] for k in cls.FIELDS if k in ctx})
        raise TypeError("ctx must be a GateContext or dict")

    def resolved(self) -> tuple[bool, set, bool]:
        recs = [r for r in self.locked_records or [] if isinstance(r, dict)]
        shared = set(self.shared_hgnc_ids) if self.shared_hgnc_ids is not None else {
            r.get("hgnc_id") for r in recs if r.get("audience") == "couple"}
        hidden = self.counterpart_status_hidden if self.counterpart_status_hidden is not None else not shared
        esc = self.escalation_required if self.escalation_required is not None else any(
            r.get("escalate") or r.get("status") == "needs_counselor" for r in recs)
        return bool(hidden), shared, bool(esc)


@dataclass
class GateResult:
    passed: bool
    violations: list = field(default_factory=list)

    def __getitem__(self, key: str):  # dict-style access, matching the contract shape
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    @property
    def rules(self) -> list[str]:
        return sorted({v["rule"] for v in self.violations})

    @property
    def fetal_route(self) -> bool:
        return any(v["rule"] == "uae_law" and v["detail"].startswith(FETAL_ROUTE) for v in self.violations)

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------------------------- normalization
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍‎‏⁠⁦⁧⁨⁩؜﻿­ـ"))
_SEPARATORS = str.maketrans({"٫": ".", "٬": ",", "٪": "%", "،": ",", " ": " ",
                             " ": " ", " ": " ", "−": "-", "‐": "-", "‑": "-"})
_HOMOGLYPHS = str.maketrans("АВСЕНКМОРТХаеорсухіІ", "ABCEHKMOPTXaeopcyxiI")


def normalize(text: str) -> str:
    """NFKC, strip zero-width/tatweel, map every Unicode decimal digit (Arabic-Indic, Persian, ...) to ASCII,
    map Arabic decimal/thousands/percent signs and common Cyrillic homoglyphs."""
    t = unicodedata.normalize("NFKC", str(text)).translate(_ZERO_WIDTH).translate(_SEPARATORS)
    t = "".join(str(unicodedata.decimal(c)) if c.isdecimal() and not c.isascii() else c for c in t)
    return t.translate(_HOMOGLYPHS)


def _dec(s: str) -> Decimal | None:
    try:
        return Decimal(s.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


# ------------------------------------------------------------------------------------ numeric drift
_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_NUM_RX = re.compile(rf"(?<![A-Za-z؀-ۿ\d.,:_/\-+])(?:{_NUM})")
_LOOSE_NUM_RX = re.compile(rf"(?<![A-Za-z؀-ۿ\d.,_])(?:{_NUM})")

# Integers inside fixed, non-risk phrases (task card: explicit small allowlist).
FIXED_PHRASES = [
    re.compile(r"\b48[\s-]*(?:hours?|hrs?|h)\b", re.I),
    re.compile(r"48\s*(?:ساعة|ساعه)"),
    re.compile(r"\bstep\s+[1-7]\b", re.I),
    re.compile(r"الخطوة\s+[1-7]"),
]

_EN_UNITS = {"zero": 0, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
             "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
             "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
             "one": 1, "dozen": 12, "twice": 2, "triple": 3, "thrice": 3}
_EN_SCALES = {"hundred": 100, "thousand": 1000, "million": 1000000}
_EN_WORD = "|".join(sorted(list(_EN_UNITS) + list(_EN_SCALES), key=len, reverse=True))
_EN_WORDSEQ_RX = re.compile(rf"\b(?:{_EN_WORD})(?:[\s-]+(?:and[\s-]+)?(?:{_EN_WORD}))*\b", re.I)

# "1 in N", "one in N", "a 1-in-N", "1 out of N", "1:N", "1/N", Arabic "1 من كل N" / "واحد من كل N"
_ONE = r"(?:1|one|a|single|واحد|واحدة)"
_ONE_IN_RX = re.compile(
    rf"(?<![\w.,]){_ONE}[\s-]*(?:in|out\s+of|of\s+every|from\s+every|من\s+(?:كل|بين)|من|في|:|/)[\s-]*"
    rf"((?:{_NUM})|(?:(?:{_EN_WORD})(?:[\s-]+(?:and[\s-]+)?(?:{_EN_WORD}))*))(?![\w])", re.I)
_FRACTION_RX = re.compile(rf"(?<![\w.,/])(\d+)\s*/\s*(\d+)(?![\w/])")
_PERCENT_RX = re.compile(
    rf"(?<![A-Za-z؀-ۿ\d.,_])({_NUM})\s*(?:%|percent\b|per\s+cent\b|pct\b|بالمئة|بالمائة|في\s+المئة|في\s+المائة)",
    re.I)
_EN_FRACTION_WORDS = re.compile(r"\b(?:a|one)?[\s-]*(quarter|half)\b", re.I)
_AR_FRACTION_WORDS = {"ربع": Decimal(4), "نصف": Decimal(2)}

# P4 (BUG-QA-13/15): number words count when they are used as a quantity or chance. People-counting idioms and
# non-quantity uses of "half" are not numbers ("the two of you", "your other half", "half an hour").
_NUM_IDIOMS = re.compile(
    r"\b(?:the\s+)?(?:two|both|three)\s+of\s+(?:you|us|them|your\s+families)\b|\b(?:you|we|us)\s+two\b|\bother\s+half\b|"
    r"\bhalf[-\s](?:brothers?|sisters?|siblings?)\b|\bhalf\s+(?:an?\s+)?hour\b|\bone\s+(?:or|and)\s+(?:the\s+)?other\b|\bone\s+another\b",
    re.I)
# Implied "1 in 2" idioms (EN/Arabizi) and fractions other than half/quarter, only in a chance/quantity frame.
_EN_EVEN_ODDS = re.compile(r"\bfifty[\s-]+fifty\b|\bcoin[\s-]+(?:toss|flip)\b|\btoss[\s-]+up\b|\beven\s+odds\b|\bevens\b", re.I)
_EN_ORD_FRACTION = re.compile(
    r"\b(?:a|one)[\s-]+(third|fifth|sixth|eighth|tenth)\b(?!\s+(?:part(?:y|ies)|option|person|people|time|step|trimester|"
    r"week|month|year|child|pregnancy|visit|appointment|round|cycle|opinion))|\b(?:two|three|four|five|six|seven|nine)[\s-]+"
    r"(?:thirds|fifths|sixths|eighths|tenths|quarters)\b", re.I)
_ORD_DEN = {"third": 3, "fifth": 5, "sixth": 6, "eighth": 8, "tenth": 10}
# Gulf/Levantine "nuss" (half) and "thulth" (third) are ambiguous ("nass" also means "text"), so they count as a
# chance only with a chance word in the same clause. TODO(ar) native review.
_AR_CHANCE_WORDS = re.compile(r"احتمال\w*|الاحتمال\w*|نسب\w*|النسب\w*|فرص\w*|الفرص\w*|خطر|الخطر|خطور\w*|"
                              r"\b(?:chance|e?7timal\w*|i?h?timal\w*|nesba|nisba|fursa|forsa)\b", re.I)
_AR_DIALECT_FRAC = re.compile(r"(?<![ء-ي])(?:و|ب|ال|بال)?(نص|نُص|ثلث|خمس|عشر)(?![ء-ي])|"
                              r"\b(?:nuss|nus|noss|nos|ness)\b|\b(?:rub3|rob3|rubu3)\b|\b(?:thilth|tholth|thulth|tilt)\b", re.I)
_AR_DIALECT_DEN = {"نص": 2, "نُص": 2, "ثلث": 3, "خمس": 5, "عشر": 10, "nuss": 2, "nus": 2, "noss": 2, "nos": 2, "ness": 2,
                   "rub3": 4, "rob3": 4, "rubu3": 4, "thilth": 3, "tholth": 3, "thulth": 3, "tilt": 3}
_AR_EVEN_ODDS = re.compile(r"فيفتي\s*فيفتي|خمسين\s*(?:ب|في)?\s*(?:ال)?خمسين|نص\s*(?:ب|في)?\s*(?:ال)?نص|\bfifty\s*fifty\b", re.I)
_AR_NUMBER_WORDS = {  # TODO(ar) native review; compound numerals are not parsed (fail closed)
    "اثنان": 2, "اثنين": 2, "ثلاثة": 3, "ثلاث": 3, "أربعة": 4, "أربع": 4, "خمسة": 5, "خمس": 5, "ستة": 6,
    "سبعة": 7, "سبع": 7, "ثمانية": 8, "ثماني": 8, "تسعة": 9, "تسع": 9, "عشرة": 10, "عشر": 10,
    "عشرين": 20, "عشرون": 20, "ثلاثين": 30, "ثلاثون": 30, "أربعين": 40, "أربعون": 40, "خمسين": 50,
    "خمسون": 50, "ستين": 60, "ستون": 60, "سبعين": 70, "سبعون": 70, "ثمانين": 80, "ثمانون": 80,
    "تسعين": 90, "تسعون": 90, "مئة": 100, "مائة": 100, "ألف": 1000, "آلاف": 1000,
}
_AR_WORD_RX = re.compile(
    r"(?<![ء-ي])(?:و|ب|ل|ف)?(" + "|".join(sorted(_AR_NUMBER_WORDS, key=len, reverse=True)) + r")(?![ء-ي])")
_AR_FRAC_RX = re.compile(r"(?<![ء-ي])(?:و|ب|ال)?(ربع|نصف)(?![ء-ي])")

# Absolute reassurance is an implied number (0) that no locked record carries (P-04).
_ZERO_CLAIMS = re.compile(
    r"\b(?:no|zero|nil)\s+(?:risk|chance|possibility)\b|\brisk[-\s]free\b|\bnothing\s+to\s+worry\b|"
    r"\b(?:100|hundred)\s*(?:%|percent)\s+(?:safe|sure|certain|healthy)\b|\bcompletely\s+safe\b|"
    r"\b(?:definitely|certainly)\s+not\s+a\s+carrier\b|\ball[-\s]clear\b|"
    r"لا\s+يوجد\s+(?:أي\s+)?(?:خطر|احتمال)|بدون\s+(?:أي\s+)?خطر|لا\s+خطر", re.I)

_SKIP_KEYS = {"digest", "contract_version", "gene", "fusage", "audience", "carrier_role", "reason",
              "scenario", "status"}


def _parse_en_words(seq: str) -> Decimal | None:
    total, current, seen = 0, 0, False
    for w in re.split(r"[\s-]+", seq.lower()):
        if not w or w == "and":
            continue
        if w in _EN_UNITS:
            current += _EN_UNITS[w]
            seen = True
        elif w in _EN_SCALES:
            current = max(current, 1) * _EN_SCALES[w]
            if _EN_SCALES[w] >= 1000:
                total, current = total + current, 0
            seen = True
        else:
            return None
    return Decimal(total + current) if seen else None


def _num_token(tok: str) -> Decimal | None:
    tok = tok.strip()
    if re.fullmatch(_NUM, tok):
        return _dec(tok)
    return _parse_en_words(tok)


def _locked_sets(records: Iterable[dict]) -> tuple[set, set, set]:
    """(numeric values, numbers appearing in display strings, N of every '1 in N' display)."""
    values: set[Decimal] = set()
    display: set[Decimal] = set()
    one_in: set[Decimal] = set()

    def walk(obj, key=None):
        if key in _SKIP_KEYS:
            return
        if isinstance(obj, bool) or obj is None:
            return
        if isinstance(obj, (int, float)):
            d = _dec(repr(obj))
            if d is not None:
                values.add(d)
        elif isinstance(obj, str):
            s = normalize(obj)
            for m in re.finditer(rf"\b1\s+in\s+({_NUM})", s):
                d = _dec(m.group(1))
                if d is not None:
                    one_in.add(d)
            for m in _LOOSE_NUM_RX.finditer(s):
                d = _dec(m.group(0))
                if d is not None:
                    display.add(d)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, k)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                walk(v, key)

    for r in records or []:
        walk(r)
    return values, display, one_in


def _check_numbers(text: str, records: list[dict]) -> list[dict]:
    values, display, one_in = _locked_sets(records)
    plain_ok = values | display
    out: list[dict] = []
    t = text
    for rx in FIXED_PHRASES:
        t = rx.sub(" ", t)
    t = _NUM_IDIOMS.sub(" ", t)

    def _need_one_in(n: Decimal, what: str) -> None:
        if n not in one_in:
            out.append({"rule": "numeric_drift", "detail": f"{what} is not a locked value"})

    for m in list(_EN_EVEN_ODDS.finditer(t)) + list(_AR_EVEN_ODDS.finditer(t)):
        _need_one_in(Decimal(2), "even-odds idiom (implied 1 in 2)")
    t = _AR_EVEN_ODDS.sub(" ", _EN_EVEN_ODDS.sub(" ", t))

    def sub_ord_fraction(m: re.Match) -> str:
        if m.group(1):
            _need_one_in(Decimal(_ORD_DEN[m.group(1).lower()]), f"fraction word '{m.group(1)}'")
        else:
            out.append({"rule": "numeric_drift", "detail": "multi-part fraction word is not a locked value"})
        return " "
    t = _EN_ORD_FRACTION.sub(sub_ord_fraction, t)

    kept = []
    for c in re.split(r"([.!?؟;\n،,:])", t):
        if _AR_CHANCE_WORDS.search(c):
            for m in _AR_DIALECT_FRAC.finditer(c):
                w = (m.group(1) or m.group(0)).lower()
                _need_one_in(Decimal(_AR_DIALECT_DEN.get(w, 0)), "dialect fraction word used as a chance")
            c = _AR_DIALECT_FRAC.sub(" ", c)
        kept.append(c)
    t = "".join(kept)

    for m in _ZERO_CLAIMS.finditer(t):
        out.append({"rule": "numeric_drift", "detail": "absolute reassurance (implied zero) is not a locked value"})
    t = _ZERO_CLAIMS.sub(" ", t)

    def sub_one_in(m: re.Match) -> str:
        n = _num_token(m.group(1))
        if n is None or n not in one_in:
            out.append({"rule": "numeric_drift", "detail": f"'1 in {m.group(1).strip()}' is not a locked value"})
        return " "
    t = _ONE_IN_RX.sub(sub_one_in, t)

    def sub_fraction(m: re.Match) -> str:
        num, den = _dec(m.group(1)), _dec(m.group(2))
        if num != 1 or den not in one_in:
            out.append({"rule": "numeric_drift", "detail": f"fraction '{m.group(0)}' is not a locked value"})
        return " "
    t = _FRACTION_RX.sub(sub_fraction, t)

    def sub_percent(m: re.Match) -> str:
        d = _dec(m.group(1))
        if d is None or d.scaleb(-2) not in values:
            out.append({"rule": "numeric_drift", "detail": f"'{m.group(1)}%' is not a locked value"})
        return " "
    t = _PERCENT_RX.sub(sub_percent, t)

    def sub_fraction_word(m: re.Match) -> str:
        n = Decimal(4) if m.group(1).lower() == "quarter" else Decimal(2)
        if n not in one_in:
            out.append({"rule": "numeric_drift", "detail": f"'{m.group(1)}' is not a locked value"})
        return " "
    t = _EN_FRACTION_WORDS.sub(sub_fraction_word, t)

    def sub_ar_fraction(m: re.Match) -> str:
        if _AR_FRACTION_WORDS[m.group(1)] not in one_in:
            out.append({"rule": "numeric_drift", "detail": "Arabic fraction word is not a locked value"})
        return " "
    t = _AR_FRAC_RX.sub(sub_ar_fraction, t)

    for m in _NUM_RX.finditer(t):
        d = _dec(m.group(0))
        if d is None or d not in plain_ok:
            out.append({"rule": "numeric_drift", "detail": f"'{m.group(0)}' is not a locked value"})

    for m in _EN_WORDSEQ_RX.finditer(t):
        seq = m.group(0)
        if seq.strip().lower() == "one":
            continue  # bare "one" is ordinary language ("one of you"); "one in N" is handled above
        d = _parse_en_words(seq)
        if d is None or d not in plain_ok:
            out.append({"rule": "numeric_drift", "detail": f"number word '{seq}' is not a locked value"})

    for m in _AR_WORD_RX.finditer(t):
        if Decimal(_AR_NUMBER_WORDS[m.group(1)]) not in plain_ok:
            out.append({"rule": "numeric_drift", "detail": "Arabic number word is not a locked value"})
    return out


# ----------------------------------------------------------------------------------------- leakage
HGVS_RX = re.compile(
    r"(?<![A-Za-z0-9])(?:[cgmnr]\.(?:\(|\*|-)?(?:\d|SYN)|p\.\(?(?:[A-Z][a-z]{2}|[A-Z])\d+|"
    r"N[MCGPR]_\d+|ENS[TG]\d{5,}|rs\d{3,})", re.I)

# Paraphrase map (gene -> condition names/abbreviations) used only as a deny list. Over-blocking only.
_ALIASES: dict[str, list[str]] = {
    "HBB": ["beta thalassemia", "beta thalassaemia", "sickle cell", "الثلاسيميا بيتا", "فقر الدم المنجلي",
            "الأنيميا المنجلية"],
    "HBA2": ["alpha thalassemia", "alpha thalassaemia", "الثلاسيميا ألفا"],
    "CYP21A2": ["congenital adrenal hyperplasia", "adrenal hyperplasia", "21-hydroxylase", "CAH",
                "تضخم الغدة الكظرية"],
    "SMN1": ["spinal muscular atrophy", "SMA", "ضمور العضلات الشوكي"],
    "MEFV": ["familial mediterranean fever", "mediterranean fever", "FMF", "حمى البحر المتوسط"],
    "ABCA4": ["stargardt", "retinal dystrophy", "ستارغاردت"],
    "GJB2": ["hearing loss", "deafness", "connexin 26", "فقدان السمع", "الصمم"],
    "CYP1B1": ["congenital glaucoma", "glaucoma", "الزرق"],
}
_THAL = ("thalassemia", "thalassaemia", "ثلاسيميا")
_PANEL_CACHE: dict | None = None


def _panel() -> dict:
    """symbol(upper) -> {hgnc_id, names}; read-only from contracts/gene_panel.json."""
    global _PANEL_CACHE
    if _PANEL_CACHE is None:
        genes = json.loads(_PANEL_PATH.read_text(encoding="utf-8"))["genes"]
        out = {}
        for g in genes:
            names = [g["condition"]] + [p.strip() for p in re.split(r"[/()]", g["condition"]) if p.strip()]
            out[g["symbol"].upper()] = {"hgnc_id": g["hgnc_id"], "names": names + _ALIASES.get(g["symbol"], [])}
        _PANEL_CACHE = out
    return _PANEL_CACHE


def _term_rx(term: str) -> re.Pattern:
    parts = [re.escape(p) for p in re.split(r"[\s\-_]+", term.strip()) if p]
    body = r"[\s\-_]*".join(parts)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)


def _spaced_rx(term: str) -> re.Pattern:
    body = r"[\s.\-_*·|]*".join(re.escape(c) for c in term)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)


def _expand_forbidden(terms: Iterable[str], allowed_genes: set[str]) -> list[str]:
    panel = _panel()
    by_id = {str(v["hgnc_id"]): k for k, v in panel.items()}
    allowed_names = set()
    for g in allowed_genes:
        for n in panel.get(g, {}).get("names", []):
            allowed_names.add(n.lower())
    if any(g in allowed_genes for g in ("HBB", "HBA2")):
        allowed_names.update(_THAL)
    out: list[str] = []
    for t in terms:
        t = normalize(str(t)).strip()
        if not t:
            continue
        out.append(t)
        sym = t.upper()
        m = re.fullmatch(r"(?:HGNC:)?(\d+)", sym)
        if m and m.group(1) in by_id:
            sym = by_id[m.group(1)]
            out.append(sym)
        if sym in panel:
            out.append(f"HGNC:{panel[sym]['hgnc_id']}")
            out += [n for n in panel[sym]["names"] if n.lower() not in allowed_names]
    return list(dict.fromkeys(out))


def _check_leakage(text: str, ctx: GateContext) -> list[dict]:
    out: list[dict] = []
    allowed = {str(r.get("gene", "")).upper() for r in ctx.locked_records or [] if isinstance(r, dict)}
    terms = _expand_forbidden(ctx.forbidden_terms or [], allowed)
    hit = 0
    for t in terms:
        if _term_rx(t).search(text):
            hit += 1
        elif re.fullmatch(r"[A-Za-z0-9]{3,12}", t) and _spaced_rx(t).search(text):
            hit += 1  # spaced/dotted obfuscation, e.g. "S M N 1", "H.B.B"
    if hit:
        out.append({"rule": "leakage", "detail": f"{hit} forbidden term pattern(s) matched (terms not echoed)"})
    if HGVS_RX.search(text):
        out.append({"rule": "leakage", "detail": "variant nomenclature (HGVS-like string) in outbound text"})
    return out


# ----------------------------------------------------------------------------- shared text helpers
# Rule classes below are lemma/phrase FAMILIES (verb stems x object families, reference x status
# co-occurrence, Arabic root/clitic variants), not corpus strings (DECISIONS #25).
_SENT_SPLIT = re.compile(r"(?<=[.!?؟;\n])(?:\s+|$)|(?<=[!?؟;\n])|\s+[-–—]\s+|[:\"“”«»()]")
_CLAUSE_SPLIT = re.compile(r"(?:[.](?=\s|$)|[!?؟;\n,،:\"“”«»()])+|\s+[-–—]\s+")  # decimals like 80.2 stay whole
_NEG_EN = re.compile(r"\b(?:not|never|no|nothing|nobody|no\s+one|isn'?t|aren'?t|wasn'?t|don'?t|doesn'?t|cannot|can'?t|n't)\b", re.I)
_NEG_AR = re.compile(r"(?:^|\s)(?:و|ف)?(?:ليس|ليست|لا|غير|ما|لم|لن|مو|مش)(?=\s)")  # clitic wa-/fa- allowed


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s and s.strip()]


def _clauses(text: str) -> list[str]:
    return [s.strip() for s in _CLAUSE_SPLIT.split(text) if s and s.strip()]


def _deobfuscate(text: str) -> str:
    """Collapse letter-by-letter obfuscation: 'Y.o.u s.h.o.u.l.d' -> 'You should'; 'y o u' -> 'you'."""
    t = re.sub(r"(?<![A-Za-z])(?:[A-Za-z][.\-_*·'’|]){2,}[A-Za-z]?(?![A-Za-z])",
               lambda m: re.sub(r"[.\-_*·'’|]", "", m.group(0)), text)
    t = re.sub(r"(?<![A-Za-z])(?:[A-Za-z][ ]){3,}[A-Za-z](?![A-Za-z])", lambda m: m.group(0).replace(" ", ""), t)
    return t


def _variants(text: str) -> list[str]:
    d = _deobfuscate(text)
    return [text] if d == text else [text, d]


def _negated_before(text: str, start: int, window: int = 25) -> bool:
    pre = text[max(0, start - window):start]
    return bool(_NEG_EN.search(pre) or _NEG_AR.search(" " + pre))


# ------------------------------------------------------------- leakage: partner status (DECISIONS #23)
_REF_EN = (r"(?:\b(?:your|ur|the|my|his|her)\s+(?:future\s+|husband-to-be\s+|wife-to-be\s+)?(?:partner|wife|husband|fianc[eé]e?|"
           r"spouse|bride|groom|other\s+half|betrothed|intended|husband-to-be|wife-to-be)(?:['’]s)?\b|"
           r"\b(?:his|her|their)\s+(?:family|relatives|parents|side|result|results|screen|test|tests|genes?|dna|status)\b|"
           r"\b(?:he|she)\b(?=\s+(?:is|was|has|had|carries|carry|tested|screened|also|too|might|may|could|does|did|"
           r"isn['’]?t|wasn['’]?t|doesn['’]?t|didn['’]?t|['’]s|will|would)\b))")
_STATUS_EN = (r"\b(?:carriers?|carries|carry(?:ing)?|variants?|mutations?|mutated|positive|negative|affected|unaffected|"
              r"gene\s+change|changed\s+copy|pathogenic|faulty\s+gene|the\s+gene|a\s+gene|bad\s+gene|"
              r"tested\s+(?:positive|negative)|screened?\s+(?:positive|negative)|has\s+(?:the|a)\s+(?:change|variant|condition)|"
              r"clear|cleared|healthy|sick|ill|diseased?)\b")
_REF_EN_RX = re.compile(_REF_EN, re.I)
_STATUS_EN_RX = re.compile(_STATUS_EN, re.I)
_REF_AR_RX = re.compile(r"(?:شريك|شريكة|شريكتك|شريكك|زوجتك|زوجك|زوجتكم|خطيبتك|خطيبك|عروسك|عريسك|الطرف\s+الآخر|"
                        r"عائلته|عائلتها|أهله|أهلها|شريك\s+حياتك|شريكة\s+حياتك|نتيجته|نتيجتها)")
_STATUS_AR_RX = re.compile(r"(?:حامل\w*\s*(?:لل|ل|جين|الجين|متغير|طفرة|المرض|صفة|مرض)|حاملة|يحمل|تحمل\s+(?:جين|الجين|متغير|طفرة|المرض|صفة)|"
                           r"طفرة|متغير|مصاب|مصابة|إيجابي\w*|ايجابي\w*|سلبي\w*|سليم|سليمة|المرض)")
# P4 (BUG-QA-11) classes. The contract names "the partner ... or their family": family references, family-history
# statements, vague status ("something showed up"), the partner's first-person voice, Arabizi.
_REF_FAMILY_EN_RX = re.compile(
    r"\b(?:your\s+)?(?:future\s+)?in-?laws\b|\b(?:his|her|their)\s+(?:own\s+)?(?:mother|father|mum|mom|dad|brothers?|sisters?|siblings?|"
    r"cousins?|uncles?|aunts?|grand\w+|ancestors|lineage|bloodline|line|people|tribe|clan|kids|children|son|daughter)\b|"
    r"\bthe\s+other\s+(?:family|side|partner|person)\b", re.I)
_FAMHX_EN_RX = re.compile(
    r"\b(?:has|have|had|got|with|carr(?:y|ies))\s+(?:a\s+|an\s+)?(?:(?:known|strong|long|family|medical|genetic|serious)\s+)*"
    r"(?:history|condition|disorder|syndrome|illness|disease|problem|issue)s?\b|\bruns?\s+in\b|\bran\s+in\b|\brunning\s+in\b|"
    r"\b(?:died|passed\s+away)\b|\blost\s+(?:a|two|their|his|her)\s+(?:\w+\s+)?(?:child|baby|son|daughter)\b|"
    r"\b(?:sick|affected|ill|disabled)\s+(?:child|baby|son|daughter|brother|sister|kids|children|relative|cousin)\b|\b(?:inherited|hereditary)\b",
    re.I)
_VAGUE_EN_RX = re.compile(
    r"\b(?:something|anything)\b(?:\s+\w+){0,3}?\s+(?:in|on|with|about|came\s+up|showed|shows|turned\s+up|was\s+found|found|flagged|"
    r"detected|picked\s+up|there)\b|\b(?:flagged|found|show|showed|shows|showing|detected|picked\s+up|came\s+back\s+with|turned\s+up|revealed)\s+"
    r"(?:\w+\s+){0,2}?(?:something|an?\s+(?:issue|problem|finding|concern|flag)|a\s+red\s+flag)\b|\bwas\s+flagged\b|"
    r"\b(?:isn['’]?t|is\s+not|wasn['’]?t|was\s+not|not\s+exactly|not\s+entirely|not\s+totally|not|un)[\s-]*clean\b|\bclean\b|"
    r"\bnot\s+(?:normal|clear|good|great|ok|okay|fine|perfect|reassuring)\b|\bred\s+flags?\b|\b(?:abnormal|unusual|concerning|worrying)\b",
    re.I)
_NONDISCLOSURE_EN = re.compile(
    r"\b(?:can['’]?t|cannot|won['’]?t|will\s+not|do\s+not|don['’]?t|does\s+not|doesn['’]?t|did\s+not|didn['’]?t|never|not\s+able\s+to|"
    r"unable\s+to|is\s+not|isn['’]?t)\s+"
    r"(?:\w+\s+){0,2}?(?:share|shared|show|shown|tell|disclose|disclosed|reveal|revealed|say|give|discuss|see|visible)\b", re.I)
_FIRST_PERSON_STATUS_EN = re.compile(
    r"\b(?:i|i['’]m|i\s+am|i['’]ve|me|my)\b(?:\s+\w+){0,3}?\s+(?:a\s+)?(?:carriers?|carry|carrying|carries|positive|affected|"
    r"variants?|mutations?|the\s+gene|gene\s+change|changed\s+copy|pathogenic)\b|\bmy\s+(?:own\s+)?(?:family|parents|mother|father|"
    r"brother|sister|side)\b(?:\s+\w+){0,4}?\s+(?:history|runs?\s+in|carr\w+|condition|disease|affected|sick)\b", re.I)
_REF_AR_FAMILY_RX = re.compile(
    r"(?:أهل|اهل|عائلة|عايلة|عيلة|أسرة|اسرة|أم|ام|أبو|ابو|أخو|اخو|أخت|اخت|عم|خال|جد|جدة|ولد|بنت|أقارب|اقارب)\s+"
    r"(?:خطيب|زوج|شريك|عروس|عريس|حرم|مرت|رجل|رجال)\w*|أسرته|أسرتها|عيلته|عيلتها|عايلته|عايلتها|أهل\s+الطرف\s+(?:الثاني|الآخر)|"
    r"نسايب\w*|أنساب\w*|أصهار\w*|حرمك|مرتك|أم\s+عيالك|بو\s+عيالك|رجلك|رجالك|رجّالك")
_FAMHX_AR_RX = re.compile(
    r"تاريخ\s+(?:عائلي|مرضي|وراثي)|سجل\s+(?:عائلي|مرضي)|وراثي\w*|منتشر\w*|يجري\s+في|موجود\w*\s+(?:في|عند)|مرض\w*|حالة|حالات|"
    r"توف(?:ي|ى)\w*|مات\w*|فقد\w*\s+(?:طفل|ولد|بنت|ابن|جنين)|(?:طفل|ولد|بنت|عيال|أطفال)\w*\s+(?:مريض|مرضى|مصاب)\w*")
_VAGUE_AR_RX = re.compile(
    r"(?:في|فيه|فيها|فيهم)\s+(?:شي|شيء|اشي|شيئ)|طلع\w*\s+(?:\S+\s+)?(?:شي|شيء|اشي)|ظهر\w*\s+(?:\S+\s+)?(?:شي|شيء)|مشكل\w*|ملاحظ\w*|"
    r"غير\s+طبيعي\w*|(?:مو|مش|مب|ليست|ليس|غير)\s+نظيف\w*|نظيف\w*|إشارة|علامة")
_NONDISCLOSURE_AR = re.compile(r"(?:لا|لن|ما)\s+(?:نستطيع|يمكننا|نقدر|نشارك|نكشف|نعرض|نخبر|نقول|تظهر|يظهر|نظهر|نُظهر)")
_FIRST_PERSON_STATUS_AR = re.compile(r"(?:أنا|انا)\s+(?:\S+\s+)?(?:حامل\w*|أحمل|احمل|مصاب\w*|عندي\s+(?:جين|طفرة|متغير))|نتيجتي\s+(?:\S+\s+)?(?:إيجابي\w*|ايجابي\w*|فيها)")
_AZ_REF_RX = re.compile(
    r"\b(?:zawj(?:t|it|at)?(?:ak|ik|ek|k)|zo+j(?:t|at)?(?:ak|ik|ek|k)|marr?t(?:ak|ek|k)|[7h]arm(?:ak|ek)|(?:kh|5)ate?e?b(?:t)?(?:ak|ik|ek|k)|"
    r"khatib(?:t)?(?:ak|ik|ek)|share?e?k(?:t)?(?:ak|ik|ek)|3aroo?s(?:t)?(?:ak|ik|ek)|3aree?s(?:ak|ik|ek)|ahl(?:o|ha|uh|aha)|"
    r"3a(?:y|2|i)?e?lt(?:o|ha|uh))\b", re.I)
_AZ_STATUS_RX = re.compile(
    r"\b(?:[7h]aa?m(?:e|i)?l(?:a|eh|ah|at|ah)?|ta?[7h]mil\w*|ti[7h]mil\w*|y[ie]?[7h]mil\w*|mosaa?b\w*|musaa?b\w*|tafra\w*|"
    r"mutagh\w*|[ie]jaa?bi\w*|positive|carrier|mare[e]?dh?\w*|marid\w*|f(?:i|ee)ha?\s+(?:shi|shay|eshi))\b", re.I)
_SHARED_MARKERS = re.compile(r"\b(?:both|also|too|as\s+well|same\s+gene|shared)\b|كلاكما|كلا|أيضا|أيضاً|نفس\s+الجين|المشترك", re.I)


_SECOND_PERSON = re.compile(r"(?:\byou\b|\byour\s+own\b|\byou['’]re\b|أنت|انت|نتيجتك)\s*$", re.I)


def _partner_status(sentence: str, status_rx: re.Pattern) -> bool:
    """True if some status term in the sentence is not simply about the recipient ('you carry ...')."""
    for m in status_rx.finditer(sentence):
        if not _SECOND_PERSON.search(sentence[max(0, m.start() - 14):m.start()]):
            return True
    return False


def _authorized_residuals(ctx: GateContext) -> set:
    """A carrier_partner_only record addressed to this recipient authorizes its own residual-carrier figure
    (the chance that a screen-negative partner is still a carrier). Nothing else about the partner."""
    out = set()
    for r in ctx.locked_records or []:
        if isinstance(r, dict) and r.get("audience") == "carrier_partner_only" and r.get("posterior_carrier_b_one_in"):
            m = re.search(rf"({_NUM})\s*$", normalize(r["posterior_carrier_b_one_in"]))
            if m and _dec(m.group(1)) is not None:
                out.add(_dec(m.group(1)))
    return out


_CONTRAST = re.compile(r"\s*(?:,|;)?\s*\b(?:but|however|though|although|yet|still|except)\b|\s*(?:،)?\s*(?:لكن|ولكن|بس|إلا\s+أن|الا\s+ان|غير\s+أن)(?![ء-ي])", re.I)


def _vague_hit(s: str, vague: re.Pattern, nondisclosure: re.Pattern) -> bool:
    return any(vague.search(c) and not nondisclosure.search(c) for c in _CONTRAST.split(s) if c)


def _check_partner_status(text: str, ctx: GateContext) -> list[dict]:
    hidden, shared, _ = ctx.resolved()
    shared_names: list[str] = []
    panel = _panel()
    by_id = {v["hgnc_id"]: k for k, v in panel.items()}
    for hid in shared:
        sym = by_id.get(hid)
        if sym:
            shared_names += [sym] + panel[sym]["names"]
    authorized = _authorized_residuals(ctx)
    # Partner's first-person voice (roleplay / quoted partner): our own copy never speaks about "my" status.
    if hidden and (_FIRST_PERSON_STATUS_EN.search(text) or _FIRST_PERSON_STATUS_AR.search(text)):
        return [{"rule": "leakage", "detail": "first-person genetic-status statement (partner voice) outside the consented intersection"}]
    for s in _sentences(text):
        ref_en = _REF_EN_RX.search(s) or _REF_FAMILY_EN_RX.search(s)
        ref_ar = _REF_AR_RX.search(s) or _REF_AR_FAMILY_RX.search(s)
        en = ref_en and (_partner_status(s, _STATUS_EN_RX) or _FAMHX_EN_RX.search(s)
                         or _vague_hit(s, _VAGUE_EN_RX, _NONDISCLOSURE_EN))
        ar = ref_ar and (_partner_status(s, _STATUS_AR_RX) or _FAMHX_AR_RX.search(s)
                         or _vague_hit(s, _VAGUE_AR_RX, _NONDISCLOSURE_AR))
        az = _AZ_REF_RX.search(s) and _AZ_STATUS_RX.search(s)
        if not (en or ar or az):
            continue
        if not hidden and (_SHARED_MARKERS.search(s) or any(_term_rx(n).search(s) for n in shared_names)):
            continue  # statement about the consented intersection
        if authorized and any(_dec(m.group(0)) in authorized for m in _LOOSE_NUM_RX.finditer(s)):
            continue  # the recipient's own locked discordant record
        return [{"rule": "leakage", "detail": "statement about the partner's genetic status outside the consented intersection"}]
    return []


# --------------------------------------------------------------------------------------- directive
_FILLER = (r"^[\s'‘’`\"“”«»*_\-–—]*(?:(?:do\s+the\s+(?:\w+\s+){0,2}?thing\s+and|be\s+(?:\w+\s+)?(?:smart|sensible|wise|brave|realistic)\s+and|"
           r"go\s+ahead\s+and|just\s+go\s+and|"
           r"just|so|then|please|honestly|really|simply|and|but|well|ok|okay|look|listen|now|seriously|frankly|"
           r"trust\s+me|believe\s+me|my\s+advice|our\s+advice|advice|tip|bottom\s+line|in\s+short|yes|no)\b[\s,]*)*")
_OBJ = (r"(?:(?:(?:the|this|your|our|that|his|her)\s+)?(?:marriage|wedding|engagement|nikah|union|match|relationship|proposal|"
        r"betrothal|contract|marriage\s+contract|arrangement|commitment|katb\s+(?:el|al)?[-\s]?kitab|milcha|milka)|"
        r"him|her|them|it)\b")
_DEC_OBJ = (r"(?:cancel|call\s+off|break\s+off|end|stop|drop|postpone|delay|reconsider|rethink|abandon|quit|annul|"
            r"back\s+out\s+of|walk\s+away\s+from|pull\s+out\s+of|get\s+out\s+of|leave|dump|divorce|separate\s+from|forget|"
            r"go\s+through\s+with|proceed\s+with|go\s+ahead\s+with|carry\s+on\s+with|continue\s+with|move\s+forward\s+with|"
            r"push\s+ahead\s+with|complete|accept|reject|refuse|decline|marry|wed|choose|"
            r"step\s+back\s+from|pull\s+back\s+from|hold\s+off\s+on|think\s+twice\s+about|say\s+(?:yes|no)\s+to|finali[sz]e|"
            r"commit\s+to|let\s+go\s+of|give\s+up(?:\s+on)?|put\s+an\s+end\s+to|stay\s+away\s+from|run\s+from)")
_DEC_INTRANS = (r"(?:separate|divorce|split\s+up|break\s+up|walk\s+away|back\s+out|get\s+married|marry|wed|elope|"
                r"(?:go\s+ahead|proceed|cancel|move\s+on)(?=\s*(?:$|now|anyway|regardless|then|already|with\s+confidence)))")
_FIND = r"(?:find|choose|pick|look\s+for|search\s+for|get|go\s+for)\s+(?:yourself\s+)?(?:someone|somebody|another|a\s+different|a\s+new|a\s+better|an\s+unrelated)\b"
_IMPERATIVE_RX = re.compile(
    _FILLER + r"(?:(?:don['’]?t|do\s+not|never|please\s+don['’]?t)\s+)?"
    rf"(?:(?:break|call|put|cut)\s+(?:it|this|that|things|him|her|them|(?:the|this|your)\s+(?:marriage|wedding|engagement|nikah|match|union|contract))\s+off\b|"
    rf"{_DEC_OBJ}\s+{_OBJ}|{_DEC_INTRANS}\b|(?:go\s+ahead|proceed)\s+(?:and|to)\s+(?:marry|wed|get\s+married)\b|{_FIND})", re.I)
_ACT = (r"(?:marry|marrying|get(?:ting)?\s+married|wed|cancel\w*|call(?:ing)?\s+(?:\w+\s+){0,3}?off|break(?:ing)?\s+(?:\w+\s+){0,3}?(?:off|up)|"
        r"proceed\w*|go(?:ing)?\s+ahead|go(?:ing)?\s+through|terminat\w*|abort\w*|end(?:ing)?\s+(?:it|the|this|your|a)\b|"
        r"separat\w*|divorc\w*|reconsider\w*|postpon\w*|leave\s+(?:him|her|them|each\s+other)|walk\s+away|back\s+out|"
        r"(?:have|having)\s+(?:a\s+)?(?:child|children|bab(?:y|ies)|kids)|tie\s+the\s+knot|split(?:ting)?\s+up|call(?:ing)?\s+it\s+quits|"
        r"sign(?:ing)?\s+(?:the\s+|your\s+|this\s+)?(?:marriage\s+contract|nikah|marriage\s+papers|contract)|let\s+(?:him|her|them)\s+go|part\s+ways|"
        r"go\s+(?:your\s+)?separate\s+ways|end\s+things|"
        r"(?:step|pull)\s+back\s+from\s+(?:the|this|your)\s+(?:marriage|wedding|engagement|nikah|match|union|contract|marriage\s+contract)|"
        r"hold\s+off\s+on\s+(?:the|this|your)\s+(?:marriage|wedding|engagement|nikah)|"
        r"say\s+(?:yes|no)\s+to\s+(?:him|her|the\s+(?:marriage|proposal|match)))")
_MARRIAGE_WORDS = (r"(?:marr\w*|wedding|engage\w*|nikah|fianc\w*|union|cancel\w*|call\w*\s+off|break\w*\s+off|separat\w*|divorc\w*|"
                   r"leave\s+(?:him|her)|marriage\s+contract|katb\s+(?:el|al)?[-\s]?kitab|milcha|milka|th(?:e|is)\s+match|"
                   r"tie\s+the\s+knot|walk\s+away|step\s+back|part\s+ways)")
DIRECTIVE_EN = [
    re.compile(rf"\b(?:you|u|you\s+two|you\s+both|both\s+of\s+you|the\s+two\s+of\s+you|the\s+couple|they|couples?\s+like\s+you|y['’]?all)\s+"
               rf"(?:really\s+|definitely\s+|probably\s+|clearly\s+|honestly\s+|seriously\s+)?"
               rf"(?:should|must|need\s+to|ought\s+not\s+to|ought\s+to|had\s+better|['’]d\s+better|have\s+to|shall|would\s+be\s+wise\s+to|'?d\s+be\s+wise\s+to)"
               rf"(?:n['’]t|\s+not|\s+never)?\s+(?:\w+\s+){{0,3}}?{_ACT}", re.I),
    re.compile(r"\byou\s+(?:should|must|ought\s+to)\s+(?:too|as\s+well|also|do\s+the\s+same|follow\s+(?:suit|them|their\s+lead))\b", re.I),
    re.compile(rf"\b(?:i|we)\s+(?:strongly\s+|would\s+|really\s+)?(?:recommend|advise|suggest|urge|encourage)\s+"
               rf"(?:that\s+)?(?:you\s+)?(?:(?:do\s+)?not\s+|against\s+)?(?:to\s+)?{_ACT}", re.I),
    re.compile(rf"\b(?:i|we)(?:['’]d|\s+would|\s+will)\s+(?:not\s+|never\s+|definitely\s+|personally\s+|honestly\s+|probably\s+)*"
               rf"(?:{_DEC_OBJ}|{_DEC_INTRANS}|{_ACT})", re.I),
    re.compile(rf"\b(?:it(?:['’]s|\s+is|\s+would\s+be|\s+will\s+be)\s+)?(?:best|better|wiser|safer|smarter|advisable|preferable|sensible)\s+"
               rf"(?:for\s+(?:you|both\s+of\s+you|the\s+two\s+of\s+you)\s+)?(?:not\s+)?(?:to|if\s+you)\s+(?:not\s+)?(?:{_DEC_OBJ}|{_DEC_INTRANS}|{_ACT})", re.I),
    re.compile(rf"\b(?:don['’]t|do\s+not|never|please\s+do\s+not)\s+{_ACT}", re.I),
    re.compile(r"\b(?:find|choose|pick|look\s+for|search\s+for)\s+(?:a\s+|yourself\s+a\s+)?(?:another|a\s+different|a\s+new|a\s+better|an\s+unrelated|someone\s+else)\s*"
               r"(?:partner|spouse|husband|wife|fianc\w*|match|one|person)?\b", re.I),
    re.compile(r"\b(?:the\s+)?(?:right|best|only\s+responsible|responsible|smart|smartest|wise|wisest|correct|sensible|logical|safest|safe|obvious|"
               r"only|honest|mature|reasonable)\s+(?:choice|decision|thing|move|option|step|course|path|way|answer|plan)\s+"
               r"(?:is|would\s+be|for\s+you\s+is)\s+to\b", re.I),
    re.compile(r"\b(?:my|our|the\s+app['’]?s|the\s+best|the\s+medical|the\s+clear|the\s+obvious)\s+(?:advice|recommendation|suggestion|verdict|opinion|view|counsel|guidance)\b"
               rf"[^.]{{0,80}}?{_MARRIAGE_WORDS}", re.I),
    re.compile(r"\b(?:marriage|wedding|engagement|nikah)\s+(?:should|must|ought\s+to|had\s+better|needs?\s+to|shouldn['’]t|mustn['’]t)\s+(?:not\s+)?"
               r"(?:go\s+ahead|proceed|happen|take\s+place|continue|be\s+(?:cancel\w*|called\s+off|postponed|stopped))", re.I),
]
# P4 (BUG-QA-8) families: recommendation verbs beyond should/advise, passive advice, reported directives, "it's time to",
# superlative-choice framings, implicit "find another match", "might want to / better off".
_DEC_PHRASE = rf"(?:{_DEC_OBJ}\s+{_OBJ}|{_ACT})"
DIRECTIVE_EN_P4 = [
    re.compile(rf"\b(?:i|we|the\s+(?:team|doctors?|counsel\w*|clinic|app|experts?))\s+(?:(?:\w+ly|would|really|must|do|['’]d|can\s+only|have\s+to)\s+)*"
               rf"(?:recommend\w*|advis\w*|suggest\w*|urg\w*|encourag\w*|implor\w*|beg|want|would\s+like|invite|warn|caution|counsel)\s+"
               rf"(?:that\s+)?(?:you|both\s+of\s+you|the\s+two\s+of\s+you|you\s+both|you\s+two)?\s*(?:(?:do\s+)?not\s+|against\s+|strongly\s+)?"
               rf"(?:to\s+)?(?:\w+ly\s+)?{_DEC_PHRASE}", re.I),
    re.compile(rf"\b(?:you\s+are|you['’]re|couples\s+(?:like\s+you\s+)?are)\s+(?:\w+ly\s+)?(?:advised|urged|encouraged|recommended|asked|told|expected)\s+"
               rf"(?:not\s+)?to\s+(?:\w+ly\s+)?{_DEC_PHRASE}|\bit\s+is\s+(?:\w+ly\s+)?(?:recommended|advised|suggested|advisable|wise)\s+"
               rf"(?:that\s+(?:you\s+)?)?(?:not\s+)?(?:to\s+)?{_DEC_PHRASE}", re.I),
    re.compile(rf"\b(?:said|says|say|told|tell|tells|telling|wrote|writes|advised|urged|warned|insist\w*)\s+(?:you|u|me|us|them|him|her)?\s*"
               rf"(?:that\s+you\s+(?:should|must|need\s+to|have\s+to|ought\s+to)\s+|to\s+)(?:not\s+|never\s+)?{_DEC_PHRASE}", re.I),
    re.compile(rf"\b(?:it['’]s|it\s+is|now\s+is|this\s+is)\s+(?:high\s+|about\s+|probably\s+|really\s+)?(?:the\s+)?time\s+"
               rf"(?:for\s+(?:you|both\s+of\s+you|the\s+two\s+of\s+you|you\s+two)\s+)?to\s+(?:{_DEC_PHRASE}|{_DEC_INTRANS}|move\s+on|let\s+go|say\s+goodbye)", re.I),
    re.compile(r"\b(?:the\s+)?(?:kindest|fairest|wisest|safest|smartest|best|simplest|easiest|healthiest|bravest|noblest|surest|soundest|"
               r"most\s+\w+|least\s+\w+|kind|fair|loving|caring|prudent|practical|natural|ethical|moral|brave|noble|sane|right|responsible|smart|"
               r"wise|correct|sensible|logical|safe|obvious|only|honest|mature|reasonable)\s+(?:choice|decision|thing|move|option|step|course|path|"
               r"way|answer|plan)(?:\s+(?:here|now|to\s+make|left))?(?:\s+(?:for|in|about|regarding)\s+(?:\w+\s+){0,3}?\w+)?\s+(?:is|would\s+be|will\s+be|remains)\s+(?:for\s+you\s+)?"
               r"(?:to\b|that\s+you\b|clear\b|obvious\b|simple\b)", re.I),
    re.compile(rf"\b(?:you|you\s+two|you\s+both|both\s+of\s+you)\s+(?:might|may)\s+want\s+to\s+(?:\w+\s+){{0,2}}?{_ACT}|"
               rf"\byou\s+(?:would|['’]d)\s+do\s+well\s+to\s+(?:\w+\s+){{0,2}}?{_ACT}|"
               rf"\b(?:you|you\s+two|both\s+of\s+you)\s+(?:are|['’]re|would\s+be|['’]d\s+be)\s+better\s+off\s+(?:not\s+)?{_ACT}", re.I),
    re.compile(r"\b(?:finding|choosing|picking|looking\s+for|searching\s+for|seeking|consider(?:ing)?\s+(?:finding\s+)?)\s*(?:a\s+|yourself\s+a\s+)?"
               r"(?:another|a\s+different|a\s+new|a\s+better|an\s+unrelated|someone\s+else|other|a\s+safer)\s*(?:partner|spouse|husband|wife|"
               r"fianc\w*|match|person|man|woman|bride|groom|suitor|candidate)\b|\b(?:another|a\s+different|a\s+better|a\s+new|an\s+unrelated|"
               r"a\s+safer|a\s+non[-\s]?carrier)\s+(?:match|partner|spouse|husband|wife|bride|groom|suitor|candidate|fianc\w*)\b", re.I),
]
_FINAL_ANSWER = re.compile(r"\b(?:final|my|our|short|honest|straight|real|simple)\s+answer\s*(?:is|would\s+be|:|-|—)?\s*[\"“'‘]?\s*"
                           r"(?:yes|no|nope|yep|definitely|absolutely)\b", re.I)
_REPORTED_Q = re.compile(r"\b(?:ask\w*|wonder\w*|question\w*|unsure|not\s+sure|deciding|decide|considering|thinking\s+about|debat\w*)\s+"
                         r"(?:us\s+|you\s+|me\s+|themselves\s+|yourselves\s+|ourselves\s+)?(?:whether|if)\b", re.I)
_ADVICE_Q = re.compile(r"\b(?:should|ought|must|would\s+you|shall|is\s+it\s+(?:wise|better|best|a\s+good\s+idea|smart|right|ok|okay|safe)|"
                       r"do\s+you\s+(?:think|recommend|advise|suggest)|what\s+would\s+you\s+do|better\s+to)\b", re.I)
_ANSWER_RX = re.compile(
    r"^\W*(?:(?:my|our|the|final|short|honest|straight)\s+answer(?:\s+is)?\s*[:\-]?\s*|(?:i|we)['’]?d\s+say\s+|"
    r"(?:i|we)\s+(?:would\s+say|think|believe|feel|say)\s+|honestly,?\s+|frankly,?\s+|in\s+(?:my|our)\s+(?:view|opinion),?\s+)?"
    r"(?:yes|no(?!\s+(?:one|body|single|decision|advice|right|wrong|recommendation|answer|choice)\b)|nope|yep|yeah|definitely(?:\s+not)?|"
    r"absolutely(?:\s+not)?|certainly(?:\s+not)?|of\s+course(?:\s+not)?|not\s+at\s+all|probably\s+not|they\s+should(?:n['’]t)?|"
    r"you\s+should(?:n['’]t)?|i\s+would(?:n['’]t)?)\b", re.I)
# a reply that hands the decision back is not an answer ("No, that is your decision", "we can't answer that")
_ANSWER_NEUTRAL = re.compile(r"\byour\s+(?:own\s+)?(?:choice|call|decision)|\bup\s+to\s+(?:you|both\s+of\s+you)\b|\byours\s+to\b|"
                             r"\b(?:we|i)\s+(?:can['’]?t|cannot|don['’]?t|do\s+not|won['’]?t|will\s+not)\b|\bno\s+one\b|\bnobody\b|\bcounsel\w*|"
                             r"قرارك\w*|خيارك\w*|يعود\s+(?:إليك|لك)\w*|لكما\s+القرار|لكم\s+القرار|المستشار\w*|(?:لا|لن)\s+(?:نقدم|ننصح|نجيب|نقرر|نحدد)", re.I)
_AR_ADVICE_Q = re.compile(r"هل\s+(?:يجب|ينبغي|من\s+الأفضل|الأفضل|تنصح\w*|أنصح|ننصح)|لازم|المفروض|الأفضل|تنصح\w*|تنصحون\w*|برأيك")
_AR_ANSWER_RX = re.compile(r"^\W*(?:نعم|لا(?=\s*(?:[،,.!؟]|$|أبد|ابد))|أكيد|اكيد|طبعا|طبعاً|أبدا|أبداً|ابدا|إيه|ايه|اي|لأ|جوابي|الجواب|رأيي|نصيحتي)(?![ء-ي])")
# Arabizi (transliterated Gulf/Levantine): decision verb + marriage noun, or a modal/advice word + marriage noun. TODO(ar) review.
_AZ_NOUN = (r"(?:(?:el|al|il|l)[\s-]?)?(?:kh[eiuo]tba|5[eiuo]tba|zawa?a?j|zwaj|3[eiu]rs|milcha|milka|malka|nika?h|kitab|ktab|"
            r"3a?[qg]d|irtiba?t|ertibat|zaffa|zafaf)\b")
_AZ_VERB = (r"(?:kan?sel\w*|cansel\w*|cancel\w*|[aei]?lgh[iy]\w*|t[ie]?lgh[iy]\w*|algh\w*|[ie]?fsa?kh\w*|tfsa?kh\w*|tfs5\w*|f[ou]kk?\w*|tfokk?\w*|"
            r"[ie]?trok\w*|utruk\w*|tsib\w*|sib\w*|seeb\w*|t?kamm?el\w*|kamml\w*|t?w[ae]?[gq]{1,2}if\w*|t?tamm\w*|a?jjel\w*|t?a2a?jil\w*|t?ajjil\w*)")
_AZ_DIRECTIVE = re.compile(
    rf"\b{_AZ_VERB}\s+(?:\w+\s+){{0,2}}?{_AZ_NOUN}|"
    rf"\b(?:lazem|lazim|la2zem|la2zm|mafroo?d|mfrood|a7san|ahsan|a7sanlak|ahsanlak|a7sanlkom|ansa7\w*|nansa7\w*|ansah\w*|nansah\w*|nnsa7\w*|"
    rf"anse7\w*|ba3?dam|b3adam|bi3adam|nsha?j3?\w*)\b[^.]{{0,40}}?{_AZ_NOUN}", re.I)
_COUNTERFACTUAL = re.compile(r"\bif\s+i\s+(?:were|was)\s+(?:you|in\s+your\s+(?:shoes|place|position))|\bin\s+your\s+(?:shoes|place|position)\b|"
                             r"\bif\s+it\s+were\s+(?:me|up\s+to\s+me)\b|\boff\s+the\s+record\b|\bnot\s+as\s+(?:the|an?)\s+(?:app|assistant|ai|bot|system)\b|"
                             r"\bbetween\s+(?:us|you\s+and\s+me)\b|\bas\s+your\s+(?:\w+\s+)?(?:sister|brother|friend|mother|father|aunt|uncle|cousin|elder|doctor|mum|mom|dad)\b",
                             re.I)
_DECISION_TERMS = re.compile(rf"{_MARRIAGE_WORDS}|\b(?:{_DEC_OBJ})\s+{_OBJ}|\bnot\s+worth\b|\b(?:terminat|abort)\w*", re.I)
_RECO_NOT_HAPPEN = re.compile(r"\b(?:marriage|wedding|engagement|nikah)\s+(?:does\s+not|doesn['’]t|do\s+not|not|never|won['’]t|will\s+not)\s+"
                              r"(?:go\s+ahead|proceed|happen|take\s+place|continue)", re.I)
_RECO_WORDS = re.compile(r"\b(?:recommend\w*|advi[cs]e\w*|suggest\w*|urge|best|better|prefer\w*|hope|should|must)\b", re.I)
_JUDGEMENT = re.compile(r"\b(?:marrying|to\s+marry|marriage\s+to|this\s+(?:marriage|match|union|wedding|engagement)|the\s+(?:marriage|wedding|engagement)|"
                        r"(?:going|go)\s+through\s+with\s+(?:it|this|the\s+(?:marriage|wedding)))\b[^.]{0,50}?"
                        r"\b(?:would\s+be|is|will\s+be|seems|looks)\s+(?:not\s+|n['’]t\s+)?(?:like\s+)?(?:a\s+|an\s+)?(?:big\s+|huge\s+|terrible\s+|serious\s+)?"
                        r"(?:mistake|bad\s+idea|error|wrong|unwise|foolish|regret\w*|disaster|terrible|good\s+idea|great\s+idea|right\s+choice|"
                        r"wise|safe\s+choice|fine\s+choice|risky|irresponsible)\b", re.I)
_POSITIVE_EVAL = re.compile(r"\b(?:good\s+idea|great\s+idea|right\s+choice|wise|safe\s+choice|fine\s+choice)\b", re.I)
_NEUTRAL_DISJ = re.compile(r"\b(?:whether|or\s+not|either\s+way|or\s+no)\b|أو\s+عدمه|من\s+عدمه|أم\s+لا|أو\s+لا|سواء", re.I)
_MULTILINGUAL = re.compile(
    r"\b(?:devr\w*|doi[st]\w*|il\s+faut|faut\s+pas|debe\w*|deber\w*|sollt?\w*|musst?\w*|dovresti|dovete|no\s+deb\w*)\b[^.]{0,30}?"
    r"\b(?:mari\w*|casar\w*|casen|heirat\w*|sposa\w*|annul\w*|cancel\w*|abort\w*|avort\w*|divorc\w*|separ\w*)|"
    r"\b(?:ne\s+vous\s+mariez|no\s+te\s+cases|no\s+se\s+casen|heirate\s+nicht|non\s+sposarti)\b|"
    r"\b(?:la|lazem|lazim|la2zem|la2zm|mafroo?d|mfrood|ma|mo|la\s+t)\s*(?:\w+\s+)?(?:t?t[sz]awa?j\w*|tetzawaj\w*|zawaj\w*|tkamm?el\w*|tkmel\w*|"
    r"t?[ie]lghi\w*|tfsa?kh\w*|tetlaq\w*|t?sa?yb\w*|t?ookhedh\w*|takhedh\w*|takhith\w*)", re.I)

# Arabic (MSA + Gulf). Roots: z-w-j (marry), l-gh-y (cancel), k-m-l (complete), f-s-kh (annul), t-r-k (leave),
# f-s-l (separate), t-l-q (divorce), kh-t-b (engage), j-h-d (abort). TODO(ar) native review.
_AR_ROOTS = (r"(?:تتزوج\w*|تزوج\w*|يتزوج\w*|(?<!شهادة )(?<!قبل )(?<!فحص )(?<!فحوصات )(?<!شهادات )ال?زواج|زيجة|خطوب\w*|الخطبة|"
             r"إلغاء|الغاء|تلغ\w*|ألغ\w*|الغ\w*|يلغ\w*|فسخ\w*|تفسخ\w*|تكمل\w*|تكملي\w*|إكمال|اكمال|تتمم\w*|انفصال|تنفصل\w*|انفصل\w*|"
             r"طلاق|تطلق\w*|اترك\w*|تترك\w*|ابتعد\w*|تبتعد\w*|جه(?:ا)?ض\w*|إنهاء\s+الحمل|تنجب\w*|الإنجاب|تاخذ\w*|تأخذ\w*|تارتبط\w*|ترتبط\w*|الارتباط|"
             # P4: marriage-contract vocabulary and proceed / withdraw / postpone verbs (BUG-QA-8)
             r"(?:عقد|كتب|كتابة)\s+(?:ال)?(?:قران|زواج|كتاب)|القران|الملكة|الملچة|ملكة|العرس|الزفاف|عرس|زفاف|الدخلة|إتمام|اتمام|تتمو\w*|"
             r"المضي|تمضي\w*|التراجع|تتراجع\w*|تراجع\w*|العدول|تعدل\w*\s+عن|التوقف\s+عن|تتوقف\w*\s+عن)")
DIRECTIVE_AR = [
    # advice / modal frame + decision root in the same clause
    re.compile(r"(?:ننصح|أنصح|انصح|ننصحك\w*|أنصحك\w*|نوصي|أوصي|يجب|ينبغي|يتعين|لازم|لا\s*بد|لابد|عليك|عليكم|عليكما|"
               r"من\s+الأفضل|الأفضل|الأحسن|أحسن\s+لك|أحسن\s+لكم|المفروض|يفضل|يُفضل|نصيحتي|نصيحتنا|رأيي|برأيي|في\s+رأيي|"
               r"اقتراحي|توصيتي|توصيتنا|لو\s+كنت\s+مكانك\w*|لو\s+أنا\s+مكانك\w*|لو\s+انا\s+مكانك\w*|"
               # P4: urge / encourage / invite verbs, "not to" (bi-adam), "it is time", preference wishes (BUG-QA-8)
               r"نحث\w*|أحث\w*|احث\w*|نشجع\w*|أشجع\w*|اشجع\w*|ندعو\w*|أدعو\w*|ادعو\w*|نطلب\s+منك\w*|أطلب\s+منك\w*|نرجو\s+منك\w*|أرجو\s+منك\w*|"
               r"بعدم|الأولى|الاولى|الأصلح|الأسلم|الأنسب|حان\s+الوقت|آن\s+الأوان|يا\s*ليت|أتمنى\s+أن|نتمنى\s+أن|ودي|بودي|لو\s+علي|لو\s+بيدي|"
               r"الخيار\s+(?:الأفضل|الصحيح|الأسلم|الوحيد)|القرار\s+(?:الأفضل|الصحيح|الأسلم|الحكيم))"
               rf"[^.!؟?\n،,]{{0,45}}?{_AR_ROOTS}"),
    # negated jussive / prohibitive of the decision verbs
    re.compile(r"(?:^|\s)(?:لا|ما|لاتـ?)\s*(?:ت|تـ)(?:تزوج|زوج|اخذ|أخذ|كمل|كملي|كملوا|تمم|خطب|ربط|رتبط|ورط|سوي\s+الزواج)\w*"),
    # imperative of marry / cancel / leave at clause start or after the conjunction wa-/fa-
    re.compile(r"(?:^|[\s،,.!؟])(?:و|ف)?(?:تزوج|تزوجي|تزوجوا|تزوجا|ألغ|الغ|الغي|ألغي|ألغوا|افسخ\w*|اترك\w*|انفصل\w*|ابتعد\w*|طلق\w*|"
               r"سيب\w*|خلها|خله|كنسل\w*|كمل|كملي|كملوا|اخطب\w*)(?=$|[\s،,.!؟])"),
    # find another partner (Gulf: dawwir lak wahda thaniya)
    re.compile(r"(?:دور|دوري|دوّر|ادور|ابحث|ابحثي|ابحثوا|شوف|شوفي|اختر|اختاري|اختار)\s+(?:لك\s+|لنفسك\s+|على\s+|عن\s+)?"
               r"(?:واحد|وحدة|واحدة|شريك\w*|زوج\w*|عروس\w*|غيره|غيرها|غير|بنت|ولد|رجل|امرأة)\w*"),
    re.compile(r"(?:شريك|شريكة|زوج|زوجة|عروس|واحدة|واحد|وحدة)\w*\s+(?:ثاني|ثانية|آخر|أخرى|اخرى|غيرها|غيره)"),
]
DIRECTIVE_AR.append(re.compile(
    r"(?:ال)?(?:زواج|عرس|زفاف|خطوب\w*|خطبة|ملكة|قران)(?:\s+\S+){0,2}?\s+(?:لازم|يجب|المفروض|لا\s*بد|لابد|ينبغي|الأفضل)\s+(?:أن\s+|ان\s+)?"
    r"(?:ي|ت|ين|يت|تت)?(?:وقف|توقف|لغى|لغي|نلغى|نلغي|تلغى|تأجل|أجل|نفسخ|فسخ|نهي|نتهي|خلص|نقطع|قطع)\w*"))
_AR_NEG_ADVICE = re.compile(r"(?:لا|لن|ما)\s+(?:ننصح|نوصي|أنصح|نقول|نخبر|نحدد|نقرر)")


def _check_directive(text: str) -> list[dict]:
    out: list[dict] = []

    def add(detail):
        out.append({"rule": "directive", "detail": detail})

    for variant in _variants(text):
        sents = _sentences(variant)
        families = [(f"EN family {i}", i in (2, 8), rx) for i, rx in enumerate(DIRECTIVE_EN)]
        families += [(f"EN P4 family {i}", i == 0, rx) for i, rx in enumerate(DIRECTIVE_EN_P4)]
        for name, neutral_ok, rx in families:
            for m in rx.finditer(variant):
                sent = next((s for s in sents if m.group(0)[:20] in s), variant)
                pre = sent[:max(0, sent.find(m.group(0)[:10]))]
                if neutral_ok and _NEUTRAL_DISJ.search(sent) and _NEG_EN.search(pre or sent[:1]):
                    continue  # "we do not advise whether to marry" - a neutrality disclaimer
                if _REPORTED_Q.search(pre):
                    continue  # "some couples ask whether they should ..." reports a question; answers are checked below
                add(f"directive phrasing ({name})")
                break
        # Q-and-A: an advice question about the decision (direct or reported) followed by a yes/no style answer
        decision_msg = bool(_DECISION_TERMS.search(variant) or re.search(_ACT, variant, re.I))
        if decision_msg and _FINAL_ANSWER.search(variant):
            add("answer to a decision question")
        for k, s in enumerate(sents[:-1]):
            short_q = s.rstrip().endswith("?") and len(re.findall(r"\w+", s)) <= 4
            q_en = (s.rstrip().endswith("?") and (_ADVICE_Q.search(s) or short_q)) or _REPORTED_Q.search(s)
            nxt = sents[k + 1]
            if _ANSWER_NEUTRAL.search(nxt):
                continue
            if q_en and (_DECISION_TERMS.search(s) or re.search(_ACT, s, re.I)) and _ANSWER_RX.search(nxt):
                add("answer to a decision question")
            if _AR_ADVICE_Q.search(s) and re.search(_AR_ROOTS, s) and _AR_ANSWER_RX.search(nxt):
                add("answer to a decision question (AR)")
        if _AZ_DIRECTIVE.search(variant):
            add("directive phrasing (Arabizi)")
        for c in _clauses(variant):
            if _IMPERATIVE_RX.search(c) and not _NEUTRAL_DISJ.search(c):
                add("imperative decision verb (EN)")
                break
        for s in _sentences(variant):
            if _COUNTERFACTUAL.search(s) and _DECISION_TERMS.search(s):
                add("advice framing (counterfactual/roleplay) with a decision")
            if _RECO_NOT_HAPPEN.search(s) and _RECO_WORDS.search(s):
                add("recommendation that the marriage not go ahead")
            for m in _JUDGEMENT.finditer(s):
                if not _NEG_EN.search(m.group(0)) or _POSITIVE_EVAL.search(m.group(0)):
                    add("judgement of the marriage decision")
        if _MULTILINGUAL.search(variant):
            add("directive phrasing (other language / transliteration)")
    for c in _clauses(text) + _sentences(text):
        neutral = _NEUTRAL_DISJ.search(c) and _AR_NEG_ADVICE.search(c)
        for i, rx in enumerate(DIRECTIVE_AR):
            if rx.search(c) and not (neutral and i == 0):
                add(f"directive phrasing (AR family {i})")
    return list({v["detail"]: v for v in out}.values())


# ----------------------------------------------------------------------------------------- uae_law
# Fed. Law 11/2008 (donated gametes/embryos); Fed. Law 7/2019 (PGT-M needs written consent of both
# spouses); Art. 16 Medical Liability Law / Cabinet Res. 44/2024 (fetal anomaly -> MFM + counselor, no
# advice). Statute wording per docs/01 P-16; anything beyond it TODO(verify).
_GAMETE = r"(?:sperm|semen|eggs?|ova|ovum|oocytes?|embryos?|gametes?|zygotes?)"
DONOR_EN = [
    re.compile(rf"\b(?:donors?(?:['’]s|s['’])?|donated|donating|donations?)\b[^.]{{0,30}}?\b{_GAMETE}\b|\b{_GAMETE}\b[^.]{{0,30}}?\bdon(?:or|ors|ated|ation|ations|ating)\b", re.I),
    re.compile(r"\b(?:donated|donation|donor)[-\s](?:conceived|conception|ivf|insemination|cycle|program\w*|bank)\b", re.I),
    re.compile(rf"\b{_GAMETE}\b[^.]{{0,20}}?\bfrom\s+(?:another|a\s+different|other|someone|somebody|an?\s+(?:anonymous|unknown|unrelated)|"
               r"(?:a|your|her|his|my|their)\s+(?:friend|relative|stranger|bank|man|woman|couple|third|sister|brother|cousin|aunt|uncle|"
               r"mother|father|niece|nephew|neighbou?r|colleague|sister-in-law|brother-in-law))\b", re.I),
    re.compile(rf"\b(?:someone|somebody|another\s+(?:man|woman|person|couple)|a\s+stranger|a\s+friend|a\s+relative|other\s+(?:people|couples|women|men))"
               rf"(?:['’]s|s['’])?\s+(?:\w+\s+)?{_GAMETE}", re.I),
    re.compile(r"\bembryos?\s+(?:adoption|donation|sharing|transfer\s+from\s+another)|\badopt\w*\s+(?:an?\s+|the\s+|surplus\s+|spare\s+|donated\s+)?embryos?|"
               r"\b(?:egg|sperm|embryo|oocyte)\s+(?:sharing|bank\w*|swap\w*|exchange)|\b(?:surplus|spare|leftover)\s+embryos?\b|"
               r"\bthird[-\s]party\s+(?:reproduction|conception|gametes?|eggs?|sperm|ivf)", re.I),
]
_GAMETE_AR = r"(?:بويض\w*|البويض\w*|حيوان\w*\s+منوي\w*|الحيوانات\s+المنوية|نطف\w*|النطف\w*|نطاف|السائل\s+المنوي|أجن\w*|الأجن\w*|اجن\w*|جنين\w*|الجنين|لقائح|اللقائح|لقيحة)"
DONOR_AR = [
    re.compile(rf"{_GAMETE_AR}[^.!؟?\n]{{0,25}}?(?:من\s+(?:امرأة|إمرأة|رجل|زوجين|شخص|سيدة|متبرع\w*|بنك|غير\w*|أخرى|اخرى|آخر)|متبرع\w*|مُتبرع\w*|تبرع\w*|التبرع)"),
    re.compile(rf"(?:متبرع\w*|المتبرع\w*|التبرع|تبرع\w*|بنك)[^.!؟?\n]{{0,25}}?{_GAMETE_AR}"),
    re.compile(r"(?:تبني|تبنّي|التبني)\s+(?:ال)?(?:أجن|اجن|جنين|لقائح|لقيحة)\w*"),
]
# P4 (BUG-QA-9) donor concept families without the word "donor": a third person's gametes (possessive or "from"),
# third-party providers, a relative giving gametes, clinic-abroad framings, Arabizi, MSA/Gulf construct state.
_SPOUSE_POSSESSOR = re.compile(r"^(?:your|my|our|his|her|their|husbands?|wife|wives|partners?|spouses?|fianc\w*|own|couples?|bride|groom)$", re.I)
_POSSESSIVE_GAMETE = re.compile(rf"\b([A-Za-z][\w-]*)['’]s?\s+(?:own\s+|\w+\s+)?{_GAMETE}\b", re.I)
_THIRD_PARTY_EN = (r"(?:cousins?|sisters?|brothers?|aunts?|uncles?|nieces?|nephews?|relatives?|friends?|neighbou?rs?|strangers?|"
                   r"colleagues?|in-?laws?|sister-in-law|brother-in-law|mother|father|another\s+(?:man|woman|person|couple)|"
                   r"other\s+(?:man|woman|men|women|people|couples?)|someone\s+else|somebody\s+else|"
                   r"unrelated\s+(?:man|woman|person)|volunteers?|contributors?|third[-\s]part(?:y|ies)|"
                   r"surrogate\w*|gestational\s+carriers?|outside\s+(?:source|person))")
DONOR_EN_P4 = [
    re.compile(rf"\b{_THIRD_PARTY_EN}\b[^.]{{0,60}}?\b{_GAMETE}\b|\b{_GAMETE}\b[^.]{{0,60}}?\b{_THIRD_PARTY_EN}\b", re.I),
    re.compile(r"\b(?:sperm|semen|eggs?|oocytes?|ova)\s+(?:from|of)\s+(?:a|an|another|some)\s+(?:\w+\s+){0,2}?non[-\s]?carriers?\b", re.I),
    re.compile(rf"\b(?:contribut\w*|provid\w*|suppl\w*|lend\w*|giv\w*|gift\w*|shar\w*|offer\w*)\b[^.]{{0,30}}?\b(?:some\s+of\s+)?(?:her|his|their)\s+{_GAMETE}\b", re.I),
    re.compile(rf"\b(?:abroad|overseas|outside\s+(?:the\s+)?(?:uae|emirates|country)|another\s+country|other\s+countries|(?:clinic|centre|center)s?\s+in\s+"
               rf"(?:\w+\s+){{0,2}}?where)\b[^.]{{0,80}}?\b(?:{_GAMETE}|donor\w*|donat\w*|(?:allowed|legal|permitted|possible)\s+there)\b|"
               rf"\b(?:{_GAMETE}|donor\w*|donat\w*)\b[^.]{{0,80}}?\b(?:abroad|overseas|outside\s+(?:the\s+)?(?:uae|emirates|country)|another\s+country)\b", re.I),
]
_REPRO_CONTEXT = re.compile(r"\b(?:ivf|icsi|iui|fertility|conceiv\w*|concept\w*|insemination|pregnan\w*|baby|treatment|clinic|gametes?|sperm|eggs?|embryos?)\b", re.I)
_DONOR_WORD = re.compile(r"\b(?:donor\w*|donat\w*|bank)\b", re.I)
_GAMETE_AZ = r"(?:b[ou]?wa?[iy]d\w*|bouwayd\w*|bwayd\w*|nit?a?f\b|nutaf|[7h]ayawa?n(?:at)?\s+manaw?i\w*|ajinn?a|ajenn?a|ajen+a)"
_DONOR_AZ = re.compile(rf"\b(?:mutabarr?[ie]3\w*|motabarr?e3\w*|tabarr?o?u?3\w*|tabaru3|mitbarr?3\w*)\b[^.]{{0,40}}?\b{_GAMETE_AZ}|\b{_GAMETE_AZ}[^.]{{0,40}}?"
                       r"\b(?:mutabarr?[ie]3\w*|motabarr?e3\w*|tabarr?o?u?3\w*|tabaru3|min\s+(?:wa?7da|wahda|imra2a|emra2a|mara|rajjal|rajul|ukht\w*|okht\w*|bank))", re.I)
_THIRD_PARTY_AR = (r"(?:امرأة|إمرأة|امراة|مرأة|سيدة|حرمة|رجل|رجال|ريال|أخت\w*|اخت\w*|أخو\w*|اخو\w*|خالت\w*|عمت\w*|بنت\s+(?:عم|خال)\w*|ابن\s+(?:عم|خال)\w*|"
                   r"قريب\w*|صديق\w*|جار\w*|شخص|غريب\w*|متبرع\w*|آخر|أخرى|اخرى|ثاني|ثانية|غير\s+حامل\w*|غيرك|غيرها|غيره)")
DONOR_AR_P4 = [
    re.compile(rf"{_GAMETE_AR}(?:\s+\S+){{0,2}}?\s+{_THIRD_PARTY_AR}(?![ء-ي])"),
    re.compile(r"(?:بنوك|بنك)\s+(?:ال)?(?:حيوانات|نطف|بويضات|أجنة|اجنة|مني)"),
    re.compile(rf"(?:في\s+الخارج|بالخارج|برا\s+(?:الدولة|البلد|الإمارات)|خارج\s+(?:الدولة|البلاد|الإمارات)|دولة\s+(?:ثانية|أخرى|اخرى))"
               rf"[^.!؟?\n]{{0,60}}?(?:{_GAMETE_AR}|متبرع\w*|تبرع\w*|مسموح|يسمح|قانوني)|(?:{_GAMETE_AR}|متبرع\w*|تبرع\w*)[^.!؟?\n]{{0,60}}?"
               r"(?:في\s+الخارج|بالخارج|برا\s+(?:الدولة|البلد)|خارج\s+(?:الدولة|البلاد|الإمارات))"),
]


def _donor_p4(text: str) -> bool:
    for m in _POSSESSIVE_GAMETE.finditer(text):
        if not _SPOUSE_POSSESSOR.match(m.group(1)):
            return True  # "a relative's eggs", "another man's sperm", "a non-carrier's sperm"
    if any(rx.search(text) for rx in DONOR_EN_P4 + DONOR_AR_P4) or _DONOR_AZ.search(text):
        return True
    if re.search(r"\b(?:use|uses|using|used|get|getting|go\s+with|choose|choosing|try|trying|find|finding|pick)\s+(?:a|an|the|their)\s+"
                 r"(?:\w+\s+)?donor\b(?!\s+(?:card|blood|organ))", text, re.I):
        return True
    return bool(_DONOR_WORD.search(text) and re.search(r"\bdonor\w*|\bdonat\w*", text, re.I) and _REPRO_CONTEXT.search(text))


PGTM_RX = re.compile(r"\bPGT(?:[-\s]?M)?\b|\bPGD\b|pre[-\s]?implantation\s+(?:genetic|diagnos|test)|embryo\s+(?:testing|screening|selection|biopsy)|"
                     r"(?:ال|لل|بال|وال|ل)?(?:فحص|تشخيص|اختبار)\s+(?:ال)?(?:جيني|وراثي)\s+(?:لل|ال)?(?:أجنة\s+)?(?:قبل|السابق\s+لل)\s*(?:ال)?"
                     r"(?:زرع|زراعة|انغراس|غرس|إرجاع)|فحص\s+(?:ال)?أجنة|"
                     # P4 (BUG-QA-9): PGT-M described without the acronym
                     r"\bembryos?\s+(?:\w+\s+){0,2}?(?:test\w*|screen\w*|select\w*|biops\w*|analys\w*|check\w*|diagnos\w*)|"
                     r"\b(?:test\w*|screen\w*|check\w*|analys\w*|biops\w*|diagnos\w*)\s+(?:of\s+|on\s+|the\s+|your\s+|each\s+)*embryos?\b|"
                     r"(?:فحص|تحليل|اختبار|تشخيص)\s+(?:\S+\s+){0,2}?(?:لل|ال)?(?:أجن|اجن)\w*|(?:الأجنة|الاجنة|أجنة|اجنة)\s+(?:\S+\s+)?(?:فحص|تحليل|اختيار|انتقاء)", re.I)
BOTH_CONSENT_RX = re.compile(
    r"written\s+consent\s+(?:of|from|by)\s+both\s+(?:spouses|partners)|both\s+(?:spouses|partners)[^.]{0,60}?written\s+consent|"
    r"both\s+(?:spouses|partners)\s+(?:must|need\s+to|have\s+to)\s+(?:sign|consent\s+in\s+writing)|"
    r"موافقة\s+(?:خطية|كتابية|مكتوبة)\s+(?:من\s+)?(?:كلا\s+)?الزوجين|موافقة\s+الزوجين\s+(?:الخطية|الكتابية|المكتوبة)", re.I)
_CONSENT_BYPASS = re.compile(
    r"\b(?:verbal|oral|spoken|implied|informal|tacit)\s+(?:consent|agreement|approval|ok)\b|"
    r"\b(?:consent|agreement|approval|signature)\s+(?:of|from|by)\s+(?:one|either|only\s+one|just\s+one|the\s+(?:wife|husband|woman|man|mother|father))\b(?!\s+and)|"
    r"\b(?:only|just)\s+(?:the\s+)?(?:wife|husband|one\s+(?:spouse|partner)|one\s+of\s+you)\b[^.]{0,30}?(?:consent|sign|agree)|"
    r"\bwithout\s+(?:the\s+|your\s+)?(?:husband|wife|spouse|partner|his|her)\b[^.]{0,25}?(?:consent|knowing|knowledge|signature|agreement)|"
    r"\b(?:no|don['’]t\s+need|do\s+not\s+need|without\s+(?:any\s+)?)\s+(?:written\s+)?(?:consent|signature|paperwork)|"
    r"الموافقة\s+(?:الشفهية|الشفوية|الضمنية)|موافقة\s+(?:شفهية|شفوية)|موافقة\s+(?:الزوجة|الزوج|أحد\s+الزوجين|طرف\s+واحد)\s*(?:فقط|وحده|وحدها|كافية|تكفي)|"
    r"بدون\s+(?:موافقة|علم|توقيع)\s+(?:الزوج|الزوجة|زوجك|زوجتك)|(?:كافية|يكفي|تكفي|كافي)|"
    # P4 (BUG-QA-9): starting on a single signature
    r"\b(?:one|a\s+single|single|just\s+one|only\s+one|just\s+your|only\s+your|your\s+own|his|her)\s+(?:\w+\s+)?signature\b(?!\s+and)|"
    r"\bsignature\s+(?:alone|only)\b|\bsign\w*\s+(?:it\s+|the\s+form\s+)?(?:alone|by\s+yourself|on\s+your\s+own|for\s+(?:both|the\s+two)\s+of\s+you)\b|"
    r"توقيع\s+(?:واحد|أحد|احد)|توقيعك\s+(?:فقط|وحده|بس)|بتوقيعك|توقيع\s+(?:الزوجة|الزوج)\s+(?:فقط|وحده|بس)|توقعي\s+(?:وحدك|بروحك)|توقع\s+(?:وحدك|بروحك)", re.I)
_PGT_ACTION = re.compile(r"\b(?:start|begin|book|schedule|arrange|undergo|go\s+ahead|proceed|sign\s+up|enrol\w*|request|order|apply|referr\w*|refer|"
                         r"next\s+step|today|tomorrow|now|this\s+(?:week|month)|next\s+(?:week|month|cycle)|cycle|just|simply|go\s+for|get\s+it|do\s+it|"
                         r"you\s+can\s+(?:have|do|get|start)|we\s+(?:will|can|['’]ll)\s+(?:start|book|arrange|refer|do))\b|"
                         r"ابدأ|ابدئي|احجز|احجزي|سجل|نبدأ|سنبدأ|الخطوة\s+التالية|اليوم|غدا|غداً|الآن", re.I)
_PGT_NEUTRAL = re.compile(r"\b(?:option|options|discuss\w*|counsel\w*|explain\w*|information|learn|ask\s+about|one\s+of|choices?)\b|"
                          r"خيار|خيارات|مناقشة|المستشار|يشرح|معلومات", re.I)
_PRENATAL_EN = re.compile(r"\b(?:fetal|foetal|fetus\w*|foetus\w*|unborn|nuchal|amnio\w*|chorionic\s+villus|cvs|ultrasound\w*|sonogra\w*|"
                          r"anomaly\s+scan|anatomy\s+scan|nipt|cell[-\s]free\s+dna|scan)\b", re.I)
_FINDING_EN = re.compile(r"\b(?:anomal\w*|abnormal\w*|malformation\w*|defect\w*|chromosom\w*|problem\w*|finding\w*|shows?|showed|suggest\w*|"
                         r"results?|means|positive|affected|condition|syndrome|marker\w*|thick\w*|likely|probably|fine|normal|concern\w*|"
                         r"decide|decision|weeks?|days?|found|detected)\b", re.I)
_TERMINATION_EN = re.compile(
    r"\b(?:terminat\w*|abort\w*|d\s*&\s*c|dilat\w*\s+and\s+(?:curettage|evacuation)|curettage|evacuation\s+of\s+(?:the\s+)?(?:uterus|pregnancy)|"
    r"end(?:ing)?\s+(?:the\s+|this\s+|your\s+|a\s+)?pregnan\w*|(?:continue|keep|discontinue|stop|interrupt)\w*\s+(?:with\s+)?(?:the\s+|this\s+|your\s+)?pregnan\w*|"
    r"(?:keep|lose)\s+the\s+baby|get\s+rid\s+of\s+(?:it|the\s+(?:baby|pregnancy|fetus))|medical\s+termination|mtp)\b", re.I)
_ANOMALY_EN = re.compile(r"\b(?:fetal|foetal)\s+(?:anomal\w*|abnormal\w*|malformation\w*|defect\w*)|\bbirth\s+defects?\b|"
                         r"\bchromosomal\s+(?:problem|abnormalit\w*|condition|disorder|anomal\w*|issue)\b", re.I)
_GEST_EN = re.compile(r"\bgestation\w*|\bweeks?\s+(?:pregnant|of\s+pregnancy|gestation)|\b\d+\s*(?:weeks?|days?)\b|"
                      r"\b(?:before|after|until|by)\s+(?:the\s+)?(?:\w+\s+){0,2}(?:days?|weeks?|deadline|limit)\b|\bdeadline\b|\bcut[-\s]?off\b|\b(?:time|legal)\s+limit\b", re.I)
_GEST_STRONG = re.compile(r"\bgestation\w*|\bweeks?\s+(?:pregnant|of\s+pregnancy)|عمر\s+الحمل", re.I)
_PREG_CONTEXT = re.compile(r"pregnan\w*|fetus|foetus|fetal|foetal|baby|terminat\w*|abort\w*|حمل|الحمل|جنين|الجنين|إجهاض|اجهاض", re.I)
_TERMINATION_AR = re.compile(r"جه(?:ا)?ض|(?:إنهاء|انهاء|إيقاف|ايقاف|وقف)\s+(?:ال)?حمل|إسقاط|اسقاط|تنزيل\s+(?:ال)?(?:جنين|حمل)|"
                             r"(?:ال)?تخلص\s+من\s+(?:ال)?(?:جنين|حمل)|(?:تكملي|تكمل|إكمال|اكمال|استمرار|الاستمرار|تستمري|تستمر)\s+(?:في\s+|ب)?(?:ال)?حمل")
_PRENATAL_AR = re.compile(r"(?:ال)?جنين|السونار|سونار|الموجات\s+فوق\s+الصوتية|الأشعة\s+الصوتية|الاشعة\s+الصوتية|بزل|السلى|الزغابات|الشفافية\s+القفوية")
_FINDING_AR = re.compile(r"تشوه\w*|عيب|عيوب|شذوذ|مشكل\w*|مصاب\w*|غير\s+طبيعي\w*|يظهر|أظهر\w*|اظهر\w*|تشير|يشير|نتيج\w*|كروموسوم\w*|صبغي\w*|"
                         r"متلازمة|سليم\w*|طبيعي\w*|أسبوع|اسبوع|يوم")
_GEST_AR = re.compile(r"عمر\s+الحمل|(?:قبل|بعد|حتى)\s+\d+\s*(?:يوم\w*|أسبوع\w*|اسبوع\w*|أسابيع)|\d+\s*(?:يوم\w*|أسبوع\w*|اسبوع\w*|أسابيع)|"
                      r"(?:قبل|بعد)\s+(?:الأربعين|الاربعين|مائة\s+وعشرين|مئة\s+وعشرين)")

# P4 (BUG-QA-12/8): termination by drug name or pill framing, pronoun termination in a pregnancy context, Gulf n-z-l /
# s-q-t verbs with a pregnancy object, Arabizi, anomaly reassurance in Gulf Arabic, gestational limits as number words.
_TERM_DRUG = re.compile(
    r"\b(?:misoprostol|mifepristone|cytotec|ru[-\s]?486|mifeprex|arthrotec|abortion\s+pills?|abortifacient\w*)\b|"
    r"\b(?:pills?|tablets?|medication|medicine|drugs?|injection|herbs?|tea)\b[^.]{0,60}?\b(?:end|stop|terminate|bring\s+on|induce|cause|trigger|"
    r"get\s+rid|interrupt|flush|empty)\b|\b(?:induc\w*|caus\w*|bring\w*\s+on|trigger\w*|provok\w*)\s+(?:a\s+)?(?:miscarriage|abortion|bleeding|"
    r"period|early\s+labou?r)|ميزوبروستول|سايتوتك|سايتوتيك|سيتوتك|(?:حبوب|حبة|دواء|أدوية|ابرة|إبرة)\s+(?:ال)?(?:إجهاض|اجهاض|تنزيل|تسقيط|إسقاط|اسقاط|مجهض\w*)|"
    r"\bseytotek\b|\bsaytotek\b", re.I)
_PRONOUN_TERM = re.compile(r"\b(?:end|stop|interrupt|terminate|not\s+keep|lose|get\s+rid\s+of)\s+(?:it|this\s+one|things)\b(?:\s+(?:early|now|soon|quickly|before))?|"
                           r"\bplan\s+to\s+end\b|\b(?:keep|continue)\s+(?:it|going)\s+(?:if|unless|only\s+if)\b", re.I)
_PREG_CONTEXT_EN = re.compile(r"\b(?:pregnan\w*|expecting|fetus\w*|foetus\w*|fetal|foetal|unborn|baby|scan|ultrasound|amnio\w*|cvs|nipt|weeks?\s+along)\b", re.I)
_TERM_AR_P4 = re.compile(r"(?:ت|ي|ن|أ|ا)?(?:نز|سق|نزز)ّ?(?:ل|ط)\w*[^.!؟?\n]{0,25}?(?:الجنين|جنين|الحمل|حمل|البيبي|بيبي|الولد|اللي\s+في\s+بطن\w*)|"
                         r"(?:الجنين|جنين|الحمل|البيبي|اللي\s+في\s+بطن\w*)[^.!؟?\n]{0,25}?(?:ت|ي|ن|أ|ا)?(?:نز|سق)ّ?(?:ل|ط)\w*|"
                         r"(?:تخلص|تتخلص|تخلصي|نتخلص)\w*\s+من(?:ه|ها)?(?=[^.!؟?\n]{0,40}(?:حمل|جنين|بيبي|بطن))")
_TERM_AZ = re.compile(r"\b(?:a?jhad\w*|i?jhaa?d\w*|tjah?d\w*|ajhed\w*|ejhad\w*|i?sqat\w*|esqat\w*|t?nazz?l\w*|nazz?l\w*|takhallas\w*|tkhallas\w*|t5alas\w*)\b"
                      r"[^.]{0,30}?\b(?:(?:el|al|il)[\s-]?)?(?:ja['’2]?n[ie]+n|jn[ie]+n|[7h]aml|baby|bebe|beibi)\b|\b(?:ijhaa?d|ejhaa?d|ajhad)\b|"
                      r"\b(?:gabl|qabl|ga?bel|ba3d|ba3ad|7atta|hatta|lain|lein)\s+(?:el\s+|al\s+)?(?:\w+\s+)?(?:shhoor|shuhoor|shohoor|ashhur|ash7or|"
                      r"asabee3|asabi3|isboo3|esbo3|usbu3|osboo3)\b", re.I)
_PRENATAL_AR_P4 = re.compile(r"البيبي|الأشعة\s+التلفزيونية|التلفزيون(?:ية)?|الأشعة|السونار|الجنين|\b(?:el|al)[\s-]?(?:sonar|janeen|janin|bebe|ashe33a|ash3a)\b", re.I)
_FINDING_AR_P4 = re.compile(r"عادي|طلع\w*|بسيط\w*|زين|زينة|تمام|ما\s+عليه|مو\s+مشكلة|مب\s+مشكلة|شي|شيء|ملاحظ\w*|\b(?:3adi|tamam|zain|zein|salim|ma\s+fi\s+shi|mafi\s+shi)\b", re.I)
_EN_NUMWORD = (r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
               r"nineteen|twenty(?:[\s-]\w+)?|thirty|forty)")
_EN_ORDWORD = (r"(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|\w+teenth|twentieth|"
               r"twenty[\s-]\w+|thirtieth|fortieth)")
_GEST_P4 = re.compile(rf"\bweek\s+{_EN_NUMWORD}\b|\b{_EN_ORDWORD}\s+week\b", re.I)
_GEST_NUM_P4 = re.compile(rf"\b{_EN_NUMWORD}\s+(?:weeks?|months?)\b", re.I)
_GEST_LIMIT_WORDS = re.compile(r"\b(?:decide|decision|deadline|limit|legal|allowed|permitted|cut[-\s]?off|too\s+late|latest|until|before|after|by|"
                               r"within|terminat\w*|end\w*|option)\b", re.I)
_AR_NUMWORD = r"(?:\d+|" + "|".join(sorted(_AR_NUMBER_WORDS, key=len, reverse=True)) + r"|العشرين|الثامن\s+عشر|الثاني\s+عشر|الرابع|الخامس|الثالث)"
_GEST_AR_P4 = re.compile(rf"(?:الأسبوع|أسبوع|اسبوع|الاسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور)\s+(?:ال)?{_AR_NUMWORD}|{_AR_NUMWORD}\s+(?:أسابيع|اسابيع|أسبوع\w*|اسبوع\w*|أشهر|اشهر|شهور)")
_GEST_AR_LIMIT = re.compile(r"قبل|بعد|حتى|خلال|لين|إلى|الى|تقرر\w*|القرار|مسموح|يسمح|الحد|آخر|اخر|حمل|الحمل|جنين|الجنين")


def _fetal_p4(text: str) -> bool:
    if _TERM_DRUG.search(text) or _TERM_AR_P4.search(text) or _TERM_AZ.search(text):
        return True
    if _PREG_CONTEXT_EN.search(text) and _PRONOUN_TERM.search(text):
        return True
    for s in _sentences(text):
        if _PRENATAL_AR_P4.search(s) and (_FINDING_AR_P4.search(s) or _FINDING_AR.search(s)):
            return True
        if _GEST_P4.search(s) and (_GEST_LIMIT_WORDS.search(s) or _PREG_CONTEXT.search(text)):
            return True
        if _GEST_NUM_P4.search(s) and (_PREG_CONTEXT.search(text) or re.search(
                r"\b(?:decide|decision|deadline|limit|legal|allowed|permitted|cut[-\s]?off|too\s+late|latest)\b", s, re.I)):
            return True
        if _GEST_AR_P4.search(s) and _GEST_AR_LIMIT.search(s):
            return True
    return False


def _check_uae(text: str) -> list[dict]:
    out: list[dict] = []
    variants = _variants(text)
    if any(rx.search(v) for v in variants for rx in DONOR_EN + DONOR_AR) or any(_donor_p4(v) for v in variants):
        out.append({"rule": "uae_law", "detail": "donor or third-party gametes/embryos are not an option under UAE law (Fed. Law 11/2008)"})
    if PGTM_RX.search(text):
        both = BOTH_CONSENT_RX.search(text)
        bypass = _CONSENT_BYPASS.search(text)
        pgt_sents = [s for s in _sentences(text) if PGTM_RX.search(s)] or [text]
        action = any(_PGT_ACTION.search(s) for s in pgt_sents)
        neutral = all(_PGT_NEUTRAL.search(s) for s in pgt_sents)
        if bypass or (not both and (action or not neutral)):
            out.append({"rule": "uae_law", "detail": "PGT-M step without the written consent of both spouses (Fed. Law 7/2019)"})
    fetal = any(_fetal_p4(v) for v in variants)
    for v in variants:
        if _TERMINATION_EN.search(v) or _TERMINATION_AR.search(v) or _ANOMALY_EN.search(v) or _GEST_STRONG.search(v):
            fetal = True
        for s in _sentences(v):
            if (_PRENATAL_EN.search(s) and _FINDING_EN.search(s)) or (_PRENATAL_AR.search(s) and _FINDING_AR.search(s)):
                fetal = True
        if _PREG_CONTEXT.search(v) and (_GEST_EN.search(FIXED_PHRASES[0].sub(" ", v)) or _GEST_AR.search(v)):
            fetal = True
    if fetal:
        out.append({"rule": "uae_law", "detail": f"{FETAL_ROUTE}: fetal-anomaly/termination/gestational content; route to licensed "
                                                 "MFM physician + accredited genetic counselor, no advice"})
    return out


# ------------------------------------------------------------------------- judicial statement (P-14)
JUDICIAL_RX = [
    re.compile(r"certificate[^.]{0,160}?regardless|regardless[^.]{0,160}?certificate", re.I),
    re.compile(r"الشهادة[^.]{0,160}?(?:بغض\s+النظر|بصرف\s+النظر|مهما\s+كانت)|(?:بغض\s+النظر|بصرف\s+النظر)[^.]{0,160}?الشهادة"),
]
# P4 (BUG-QA-15): accept the semantic family of the P-14 statement, sentence-local: certificate + "independent of the
# result" (regardless / either way / whatever / does not depend on / is not withheld ...). A contrary statement in the
# same message (certificate withheld, conditional, depends on the result) always fails.
_CERT_EN = re.compile(r"\bcertificat\w*", re.I)
_CERT_INDEP_EN = re.compile(
    r"\b(?:regardless|irrespective|no\s+matter|whatever|whichever|either\s+way|in\s+(?:any|every|all)\s+cases?|in\s+any\s+event|anyway|"
    r"independent\w*\s+of|whether\s+or\s+not|whether\s+(?:the|your)\s+results?)\b|"
    r"\b(?:does|do|will)\s+not\s+(?:\w+\s+){0,2}?(?:depend\w*|change|affect\w*)|\b(?:doesn['’]t|don['’]t|won['’]t)\s+(?:\w+\s+){0,2}?(?:depend\w*|change|affect\w*)|"
    r"\b(?:is|are)\s+not\s+(?:\w+\s+)?(?:affected|conditional|tied|linked|based|withheld|blocked|refused|denied|dependent|contingent)\b|"
    r"\b(?:isn['’]t|aren['’]t)\s+(?:\w+\s+)?(?:affected|conditional|tied|linked|based|withheld|blocked|refused|denied|dependent|contingent)\b|"
    r"\bnot\s+(?:conditional|dependent|contingent)\s+on\b", re.I)
_CERT_CONTRARY_EN = re.compile(
    r"\bcertificat\w*[^.]{0,80}?\b(?:not|never|n['’]t)\s+(?:be\s+)?(?:issued|granted|given|sent|released|valid)\b|"
    r"\bcertificat\w*[^.]{0,80}?(?<!not\s)(?<!n't\s)(?<!n’t\s)\b(?:depends?|conditional|contingent)\s+on\b|"
    r"\bcertificat\w*[^.]{0,80}?\b(?:only\s+(?:if|when|after)|unless|provided\s+that|on\s+condition)\b|"
    r"\bcertificat\w*[^.]{0,60}?(?<!not\s)(?<!n't\s)(?<!n’t\s)\b(?:be\s+|is\s+|are\s+|gets?\s+)?(?:withheld|denied|refused|blocked|revoked)\b", re.I)
_CERT_AR = re.compile(r"(?:ال)?شهاد\w*")
_CERT_INDEP_AR = re.compile(
    r"بغض\s+النظر|بصرف\s+النظر|مهما|أيا\s+كانت|أياً\s+كانت|أيًا\s+كانت|كيفما|في\s+(?:كل|جميع)\s+(?:الأحوال|الحالات)|على\s+أي\s+حال|بأي\s+حال|سواء|"
    r"(?:لا|لن|ما)\s+(?:\S+\s+)?(?:تعتمد|يعتمد|تتوقف|يتوقف|تتأثر|يتأثر|ترتبط|يرتبط|تحجب|تُحجب|يحجب|تمنع|يمنع)|غير\s+مرتبط\w*|غير\s+متوقف\w*|مستقل\w*\s+عن")
_CERT_CONTRARY_AR = re.compile(r"(?:ال)?شهاد\w*[^.!؟]{0,60}?(?:(?:لا|لن|ما)\s+(?:\S+\s+)?(?:تصدر|يصدر|تُصدر|تمنح|تُمنح)(?![^.!؟]{0,40}(?:بغض|بصرف|مهما))|"
                               r"إلا\s+إذا|فقط\s+إذا|بشرط|(?<!لا\s)(?<!لن\s)(?<!ما\s)(?:تعتمد|تتوقف)\s+على)")


def _judicial_ok(text: str) -> bool:
    if _CERT_CONTRARY_EN.search(text) or _CERT_CONTRARY_AR.search(text):
        return False
    if any(rx.search(text) for rx in JUDICIAL_RX):
        return True
    for s in _sentences(text):
        if (_CERT_EN.search(s) and _CERT_INDEP_EN.search(s)) or (_CERT_AR.search(s) and _CERT_INDEP_AR.search(s)):
            return True
    return False


# ------------------------------------------------------------------------------------ stigma (P-17)
_PEJ = (r"(?:ruin\w*|destroy\w*|poison\w*|weaken\w*|degrad\w*|spoil\w*|mistake|shameful|shame|irresponsible|selfish|sinful|sin|reckless|foolish|stupid|wrong|bad|dangerous|unnatural|backward|"
        r"primitive|ignorant|uneducated|outdated|archaic|disgusting|dirty|tainted|polluted|cursed|broken|defective|damaged|faulty|"
        r"rotten|corrupt\w*|contaminated|weak|inferior|abnormal|deformed|freak\w*|retarded|degenerate|fault|blame\w*|crime|taboo|"
        r"curse|disgrace\w*|uncivili[sz]ed|barbaric|tribal\s+nonsense)")
_CONS = (r"(?:cousins?|consanguin\w*|relatives?|kin|related\s+(?:couples?|marriages?|unions?|partners?)|famil(?:y|ies)\s+marriages?|"
         r"marr(?:y|ying|iage)\s+(?:a\s+|your\s+|to\s+a\s+)?(?:relatives?|cousins?|within\s+the\s+family|in\s+the\s+family|kin)|"
         r"tribal\s+marriages?|endogam\w*|tribes?|clans?|in-?family|within\s+(?:the|your|their)\s+(?:family|tribe|clan)|"
         r"keep\w*\s+it\s+in\s+the\s+family|marrying\s+in|intermarr\w*|bloodlines?|lineage)")
_PEJ_RX = re.compile(rf"\b{_PEJ}\b", re.I)
_CONS_RX = re.compile(rf"\b{_CONS}\b", re.I)
_GENE_PEJ = re.compile(r"\b(?:genes?|dna|blood|bloodline|lineage|famil(?:y|ies)['’]?s?|genetics?|chromosomes?|stock|seed)\b(?:\s+\w+){0,3}?\s+"
                       r"(?:dirty|broken|bad|defective|tainted|polluted|rotten|damaged|faulty|corrupt\w*|contaminated|weak|inferior|cursed|"
                       r"poisoned|sick|diseased|impure|dodgy)\b|\b(?:dirty|broken|bad|defective|tainted|polluted|rotten|damaged|faulty|"
                       r"corrupt\w*|contaminated|weak|inferior|cursed|poisoned|impure|sick)\s+(?:genes?|dna|blood|bloodline|lineage|genetics)\b", re.I)
STIGMA = [
    re.compile(r"\bin-?bre(?:d|ed|eds|eding|eders?)\b(?!\s+coefficients?)", re.I),  # F is a technical term (P-03)
    re.compile(r"\byou\s+(?:have|has|['’]ve\s+got|got|suffer\s+from|are\s+suffering\s+from)\s+(?:the|this|a)\s+(?:disease|illness|disorder|condition)\b|"
               r"\bcarriers?\s+(?:are|is)\s+(?:also\s+)?(?:sick|ill|diseased|patients?|affected|defective)\b|"
               r"\b(?:because|since)\s+you\s+(?:are|['’]re)\s+a\s+carrier\b|\byou\s+(?:are|['’]re)\s+(?:sick|ill|diseased|defective|broken|abnormal)\b", re.I),
    re.compile(r"\b(?:children|child|baby|babies|kids|offspring|sons?|daughters?)\b[^.]{0,30}?\b(?:will\s+be|would\s+be|are\s+going\s+to\s+be|be\s+born|"
               r"turn\s+out|come\s+out)\s+(?:\w+\s+)?(?:abnormal|deformed|defective|disabled|retarded|freaks?|monsters?|damaged|sick|cursed|"
               r"handicapped|crippled|broken|not\s+normal)\b", re.I),
    re.compile(r"\b(?:it\s+is|it['’]s|that\s+is|that['’]s|this\s+is)?\s*(?:all\s+)?(?:your|their|his|her)\s+(?:own\s+)?fault\b|"
               r"\byou(?:['’]re|\s+are)\s+(?:the\s+ones?\s+)?to\s+blame\b|\bblame\s+(?:yourselves|yourself|your\s+(?:family|parents|tribe))", re.I),
]
_AR_GENE_PEJ = re.compile(r"(?:جين|جينات|الجينات|جيناتها|جيناتكم|جيناتك|جيناته|دم|دمك|دمكم|دمهم|دماء|عرق|سلال\w*|نسل\w*|الحمض\s+النووي)"
                          r"(?:\s+\w+){0,2}?\s*(?:فاسد|ملوث|سيئ|سيئة|معيب|خرب|خربان|ناقص|مريض|قذر|وسخ|نجس|ضعيف|ضعيفة|ملعون)\w*")
_AR_PEJ = r"(?:خطأ|خطا|خاطئ|معيب|ناقص|مشوه|معاق|متخلف|رجعي|جاهل|جاهلة|عار|العار|ذنب|الذنب|ذنبك|ذنبكم|خطيئة|غلط|غلطة|غلطتك|غلطتكم|خطؤك|خطأك|مصيبة|لعنة|ملعون|عيب|فضيحة|سيئ|سيئة)\w*"
_AR_CONS = r"(?:أقارب|الأقارب|اقارب|القرابة|القبيلة|قبيلة\w*|داخل\s+(?:ال)?(?:عائلة|عايلة)|نفس\s+العائلة|بنت\s+عمك|ولد\s+عمك|"
_AR_CONS += r"ابن\s+عم\w*|بنت\s+عم\w*|ابن\s+خال\w*|بنت\s+خال\w*|بنات\s+العم|الحامل|حامل\w*|تحمل|الجين|أطفال\w*|الأطفال|أولاد\w*|عيال\w*|تزوجت|زواجك)"
_AR_PEJ_RX = re.compile(_AR_PEJ)
STIGMA_AR = [
    _AR_GENE_PEJ,
    re.compile(rf"(?<!صحيح أو )(?<!صح أو ){_AR_PEJ}[^.!؟?\n]{{0,35}}?{_AR_CONS}|{_AR_CONS}[^.!؟?\n]{{0,35}}?(?<!صحيح أو )(?<!صح أو ){_AR_PEJ}"),
    re.compile(r"(?:الحامل|حامل\w*|يحمل|تحمل)[^.!؟?\n]{0,20}?(?:مريض|مصاب|معيب)\w*"),
    re.compile(r"(?:الذنب|ذنبك|ذنبكم|غلطتك|غلطتكم|خطؤك|خطأك|بسببك|بسببكم|اللوم\s+عليك\w*)"),
]


# P4 (BUG-QA-14) stigma families: in-family/tribe marriage blamed for illness, moral-cost framings ("price/punishment of"),
# goods/lineage defects, blaming couples for clinic load, bloodline-purity sayings, Arabizi, Gulf/MSA offspring outcomes.
_CONS_P4 = (r"(?:tribe|tribal|clan|in-?family|within\s+(?:the|your|their)\s+(?:family|tribe|clan)|in\s+the\s+family|keep\w*\s+it\s+in\s+the\s+family|"
            r"marrying\s+in|intermarr\w*|same\s+(?:family|tribe|bloodline|clan)|bloodlines?|lineage|close\s+kin|kinship|"
            r"cousins?|consanguin\w*|relatives?|related\s+(?:couples?|marriages?|unions?))")
_CAUSAL_BLAME = re.compile(rf"\b{_CONS_P4}\b[^.]{{0,80}}?\b(?:is|are|was|were)\s+(?:\w+\s+)?(?:why|the\s+reason|to\s+blame|responsible)\b[^.]{{0,60}}?"
                           r"\b(?:sick|ill|disease\w*|disabled|defect\w*|affected|suffer\w*|problems?|die|dying|died)\b|"
                           rf"\b(?:sick|ill|disabled|defective|affected|suffering)\s+(?:\w+\s+){{0,3}}?(?:because\s+of|due\s+to|thanks\s+to|from)\s+"
                           rf"(?:\w+\s+){{0,3}}?{_CONS_P4}\b", re.I)
_MORAL_COST = re.compile(rf"\b(?:price|punishment|penalty|payback|karma|curse|toll|wages)\s+(?:of|for)\s+(?:\w+\s+){{0,3}}?{_CONS_P4}|"
                         rf"\b{_CONS_P4}\b[^.]{{0,40}}?\b(?:price|punishment|penalty|payback|karma|curse)\b|"
                         rf"\bcost\s+of\s+(?:marrying|keeping|being)\b[^.]{{0,30}}?{_CONS_P4}", re.I)
_GOODS_LINEAGE = re.compile(
    r"\b(?:damaged|spoiled|soiled|defective|faulty|broken|second[-\s]rate)\s+goods\b|"
    r"\b(?:defect\w*|flaw\w*|stain\w*|taint\w*|curse\w*|rot|sickness|disease|weakness|poison)\s+(?:(?:that\s+)?(?:runs?|running|carried|passed|"
    r"spreading|flowing)\s+)?(?:in|on|of|through|within|down)\s+(?:your|the|their|his|her)\s+"
    r"(?:lineage|bloodline|blood|family|line|genes|stock|tribe|family\s+tree|seed|ancestry)\b|"
    r"\b(?:lineage|bloodline|family\s+(?:tree|line)|ancestry|stock|seed|tribe|clan)\b(?:\s+\w+){0,3}?\s+(?:spoiled|rotten|defective|flawed|"
    r"ruined|degenerat\w*|unclean|cursed|poisoned|tainted|polluted|damaged|broken|weak|sick|corrupt\w*|impure)\b|"
    r"\bbad\s+seed\b|\bmix\w*\s+(?:the\s+)?blood\b|\b(?:pure|purity\s+of\s+the)\s+blood\w*|\bkeep\w*\s+the\s+blood\w*\s+(?:pure|clean)\b|"
    r"\bbackward\w*\s+and\s+ignoran\w*|\bignoran\w*\s+and\s+backward\w*", re.I)
_BLAME_LOAD = re.compile(r"\b(?:(?:couples?|people|families|carriers?)\s+like\s+(?:you|yours)|you(?:\s+two)?|related\s+couples|cousin\s+couples)\s+"
                         r"(?:are|is)\s+(?:the\s+)?(?:why|reason|reasons|to\s+blame|responsible)\b[^.]{0,50}?\b(?:clinics?|hospitals?|wards?|"
                         r"system|full|crowded|busy|overwhelmed|waiting\s+lists?|queues?|costs?|sick|ill)\b", re.I)
_BURDEN = re.compile(r"\b(?:burden\w*|strain\w*|drain\w*|overwhelm\w*|overload\w*|clog\w*|swamp\w*|crowding|crowd\w*\s+(?:out|the))\b[^.]{0,60}?"
                     r"\b(?:clinics?|hospitals?|health(?:care)?\s+(?:system|services)|the\s+system|society|resources|taxpayers?|the\s+state|the\s+country)\b|"
                     r"\b(?:clinics?|hospitals?|health(?:care)?\s+(?:system|services)|society|taxpayers?)\b[^.]{0,60}?\b(?:because\s+of|thanks\s+to|due\s+to)\s+"
                     r"(?:you|couples?\s+like\s+you|people\s+like\s+you|families\s+like\s+yours?|carriers?|related\s+couples|cousin\s+couples)\b", re.I)
_AZ_GENE_PEJ = re.compile(
    r"\b(?:jin+at\w*|jeenat\w*|genat\w*|jenat\w*|dam+[ak]\b|dammak\w*|dammek\w*|nasl\w*|3ir?q\w*|sulal\w*)\b(?:\s+\w+){0,2}?\s+"
    r"(?:kh?arban\w*|5arban\w*|khirban\w*|fas[ie]?d\w*|mal?wath\w*|m?3a?yoob\w*|m3eeb\w*|naqis\w*|na2es\w*|wase5\w*|wasikh\w*|"
    r"mareedh?\w*|marid\w*|broken|bad|sick|damaged|spoiled|rotten)\b", re.I)
_AR_CAUSE_SICK = (r"(?:يجيب|تجيب|يجيبون|يسبب|تسبب|يسببون|ينتج|ينتج\s+عنه|يخلف|يخلّف|يعطي|يعطيك|يؤدي\s+إلى|يؤدي\s+الى|يجلب)\s+"
                   r"(?:لل)?(?:عيال|أطفال|اطفال|أولاد|اولاد|ذرية|نسل|بزارين)\w*\s+(?:\S+\s+)?(?:مرضى|مريض\w*|معاق\w*|مشوه\w*|متخلف\w*|ناقص\w*|معلول\w*)")
_AR_OFFSPRING = r"(?:عيال|أطفال|اطفال|أولاد|اولاد|ذري|نسل|ذريت|نسلك|عيالك|أطفالك|أولادك)\w*"
STIGMA_AR_P4 = [
    re.compile(_AR_CAUSE_SICK),
    re.compile(rf"{_AR_OFFSPRING}[^.!؟?\n]{{0,30}}?(?:يطلع\w*|تطلع\w*|يكون\w*|يجون|يجو|يولد\w*|بيطلع\w*|يصير\w*|راح\s+يكون\w*)\s+(?:\S+\s+)?"
               r"(?:مرضى|مريض\w*|معاق\w*|مشوه\w*|متخلف\w*|ناقص\w*|(?:مو|مب|مش|غير)\s+طبيعي\w*|معلول\w*|خربان\w*)"),
    re.compile(r"(?:عقاب|عقوبة|جزاء|ثمن|ضريبة|لعنة|حصاد)\s+(?:\S+\s+)?(?:زواج\s+(?:ال)?أقارب|القرابة|الأقارب|اقارب|(?:الزواج|زواج)\s+(?:من\s+)?(?:داخل\s+)?(?:ال)?(?:عائلة|عايلة|قبيلة)|"
               r"داخل\s+(?:ال)?(?:عائلة|عايلة|قبيلة)|القبيلة)"),
    re.compile(r"(?:جين|جينات|الجينات|دم|دمك|دمكم|نسل\w*|سلال\w*)\w*(?:\s+\S+){0,2}?\s*(?:تالف|بايظ|بايض|مضروب|معطوب|عفن|متعفن|مسموم|خربان)\w*"),
    re.compile(rf"{_AR_OFFSPRING}[^.!؟?\n]{{0,20}}?(?:فيه|فيها|فيهم|عنده|عندها|عندهم|به|بها)\s+(?:خلل|علة|عله|نقص|تشوه|عيب)"),
    re.compile(r"(?:ال)?(?:تخلف|جهل|رجعية)\s+و\s*(?:ال)?(?:جهل|تخلف|رجعية)|(?:زواج\s+(?:ال)?أقارب|القرابة)[^.!؟?\n]{0,25}?(?:تخلف|جهل|رجعي\w*)"),
]


def _check_stigma(text: str) -> list[dict]:
    out: list[dict] = []
    for v in _variants(text):
        if _AZ_GENE_PEJ.search(v):
            out.append({"rule": "stigma", "detail": "pejorative framing of genes/family (Arabizi)"})
        for s in _sentences(v):
            for name, rx in (("blame", _CAUSAL_BLAME), ("moral cost", _MORAL_COST), ("lineage", _GOODS_LINEAGE), ("burden", _BURDEN), ("blame for load", _BLAME_LOAD)):
                m = rx.search(s)
                if m and not _negated_before(s, m.start(), 20):
                    out.append({"rule": "stigma", "detail": f"stigmatizing language (P4 {name})"})
            for i, rx in enumerate(STIGMA_AR_P4):
                m = rx.search(s)
                if m and not _NEG_AR.search(" " + s[max(0, m.start() - 8):m.start()]):
                    out.append({"rule": "stigma", "detail": f"stigmatizing language (AR P4 family {i})"})
            for m in _PEJ_RX.finditer(s):
                if _CONS_RX.search(s) and not _negated_before(s, m.start(), 30):
                    out.append({"rule": "stigma", "detail": "pejorative framing of consanguinity"})
                    break
            if _GENE_PEJ.search(s):
                out.append({"rule": "stigma", "detail": "pejorative framing of genes/family"})
            for i, rx in enumerate(STIGMA):
                m = rx.search(s)
                if m and not _negated_before(s, m.start(), 20):
                    out.append({"rule": "stigma", "detail": f"stigmatizing language (EN family {i})"})
            for i, rx in enumerate(STIGMA_AR):
                for m in rx.finditer(s):
                    # negation is checked right before the pejorative itself, wherever it sits in the match
                    pej = _AR_PEJ_RX.search(m.group(0)) if i == 1 else None
                    at = m.start() + (pej.start() if pej else 0)
                    if not _NEG_AR.search(" " + s[max(0, at - 8):at]):
                        out.append({"rule": "stigma", "detail": f"stigmatizing language (AR family {i})"})
                        break
    return list({v["detail"]: v for v in out}.values())


# --------------------------------------------------------------- false reassurance (DECISIONS #24)
_OFFSPRING = r"(?:children|child|baby|babies|kids|offspring|pregnancy|pregnancies|family|future\s+children|little\s+ones)"
REASSURE_EN = [
    re.compile(rf"\b{_OFFSPRING}\s+(?:are|is|will\s+be|would\s+be|['’]ll\s+be|should\s+be|are\s+going\s+to\s+be)\s+"
               r"(?:completely\s+|totally\s+|perfectly\s+|definitely\s+|certainly\s+|surely\s+|absolutely\s+|100%\s+|all\s+)?"
               r"(?:safe|fine|healthy|ok|okay|protected|unaffected|normal|in\s+the\s+clear|free\s+of|alright|all\s+right)\b", re.I),
    re.compile(r"\b(?:result|results|screen|screening|test|report|outcome)\s+(?:is|are|was|were|came\s+back|looks?)\s+"
               r"(?:completely\s+|totally\s+|all\s+|perfectly\s+)?(?:clear|clean|normal|fine|perfect|good|reassuring)\b", re.I),
    re.compile(r"\b(?:cleared|auto[-\s]?clear\w*|automatic(?:ally)?\s+clear\w*|all[-\s]clear|clean\s+bill)\b", re.I),
    re.compile(r"\b(?:almost|nearly|virtually|practically|most)?\s*(?:certainly|definitely|surely|undoubtedly|probably|likely|sure\s+to\s+be)\s+"
               r"(?:harmless|benign|fine|nothing|safe|ok|okay|innocent|irrelevant|not\s+(?:a\s+)?(?:problem|concern|an\s+issue|serious))\b", re.I),
    re.compile(r"\bharmless\b|\bnothing\s+to\s+(?:worry|fear)\b|\bno\s+(?:cause|reason)\s+(?:for|to)\s+(?:concern|worry)|\b(?:don['’]?t|do\s+not|no\s+need\s+to|not\s+to)\s+worry\b|"
               r"\brest\s+assured\b|\byou\s+can\s+relax\b|\byou['’]?re\s+(?:safe|fine|in\s+the\s+clear)\b|\bnothing\s+(?:is\s+)?wrong\b", re.I),
    re.compile(r"\b(?:no|without\s+(?:any\s+)?)\s+need\s+(?:for|of)\s+(?:a\s+|any\s+|further\s+|more\s+|another\s+)*(?:confirmatory\s+|follow[-\s]?up\s+|extra\s+|additional\s+|genetic\s+)?"
               r"(?:test\w*|check\w*|screen\w*|counsel\w*|appointment|review|follow[-\s]?up|specialist|doctor)", re.I),
    # discouraging, skipping or delaying counseling/testing (P-18). Always on: we never discourage it.
    re.compile(r"\b(?:no\s+need|(?:you\s+)?(?:don['’]?t|do\s+not|won['’]?t|will\s+not|needn['’]?t)\s+(?:really\s+|even\s+)?(?:need|have)|not\s+(?:necessary|needed|required)|unnecessary)\s+"
               r"(?:to\s+)?(?:(?:see|visit|book|attend|keep|have|get|do|take|go\s+to|talk\s+to|speak\s+(?:to|with)|meet|wait\s+for)\s+)?"
               r"(?:a\s+|the\s+|your\s+|any\s+|this\s+)?(?:genetic\s+|further\s+|confirmatory\s+|more\s+|another\s+|follow[-\s]?up\s+)*"
               r"(?:counsel\w*|appointment|test\w*|session|follow[-\s]?up|review|doctor|specialist|check\w*)", re.I),
    re.compile(r"\b(?:skip|cancel|postpone|delay|ignore|avoid|forget\s+about|miss|put\s+off|don['’]?t\s+bother\s+with|no\s+point\s+(?:in|to)|bypass)\s+(?:(?:seeing|going\s+to|booking|attending|getting|doing|having|keeping|see|go\s+to|book|attend|get|do|have|keep)\s+)?"
               r"(?:the\s+|your\s+|this\s+|that\s+|any\s+)?(?:genetic\s+|confirmatory\s+|follow[-\s]?up\s+)*(?:counsel\w*|appointment|test\w*|session|"
               r"follow[-\s]?up|review|referral|visit|specialist)", re.I),
]
_AR_TMN_VERB = re.compile(r"(?<![ء-ي])(?:و|ف)?(?:اطمئن|اطمن|تطمئن|تطمن|اطمأن|اطمنو)(?:ي|وا|و|ا|ين|ون)?(?![ء-ي])")
_AR_TMN_NOUN = re.compile(r"(?:يمكنك|يمكنكم|يمكنكما|تقدر|تقدرين|تقدرون|بإمكانك|بامكانك|لك|لكم|لكما|يدعو|تدعو|يبعث|تبعث)\w*\s+(?:على\s+|إلى\s+|الى\s+|لل|ل)?"
                          r"(?:ال)?اطمئنان")
_AR_TMN_BLOCKERS = re.compile(r"(?:قبل|دون|بدون|عدم|لا|لن|ليس|لم|ما|غير)\s+(?:\S+\s+)?$")


def _ar_tmn_reassurance(s: str) -> bool:
    for rx in (_AR_TMN_VERB, _AR_TMN_NOUN):
        for m in rx.finditer(s):
            if not _AR_TMN_BLOCKERS.search(s[max(0, m.start() - 20):m.start()]):
                return True
    return False


REASSURE_AR = [
    re.compile(r"(?:أطفال|الأطفال|أطفالكم|أطفالك|أولاد|أولادكم|عيال\w*|ذري\w*|الجنين|حملك|الحمل)\w*[^.؟!\n]{0,20}?"
               r"(?:في\s+أمان|بأمان|آمن\w*|امن\w*|سالم\w*|سليم\w*|بخير|لن\s+يصاب\w*|ما\s+راح\s+يصاب\w*|ما\s+عليهم|ما\s+فيهم\s+شي)"),
    re.compile(r"(?:لا\s+تقلق\w*|ما\s+في\s+(?:داعي\s+)?(?:خوف|قلق)|لا\s+داعي\s+للقلق|لا\s+داعي\s+للخوف|لا\s+تخاف\w*|لا\s+تخش\w*)"),
    re.compile(r"(?:غير\s+ضار\w*|غير\s+مؤذ\w*|لا\s+يضر|مافيه\s+شي|ما\s+فيه\s+شي|بدون\s+خطر|لا\s+خطر)"),
    re.compile(r"(?:النتيجة|نتيجتك|نتيجتكم|نتيجتكما|الفحص)\s+(?:\w+\s+)?(?:سليمة|سليم|نظيفة|طبيعية|ممتازة|خالية|مطمئنة)"),
    re.compile(r"(?<![ء-ي])(?:لا\s+داعي|لا\s+حاجة|ما\s+(?:في\s+)?داعي|لا\s+تحتاج\w*|ما\s+تحتاج\w*|مو\s+لازم|مش\s+لازم|"
               r"ليس\s+من\s+الضروري|غير\s+ضروري|بلاش|تجاهل\w*|أجّ?ل(?:ي|وا)?|ألغ(?:ي|وا)?|الغ(?:ي|وا)|فوّ?ت(?:ي|وا)?|تخطى|تخطي|تخطوا)"
               r"(?![ء-ي])[^.؟!\n]{0,25}?"
               r"(?:مراجع\w*|المستشار|مستشار|الاستشار\w*|استشار\w*|الموعد|موعد|فحص|الفحص|الطبيب|طبيب|الجلس\w*|جلس\w*|متابع\w*|التأكيد\w*)"),
    re.compile(r"(?:تم|تمت|تمّت)\s+(?:تبرئة|إخلاء|اخلاء|اعتماد|قبول|تصفية)\s*(?:\w+\s+)?(?:تلقائي\w*|آلي\w*)|(?:تلقائي\w*|آلي\w*)[^.؟!\n]{0,15}(?:سليم|بخير|مقبول)"),
]


# P4 (BUG-QA-10) families: guarantee verbs, "no reason to repeat", deferral of counseling/testing, tautologies
# ("negative means negative"), "nothing scary", "you don't have to come", Arabizi, Gulf "not necessary / after the wedding".
_CARE_EN = (r"(?:counsel\w*|appointment|test\w*|retest\w*|session|follow[-\s]?up|review|referral|visit|specialist|confirmatory|screen\w*|"
            r"check[-\s]?up|consultation|booking)")
_GUARANTEE_EN = re.compile(
    r"\b(?:guarantee\w*|promis\w*|assur(?:e|es|ed|ing)\b|ensures?\s+(?:that\s+)?(?:a\s+|your\s+)?(?:healthy|safe|normal)|"
    r"(?:can|may)\s+be\s+(?:sure|certain|confident)\s+(?:that\s+)?(?:\w+\s+){0,4}?(?:healthy|safe|fine|normal|ok|okay|unaffected|not\s+(?:a\s+)?carriers?)|"
    r"rul(?:e|es|ed)\s+(?:it|this|that|everything|any\s+risk)\s+out|rul(?:e|es|ed)\s+out\s+(?:any|all|the)\s+(?:risk|chance|possibility))", re.I)
_NO_REASON_EN = re.compile(rf"\bno\s+(?:reason|point|need|purpose|use)\s+(?:to|in|for)\s+(?:\w+\s+){{0,2}}?(?:repeat\w*|redo\w*|re-?do\w*|retest\w*|re-?check\w*|"
                           rf"{_CARE_EN}|confirm\w*|see\w*|book\w*|follow)", re.I)
_DEFER_EN = re.compile(
    r"\b(?:can|could|may)\s+(?:safely\s+|easily\s+|just\s+)?(?:wait|be\s+(?:left|postponed|delayed|skipped|ignored|put\s+off))\b|"
    r"\bwait\s+(?:until|till)\b|\b(?:until|till)\s+after\s+(?:the|your)\s+(?:wedding|marriage|honeymoon|nikah|holidays?)\b|"
    r"\bnext\s+(?:year|month|summer|winter|spring|autumn)\b|\b(?:another|some\s+other)\s+time\b|\blater\s+(?:on\s+)?(?:is|would\s+be)\s+(?:fine|ok|okay)\b|"
    r"\b(?:is|are)\s+(?:fine|ok|okay)\s+later\b|\bno\s+(?:rush|hurry)\b|\bnot\s+(?:urgent|important|a\s+priority)\b|\bformality\b|"
    r"\bcan\s+(?:safely\s+|just\s+)?(?:ignore|skip)\b|\bfeel\s+free\s+to\s+(?:skip|ignore|miss|leave|cancel|postpone|drop|forget)\b|"
    r"\b(?:is|are)\s+(?:\w+\s+)?optional\b|\bleft\s+for\s+(?:another|later|some)", re.I)
_DEFER_PRONOUN = re.compile(r"\bfeel\s+free\s+to\s+(?:skip|ignore|miss|cancel|postpone|drop|forget|leave)\s+(?:it|that|them)\b|"
                            r"\b(?:just|you\s+can)\s+(?:skip|ignore|cancel)\s+(?:it|that|them)\b", re.I)
_CARE_EN_RX = re.compile(rf"\b{_CARE_EN}\b", re.I)
_DONT_HAVE_TO = re.compile(r"\b(?:you\s+)?(?:don['’]?t|do\s+not|won['’]?t|will\s+not)\s+(?:really\s+|even\s+)?(?:have|need)\s+to\s+"
                           r"(?:come|go|attend|show\s+up|turn\s+up|keep\s+it|be\s+there|bother)\b", re.I)
_TAUTOLOGY_EN = re.compile(r"\b(?:a\s+)?(negative|clear|normal|clean)\s+(?:means|is|=)\s+(?:a\s+)?(?:negative|clear|normal|clean|safe|no\s+risk|nothing)\b", re.I)
_NOTHING_SCARY = re.compile(r"\bnothing\s+(?:scary|alarming|worrying|concerning|serious|bad|frightening|to\s+be\s+(?:scared|afraid|worried)\s+(?:of|about))\b", re.I)
REASSURE_AR_P4 = [
    re.compile(r"(?:تضمن|يضمن|نضمن|أضمن|اضمن|مضمون\w*|أؤكد\s+لك\w*|نؤكد\s+لك\w*)(?![ء-ي])"),
    re.compile(r"(?:مو|مش|مب|ما\s+هو|ماهو|ليس|غير)\s+(?:ضروري|لازم|مهم)|ما\s*له\s+داعي|ماله\s+داعي|ما\s*يحتاج|مايحتاج|ما\s+في\s+حاجة|مب\s+لازم|"
               r"لا\s+سبب\s+(?:ل|لإعادة|لاعادة)|ما\s+في\s+سبب"),
    re.compile(r"(?:بعد\s+(?:العرس|الزواج|الزفاف|الملكة|العيد|الصيف)|السنة\s+(?:الجاية|الجاي|القادمة)|العام\s+القادم|بعدين|لاحقا|لاحقاً|وقت\s+ثاني|"
               r"(?:مو|مش|مب)\s+مستعجل|ما\s+في\s+عجلة|لا\s+عجلة|شكلي\w*|مجرد\s+إجراء|اختياري\w*|أجّ?ل\w*|اجل\w*|تأجيل|خلّ?(?:ها|يه|وها|يها)\s+بعدين)"
               r"[^.؟!\n]{0,40}?(?:موعد|الموعد|فحص|الفحص|المستشار|مستشار|الاستشار\w*|جلس\w*|مراجع\w*|التأكيد\w*|تأكيد\w*|متابع\w*)|"
               r"(?:موعد|الموعد|فحص|الفحص|المستشار|الاستشار\w*|جلس\w*|مراجع\w*|التأكيد\w*|متابع\w*)[^.؟!\n]{0,40}?"
               r"(?:بعد\s+(?:العرس|الزواج|الزفاف|الملكة)|السنة\s+(?:الجاية|القادمة)|بعدين|لاحقا|لاحقاً|وقت\s+ثاني|(?:مو|مش|مب)\s+مستعجل|شكلي\w*|اختياري\w*)"),
    re.compile(r"ما\s*(?:في|فيه|فيها|فيش)?\s*(?:أي\s+|اي\s+|ولا\s+)?(?:شي|شيء|اشي)\s+(?:يخوف|يخوّف|يقلق|مخيف|يدعو\s+للقلق)|لا\s+يوجد\s+ما\s+يدعو\s+(?:لل)?(?:قلق|خوف)|"
               r"(?:نتيجت\w*|الفحص|النتيجة)\s+ما\s+فيها?\s+(?:شي|شيء)"),
]
REASSURE_AZ = [
    re.compile(r"\b(?:ma\s*f(?:i|ee)|mafi|mafee|la|mo|mu|mesh|mish|mb|mob|mub)\s+(?:a?y\s+)?(?:da3i|da3ee|7aja|haja|7aje|lazem|lazim|daroori|daruri)\b[^.]{0,40}?"
               r"(?:must?a?shar\w*|mostashar\w*|counsel\w*|maw3[ie]d|mo3ed|fa7s|fahs|test|doctor|daktor|tabeeb|tabib|appointment|t?roo?[7h]\w*|t?ru[7h]\w*)", re.I),
    re.compile(r"\b(?:ma\s*f(?:i|ee)|mafi|mafee|bdoon|bidoon|bedoon|la)\s+(?:a?y\s+)?(?:khatar|5atar|khatr|5atr)\b|"
               r"\b(?:kol+(?:shi|shay|o|u)|kollo|kulshi)\s+(?:tamam|zain|zein|zen|mzyan|fine|ok|salim|sale?em)\b|"
               r"\bla\s+t(?:kha|5a)f\w*|\bla\s+teg?la2\w*|\bla\s+tqla2\w*|\bma\s+fi\s+shi\s+(?:y5awef|ykhawef|ykhawwif)\b", re.I),
]


_CARE_AR_RX = re.compile(r"موعد|فحص|المستشار|مستشار|استشار\w*|الاستشار\w*|جلس\w*|مراجع\w*|تأكيد\w*|التأكيد\w*|متابع\w*|الطبيب|طبيب|تعيد|إعادة|اعادة")


def _reassurance_p4(s: str) -> list[str]:
    hits = []
    m = _GUARANTEE_EN.search(s)
    if m and not _negated_before(s, m.start(), 20):
        hits.append("guarantee")
    if _NO_REASON_EN.search(s):
        hits.append("no reason to repeat/attend")
    if (_CARE_EN_RX.search(s) and _DEFER_EN.search(s)) or _DEFER_PRONOUN.search(s):
        hits.append("deferral of counseling/testing")
    if _DONT_HAVE_TO.search(s) or _TAUTOLOGY_EN.search(s) or _NOTHING_SCARY.search(s):
        hits.append("dismissal")
    g = REASSURE_AR_P4[0].search(s)
    if g and not _NEG_AR.search(" " + s[max(0, g.start() - 8):g.start()]):
        hits.append("AR guarantee")
    if REASSURE_AR_P4[1].search(s) and _CARE_AR_RX.search(s):
        hits.append("AR not necessary")
    if any(rx.search(s) for rx in REASSURE_AR_P4[2:] + REASSURE_AZ):
        hits.append("AR/Arabizi")
    return hits


def _check_reassurance(text: str, ctx: GateContext) -> list[dict]:
    out = []
    for v in _variants(text):
        for s in _sentences(v):
            for h in _reassurance_p4(s):
                out.append({"rule": "false_reassurance", "detail": f"absolute reassurance or discouraging care (P4 {h})"})
            for i, rx in enumerate(REASSURE_EN):
                m = rx.search(s)
                if m and not (i in (0, 1, 4) and _negated_before(s, m.start(), 20)):
                    out.append({"rule": "false_reassurance", "detail": f"absolute reassurance or discouraging care (EN family {i})"})
            if _ar_tmn_reassurance(s):
                out.append({"rule": "false_reassurance", "detail": "absolute reassurance (AR be-reassured verb / asserted reassurance)"})
            for i, rx in enumerate(REASSURE_AR):
                if rx.search(s):
                    out.append({"rule": "false_reassurance", "detail": f"absolute reassurance or discouraging care (AR family {i})"})
        if _ZERO_CLAIMS.search(v):
            out.append({"rule": "false_reassurance", "detail": "absolute reassurance (no risk)"})
    return list({v["detail"]: v for v in out}.values())


# ------------------------------------------------------------------------------------------- entry
def _check(draft: str, ctx: GateContext) -> GateResult:
    if not isinstance(draft, str):
        raise TypeError("draft must be str")
    text = normalize(draft)
    violations: list[dict] = []
    violations += _check_numbers(text, list(ctx.locked_records or []))
    violations += _check_leakage(text, ctx)
    violations += _check_partner_status(text, ctx)
    violations += _check_directive(text)
    violations += _check_uae(text)
    if ctx.kind != "result" and (_CERT_CONTRARY_EN.search(text) or _CERT_CONTRARY_AR.search(text)):
        violations.append({"rule": "missing_judicial_statement",
                           "detail": "statement contradicts P-14 (certificate is issued regardless of the result)"})
    elif ctx.kind == "result" and not _judicial_ok(text):
        violations.append({"rule": "missing_judicial_statement",
                           "detail": "result message must state the health certificate is issued regardless (P-14)"})
    violations += _check_stigma(text)
    violations += _check_reassurance(text, ctx)
    return GateResult(passed=not violations, violations=violations)


def check(draft: str, ctx: GateContext | dict) -> GateResult:
    """Run all gate rules. Fail closed: any exception yields passed=False with a gate_error violation."""
    try:
        return _check(draft, GateContext.coerce(ctx))
    except Exception as exc:  # noqa: BLE001 - fail closed by design
        return GateResult(passed=False, violations=[{"rule": GATE_ERROR, "detail": type(exc).__name__}])
