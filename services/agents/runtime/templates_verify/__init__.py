"""Closed-template verification (DECISIONS #37, G2 a/b; TASK-P4-GATE). Owner: agent-runtime instance 2 (gate).

Patient-facing text is a closed set: CulturalCommunicator renders `templates.TEMPLATES` (EN + AR) with locked display
slots only, and the LLM paraphrase is hard-off (runtime/policy.py). This module verifies that closed set exhaustively:

  for every couple (V1-V5 + the full synthetic cohort), both partners, both languages, every draft kind the
  communicator can produce for that recipient (couple result, own explainer, escalations a/b/c/d/gate, disclosure):
    1. BioethicsSupervisor passes (the real gate, real GateContext from the real Runtime);
    2. an INDEPENDENT leakage oracle: no gene symbol / HGNC id / HGVS / condition name of the other partner (or, for
       couple-level text, of either partner) outside the consented intersection or an active disclosure;
    3. an INDEPENDENT partner-status oracle (non-interference): the recipient's texts are byte-identical to the texts
       they would get if the other partner carried nothing outside the intersection;
    4. an INDEPENDENT number oracle: every digit is part of a locked display string of the draft's own records (or the
       fixed "48 hours"); no number word other than "one";
    5. result (and private explainer) texts contain the locked judicial sentence (P-14) verbatim;
    6. every message the runtime actually delivered is exactly one of the enumerated template renders (closed set).

Nothing here computes a probability (P-02): numbers are compared as strings taken from locked records.
The held-out pass file that policy.py reads (holdout_pass.json) is written by qa-redteam only; it is NOT created here.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .. import _paths, templates

_paths.ensure()

LANGS = ("en", "ar")
ESCALATION_TRIGGERS = ("a", "b", "c", "d", "gate")
_PANEL = json.loads((_paths.ROOT / "contracts" / "gene_panel.json").read_text(encoding="utf-8"))["genes"]
_SYMBOLS = [g["symbol"] for g in _PANEL]
_AR_DIGITS = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_AR_DIGITS.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})
_EN_NUMBER_WORDS = re.compile(r"\b(?:zero|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|hundred|"
                              r"thousand|million|half|quarter|third|twice|dozen)\b", re.I)
_AR_NUMBER_WORDS = re.compile(r"(?<![ء-ي])(?:اثنان|اثنين|ثلاث\w*|أربع\w*|خمس\w*|ست\w*|سبع\w*|ثمان\w*|تسع\w*|عشر\w*|مئة|مائة|ألف|نصف|ربع|ثلث)(?![ء-ي])")


# ------------------------------------------------------------------------------------------- inventory
def inventory() -> list[dict]:
    """Every patient-facing template string: communicator templates (EN + AR), teach-back items (EN + AR) and the
    i18n reference copy behind API keys (EN; the UI owns other locales)."""
    out = []
    for lang, table in templates.TEMPLATES.items():
        for key, text in table.items():
            out.append({"source": "communicator", "lang": lang, "key": key, "text": text})
    for item in templates.TEACHBACK:
        for lang in LANGS:
            out.append({"source": "teachback", "lang": lang, "key": item["key"], "text": item.get(lang, item["en"])})
    for key, text in templates.I18N_EN.items():
        if key.startswith("teachback."):
            continue  # already listed as teach-back items
        out.append({"source": "i18n", "lang": "en", "key": key, "text": text})
    return out


def template_slots(text: str) -> set[str]:
    import string
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


# ------------------------------------------------------------------------------------------- oracles
def _panel_terms(hgnc_id: int) -> list[str]:
    for g in _PANEL:
        if g["hgnc_id"] == hgnc_id:
            names = [g["condition"]] + [p.strip() for p in re.split(r"[/()]", g["condition"]) if len(p.strip()) >= 4]
            return [g["symbol"], f"HGNC:{hgnc_id}"] + names
    return [f"HGNC:{hgnc_id}"]


def forbidden_strings(couple: dict, recipient_role: str, allowed_ids: set, *, couple_level: bool) -> list[str]:
    """Independent of runtime.forbidden_terms: built from the raw synthetic couple + contracts/gene_panel.json."""
    out = []
    for p in couple["partners"]:
        if p["role"] == recipient_role and not couple_level:
            continue
        for c in p.get("calls") or []:
            if c["hgnc_id"] in allowed_ids:
                continue
            out += _panel_terms(c["hgnc_id"]) + [c["gene"]] + [c[k] for k in ("hgvs_c", "hgvs_p") if c.get(k)]
    return sorted(set(out))


def leaked(text: str, terms: Iterable[str]) -> list[str]:
    hits = []
    for t in terms:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(t)}(?![A-Za-z0-9])", text, re.I):
            hits.append(t)
    return hits


def stray_numbers(text: str, records: list[dict]) -> list[str]:
    """Digits not inside a locked display string of the draft's own records; number words other than 'one'."""
    t = text.translate(_AR_DIGITS)
    # locked display strings: EN `*_one_in` / `*_display` and their AR siblings `*_one_in_ar` / `*_display_ar`, all produced
    # by risk_engine.lock() from the same value (DECISIONS #48, REQUEST-GATE-2)
    displays = sorted({v for r in records for k, v in r.items() if isinstance(v, str)
                       and k.endswith(("_one_in", "_display", "_one_in_ar", "_display_ar"))}, key=len, reverse=True)
    for d in displays:
        t = t.replace(d.translate(_AR_DIGITS), " ")
    t = re.sub(r"\b48\s+hours\b|48\s*ساعة", " ", t)
    # gene symbols carry digits (CYP21A2, SMN1); they are checked by the leakage oracle, not counted as numbers here
    for sym in sorted(_SYMBOLS, key=len, reverse=True):
        t = re.sub(rf"(?<![A-Za-z0-9]){re.escape(sym)}(?![A-Za-z0-9])", " ", t)
    t = re.sub(r"HGNC:\d+", " ", t)
    return re.findall(r"\d+", t) + _EN_NUMBER_WORDS.findall(t) + _AR_NUMBER_WORDS.findall(t)


