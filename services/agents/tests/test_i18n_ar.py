"""Arabic copy checks (TASK-P4-AR-ARABIC) not covered by the template closure verifier: the AR i18n reference copy,
no English placeholder left, carrier vocabulary, TODO(native-review) markers. The gate is used as-is (not edited)."""
import pathlib
import re

import pytest

from runtime import bioethics, i18n_ar, templates
from runtime import templates_verify as tv

AR_LETTER = re.compile(r"[ء-ي]")
SOURCE = pathlib.Path(i18n_ar.__file__).read_text(encoding="utf-8")


def all_ar_strings():
    out = [("template", k, v) for k, v in templates.AR.items()]
    out += [("teachback", t["id"], t["ar"]) for t in templates.TEACHBACK]
    out += [("i18n", k, v) for k, v in templates.I18N_AR.items()]
    return out


@pytest.mark.parametrize("src,key,text", all_ar_strings())
def test_no_english_placeholder_left(src, key, text):
    assert AR_LETTER.search(text), (src, key)
    en = templates.EN.get(key) if src == "template" else templates.I18N_EN.get(key)
    assert text != en, (src, key)
    # Latin text allowed only for slots, gene symbols and the PGT-M acronym
    latin = re.sub(r"\{[a-z_]+\}|PGT-M", "", text)
    assert not re.search(r"[A-Za-z]{3,}", latin), (src, key)


def test_every_ar_string_marked_for_native_review():
    n_strings = len(i18n_ar.AR) + len(i18n_ar.TEACHBACK_AR) + len(i18n_ar.I18N_AR)
    assert SOURCE.count("# TODO(native-review)") >= n_strings


def test_carrier_vocabulary_never_bare_haamil():
    # "حامل" alone also means pregnant: carrier is always "حامل(اً) للتغيّر الجيني"
    for src, key, text in all_ar_strings():
        for m in re.finditer(r"(?<![ء-ي])(?:ال)?حامل\w*", text):
            tail = text[m.end():m.end() + 14]
            # "حامل للتغيّر" or the construct state "حاملي التغيّر" (carriers of the change)
            assert re.match(r"[ً-ْ]*\s*(?:للتغيّر|التغيّر)", tail), (src, key)


def _units(table):
    opts = {k.split(".")[2] for k in table if k.startswith("care.option.")}
    out = [(f"care.option.{o}", f"{table[f'care.option.{o}.title']} {table[f'care.option.{o}.body']}") for o in opts]
    return out + [(k, v) for k, v in table.items() if not k.startswith("care.option.")]


@pytest.mark.parametrize("key,text", _units(templates.I18N_AR))
def test_ar_i18n_copy_passes_gate_and_has_no_numbers(key, text):
    ctx = bioethics.GateContext("STATIC", "ar", [], [], "care", counterpart_status_hidden=True, shared_hgnc_ids=[],
                                escalation_required=False)
    res = bioethics.check(text, ctx)
    assert res.passed, (key, res.violations)
    assert tv.stray_numbers(text, []) == [], key


def test_judicial_sentence_is_gate_accepted_and_uses_regardless():
    j = templates.AR["judicial"]
    assert "الشهادة" in j and "بغض النظر" in j
    assert bioethics._judicial_ok(j)


# ---- DECISIONS #48: Arabic figures from the locked *_ar display strings (flag flips after REQUEST-GATE-2) ----
def _v3_records():
    import json
    import risk_engine
    from runtime._paths import ROOT
    c = json.loads((ROOT / "tests" / "golden" / "cohort" / "V3.json").read_text(encoding="utf-8"))["couples"][0]
    return risk_engine.assess_couple(c)


def test_ar_render_uses_locked_ar_display_when_enabled(monkeypatch):
    rec = _v3_records()[0]
    assert rec["offspring_risk_one_in_ar"] and rec["relative_to_unrelated_display_ar"]
    monkeypatch.setattr(templates, "AR_LOCKED_DISPLAY", True)
    text = templates.render("ar", "own_discordant_ok", record=rec, gene=rec["gene"]) + " " + \
        templates.render("ar", "own_relative", record=rec)
    for k in ("offspring_risk_one_in_ar", "posterior_carrier_b_one_in_ar", "reference_unrelated_one_in_ar",
              "relative_to_unrelated_display_ar"):
        assert rec[k] in text, k
    assert " in " not in text and "about" not in text  # no English figure embedded
    ctx = bioethics.GateContext("V3A", "ar", [rec], [], "explainer")
    assert bioethics.check(text + " " + templates.AR["judicial"], ctx).passed
    # EN is unaffected by the flag
    assert rec["offspring_risk_one_in"] in templates.render("en", "own_discordant_ok", record=rec, gene=rec["gene"])


def test_ar_render_falls_back_to_locked_en_display(monkeypatch):
    rec = _v3_records()[0]
    monkeypatch.setattr(templates, "AR_LOCKED_DISPLAY", False)
    assert rec["offspring_risk_one_in"] in templates.render("ar", "own_discordant_ok", record=rec, gene=rec["gene"])
    monkeypatch.setattr(templates, "AR_LOCKED_DISPLAY", True)
    old = {k: v for k, v in rec.items() if not k.endswith("_ar")}  # a record from before DECISIONS #48
    assert rec["offspring_risk_one_in"] in templates.render("ar", "own_discordant_ok", record=old, gene=rec["gene"])
