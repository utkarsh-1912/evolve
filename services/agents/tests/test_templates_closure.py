"""G2 (a), DECISIONS #37: exhaustive verification of the closed patient template set.

Every template x every reachable locked-record combination (V1-V5 + the full synthetic cohort, both partners, EN + AR,
couple result / own explainer / escalation a,b,c,d,gate / disclosure) through the REAL Runtime (real APSI, real
risk_engine, real BioethicsSupervisor; nothing mocked). Oracles live in runtime/templates_verify and are independent
of the gate: leakage terms from the raw couple + gene panel, non-interference against a counterfactual partner,
digits only inside locked display strings, the locked judicial sentence verbatim.
"""
import json
import string

import pytest

from runtime import templates, templates_verify as tv
from runtime._paths import ROOT
from runtime.orchestrator import Runtime, load_vignettes

COHORT = ROOT / "services" / "synth" / "out" / "cohort.json"


def test_inventory_is_complete_and_slot_safe():
    inv = tv.inventory()
    assert len(inv) == len(templates.EN) + len(templates.AR) + 2 * len(templates.TEACHBACK) + \
        len([k for k in templates.I18N_EN if not k.startswith("teachback.")])
    assert set(templates.AR) == set(templates.EN), "AR and EN template keys must match"
    for key in templates.EN:
        assert tv.template_slots(templates.EN[key]) == tv.template_slots(templates.AR[key]), key
    for item in inv:
        assert tv.template_slots(item["text"]) <= templates.ALLOWED_SLOTS, item["key"]
        if item["source"] != "communicator":
            assert not tv.template_slots(item["text"]), item["key"]
    # no template carries a risk number of its own (P-01): only the fixed "48 hours"
    for item in inv:
        literal = "".join(t for t, *_ in string.Formatter().parse(item["text"]))
        assert not tv.stray_numbers(literal, []), item["key"]


def test_static_copy_verified():
    rep = tv.verify_static_copy()
    assert rep.combinations > 0
    assert rep.failures == [], rep.failures


def test_vignettes_every_template_combination(authority):
    rt = Runtime(authority=authority)
    rep = tv.verify_couples(rt, load_vignettes())
    assert rep.couples == 5 and rep.combinations > 100
    assert rep.failures == [], rep.failures


def test_vignettes_arabic_delivery_is_closed(authority):
    """Same check with both partners' language set to AR, so delivered AR messages are compared too."""
    rt = Runtime(authority=authority)
    for c in load_vignettes():
        for p in c["partners"]:
            rt.set_lang(p["partner_id"], "ar")
    rep = tv.verify_couples(rt, load_vignettes(), noninterference=False)
    assert rep.delivered_checked > 0
    assert rep.failures == [], rep.failures
    for c in load_vignettes():
        for p in c["partners"]:
            assert all(m["lang"] == "ar" for m in rt.messages(p["partner_id"]))


@pytest.mark.slow  # ~10-14 min (3 real Runtime runs per couple); nightly CI: pytest -m slow
@pytest.mark.skipif(not COHORT.exists(), reason="synthetic cohort not generated (services/synth)")
def test_full_cohort_every_template_combination(authority):
    couples = json.loads(COHORT.read_text(encoding="utf-8"))["couples"]
    rt = Runtime(authority=authority)
    rt.reset(couples=couples)
    rep = tv.verify_couples(rt, couples)
    print(f"\n[templates_verify] cohort couples={rep.couples} combinations={rep.combinations} "
          f"delivered_checked={rep.delivered_checked} failures={len(rep.failures)}")
    assert rep.couples == len(couples)
    assert rep.failures == [], rep.failures[:50]


def test_oracles_catch_planted_violations(authority):
    """The oracles are not vacuous: planted leakage, a stray number and a missing judicial line are all reported."""
    rt = Runtime(authority=authority)
    v3 = next(c for c in load_vignettes() if c["couple_id"] == "V3")
    tv._consent_and_run(rt, v3)
    other_gene = next(c["gene"] for p in v3["partners"] if p["role"] == "A" for c in p["calls"])
    assert tv.leaked(f"About {other_gene}.", tv.forbidden_strings(v3, "B", set(), couple_level=False))
    assert tv.stray_numbers("The chance is 1 in 50.", []) == ["1", "50"]
    assert tv.stray_numbers("A counselor aims to call within 48 hours about SMN1.", []) == []
    rep = tv.Report()
    r = tv.Rendered("V3", "V3B", "en", "result", "couple_result.en", "Your couple screening result.", [], True)
    tv._check_rendered(rt, v3, r, rep)
    assert any("judicial" in f for f in rep.failures)