# ------------------------------------------------------------------------------------------- enumeration
@dataclass
class Rendered:
    couple_id: str
    partner_id: str
    lang: str
    kind: str
    name: str
    text: str
    records: list
    couple_level: bool
    allowed_ids: set = field(default_factory=set)


@dataclass
class Report:
    combinations: int = 0
    couples: int = 0
    recipients: int = 0
    delivered_checked: int = 0
    failures: list = field(default_factory=list)

    def fail(self, r: Optional[Rendered], why: str) -> None:
        where = f"{r.couple_id}/{r.partner_id}/{r.lang}/{r.name}" if r else "-"
        self.failures.append(f"{where}: {why}")


def _consent_and_run(rt, couple: dict) -> dict:
    a, b = (p["partner_id"] for p in couple["partners"])
    rt.request_consent(a, b)
    rt.request_consent(b, a)
    return rt.run_compatibility(couple["couple_id"])


def _drafts_for(rt, couple: dict, pid: str, review: bool) -> list[tuple[str, object, bool]]:
    """Every draft the communicator can build for this recipient in the current runtime state: (name, Draft, couple_level)."""
    ws = rt.workspaces[couple["couple_id"]]
    ctx = rt.contexts[pid]
    shared_genes = sorted({r["gene"] for r in ws.records} | {rt._symbol(h) for h in ws.apsi["shared_hgnc_ids"]})
    out = []
    for lang in LANGS:
        cc = rt.communicator
        out.append((f"couple_result.{lang}", cc.couple_result(lang, compatible=bool(ws.apsi["compatible"]), shared_genes=shared_genes,
                                                              couple_records=list(ws.records), review_required=review), True))
        if ctx.records:
            complex_genes = {r["gene"] for r in ctx.records if rt.interpreter.is_complex(r["hgnc_id"])}
            out.append((f"own_explainer.{lang}", cc.own_explainer(lang, list(ctx.records), complex_genes), False))
        for t in ESCALATION_TRIGGERS:
            out.append((f"escalation_{t}.{lang}", cc.escalation(lang, t), False))
    return out


def _render_all(rt, couple: dict, response: dict) -> list[Rendered]:
    out = []
    ws = rt.workspaces[couple["couple_id"]]
    shared = set(ws.apsi["shared_hgnc_ids"])
    for p in couple["partners"]:
        pid = p["partner_id"]
        review = bool(response["review_required"].get(pid))
        for name, d, couple_level in _drafts_for(rt, couple, pid, review):
            out.append(Rendered(couple["couple_id"], pid, d.lang, d.kind, name, d.text, list(d.locked_records), couple_level,
                                shared | rt.disclosures.active_for_recipient(pid)))
    return out


def _check_rendered(rt, couple: dict, r: Rendered, rep: Report) -> None:
    from .. import bioethics
    rep.combinations += 1
    role = next(p["role"] for p in couple["partners"] if p["partner_id"] == r.partner_id)
    gctx = rt._gate_context(r.partner_id, r.lang, r.records, r.kind, couple_level=r.couple_level)
    res = bioethics.check(r.text, gctx)
    if not res.passed:
        rep.fail(r, f"gate blocked: {res.rules}")
    hits = leaked(r.text, forbidden_strings(couple, role, r.allowed_ids, couple_level=r.couple_level))
    if hits:
        rep.fail(r, f"leakage oracle: {len(hits)} forbidden term(s)")
    stray = stray_numbers(r.text, r.records)
    if stray:
        rep.fail(r, f"number oracle: unlocked number token(s) {stray}")
    if r.kind in ("result", "explainer") and r.name.split(".")[0] in ("couple_result", "own_explainer"):
        if templates.TEMPLATES[r.lang]["judicial"] not in r.text:
            rep.fail(r, "judicial sentence (P-14) missing")


def counterfactual(couple: dict, shared_ids: set, tag: str = "CF") -> dict:
    """Two twins of the couple, keyed by the recipient role they test: in twin[role] the OTHER partner keeps only
    their calls inside the APSI intersection. The recipient's texts must not change (non-interference, P-06)."""
    twins = {}
    for role in ("A", "B"):
        c = copy.deepcopy(couple)
        c["couple_id"] = f"{tag}{role}-{couple['couple_id']}"
        for p in c["partners"]:
            p["partner_id"] = f"{tag}{role}-{p['partner_id']}"
            if p["role"] != role:
                p["calls"] = [x for x in p.get("calls") or [] if x["hgnc_id"] in shared_ids]
        twins[role] = c
    return twins


def _texts_by_name(rendered: list[Rendered], pid: str) -> dict:
    return {r.name: r.text for r in rendered if r.partner_id == pid}


def verify_couples(rt, couples: list[dict], *, noninterference: bool = True, disclosure: bool = True) -> Report:
    """Run the real Runtime over `couples` (already added to rt) and verify every reachable template render."""
    rep = Report()
    for couple in couples:
        rep.couples += 1
        resp = _consent_and_run(rt, couple)
        rendered = _render_all(rt, couple, resp)
        for r in rendered:
            _check_rendered(rt, couple, r, rep)
        # 6. closed set: every delivered message equals one enumerated render for that recipient + language
        for p in couple["partners"]:
            pid = p["partner_id"]
            rep.recipients += 1
            allowed = {r.text for r in rendered if r.partner_id == pid}
            for m in rt.contexts[pid].messages:
                rep.delivered_checked += 1
                if m["text"] not in allowed:
                    rep.fail(None, f"{pid}: delivered message is not a template render")
            if any(c["trigger"] == "gate" for c in rt.cases.values() if c["couple_id"] == couple["couple_id"]):
                rep.fail(None, f"{couple['couple_id']}: a template draft was blocked by the gate (gate case opened)")
        # 3. non-interference against the counterfactual twin
        if noninterference:
            shared = set(rt.workspaces[couple["couple_id"]].apsi["shared_hgnc_ids"])
            for role, twin in counterfactual(couple, shared).items():
                rt.add_couple(twin)
                tresp = _consent_and_run(rt, twin)
                trend = _render_all(rt, twin, tresp)
                real_pid = next(p["partner_id"] for p in couple["partners"] if p["role"] == role)
                twin_pid = next(p["partner_id"] for p in twin["partners"] if p["role"] == role)
                real, cf = _texts_by_name(rendered, real_pid), _texts_by_name(trend, twin_pid)
                if real != cf:
                    diff = sorted(k for k in set(real) | set(cf) if real.get(k) != cf.get(k))
                    rep.fail(None, f"{couple['couple_id']}/{real_pid}: text depends on the partner's non-intersection data {diff}")
                real_msgs = [m["text"] for m in rt.contexts[real_pid].messages]
                twin_msgs = [m["text"] for m in rt.contexts[twin_pid].messages]
                if real_msgs != twin_msgs:
                    rep.fail(None, f"{couple['couple_id']}/{real_pid}: delivered messages depend on the partner's non-intersection data")
                rt._purge_couple(twin["couple_id"])
        # disclosure (DECISIONS #16): the carrier shares one own gene; the screen-negative partner's message is verified
        if disclosure:
            for p in couple["partners"]:
                for rec in list(rt.contexts[p["partner_id"]].records):
                    if not (rec["audience"] == "carrier_partner_only" and rec.get("carrier_role") == p["role"]
                            and rt.interpreter.is_complex(rec["hgnc_id"])):
                        continue  # disclose_gene accepts only the carrier's own complex-locus record
                    other = next(o for o in couple["partners"] if o["partner_id"] != p["partner_id"])
                    before = len(rt.contexts[other["partner_id"]].messages)
                    try:
                        rt.disclose_gene(p["partner_id"], rec["hgnc_id"])
                    except Exception as exc:  # noqa: BLE001 - an unreachable disclosure is reported, not hidden
                        rep.fail(None, f"{p['partner_id']}: disclosure not reachable ({type(exc).__name__})")
                        continue
                    allowed_ids = set(rt.workspaces[couple["couple_id"]].apsi["shared_hgnc_ids"]) | rt.disclosures.active_for_recipient(other["partner_id"])
                    for lang in LANGS:
                        d = rt.communicator.disclosure(lang, rec["gene"])
                        r = Rendered(couple["couple_id"], other["partner_id"], lang, d.kind, f"disclosure.{lang}", d.text, [], False, allowed_ids)
                        _check_rendered(rt, couple, r, rep)
                    for m in rt.contexts[other["partner_id"]].messages[before:]:
                        rep.delivered_checked += 1
                        if m["text"] not in {rt.communicator.disclosure(lg, rec["gene"]).text for lg in LANGS}:
                            rep.fail(None, f"{other['partner_id']}: delivered disclosure is not a template render")
    return rep


def verify_static_copy() -> Report:
    """Teach-back items and i18n reference copy: gate-clean with no locked record, no numbers, no gene or condition."""
    from .. import bioethics
    rep = Report()
    genes = [t for g in _PANEL for t in _panel_terms(g["hgnc_id"])]
    items = inventory()
    by_key = {(i["lang"], i["key"]): i["text"] for i in items}
    for item in items:
        if item["source"] == "communicator":
            continue
        if item["key"].startswith("care.option.") and item["key"].endswith(".title"):
            # an option card is displayed as title + body; verify it as displayed
            body = by_key.get((item["lang"], item["key"][: -len("title")] + "body"), "")
            item = dict(item, text=item["text"] + ". " + body)
        rep.combinations += 1
        ctx = bioethics.GateContext("STATIC", item["lang"], [], [], "care", counterpart_status_hidden=True, shared_hgnc_ids=[],
                                    escalation_required=True)
        res = bioethics.check(item["text"], ctx)
        r = Rendered("-", "-", item["lang"], "care", item["key"], item["text"], [], False)
        if not res.passed:
            rep.fail(r, f"gate blocked: {res.rules}")
        if leaked(item["text"], genes):
            rep.fail(r, "gene/condition in static copy")
        if stray_numbers(item["text"], []):
            rep.fail(r, "number in static copy")
    return rep
