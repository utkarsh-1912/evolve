"""Arabic display siblings (DECISIONS #48): built in lock() from the same Fraction, rounded once, same number."""
import hashlib
import json

import pytest

from conftest import AR_SIBLINGS, assert_ar_parity, assert_schema_valid, call, couple
from risk_engine import assess_couple, discordant, lock

SMN1, CYP, MEFV = 11117, 2600, 6998


def _smn1_cousins():
    return lock(discordant("0.013", "0.92", "1/8"), gene="SMN1", hgnc_id=SMN1, audience="carrier_partner_only",
                carrier_role="A", reference_unrelated=discordant("0.013", "0.92", 0))


def test_exact_arabic_strings_v3():
    o = _smn1_cousins()
    assert_schema_valid([o])
    assert o["offspring_risk_one_in_ar"] == "1 من كل 321"
    assert o["posterior_carrier_b_one_in_ar"] == "1 من كل 80.2"
    assert o["reference_unrelated_one_in_ar"] == "1 من كل 3,800"  # Western digits, ',' separator like EN
    assert o["relative_to_unrelated_display_ar"] == "حوالي 12 ضعفاً"


def test_arabic_fields_are_in_the_digest():
    o = _smn1_cousins()
    body = {k: v for k, v in o.items() if k != "digest"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == o["digest"]
    tampered = dict(body, offspring_risk_one_in_ar="1 من كل 50")
    assert hashlib.sha256(json.dumps(tampered, sort_keys=True).encode()).hexdigest() != o["digest"]


@pytest.mark.parametrize("c", [
    couple("unrelated", [call(CYP, "CYP21A2")], [], b_assays={str(CYP): "initial"}),       # R=0: relative null
    couple("unrelated", [call(CYP, "CYP21A2")], [], b_assays={str(CYP): "confirmatory"}),  # "1 in 3,380"
    couple("unrelated", [call(MEFV, "MEFV")], [], b_assays={str(MEFV): "initial"}),        # no number at all
    couple("first_cousins", [call(4827, "HBB")], [call(4827, "HBB")]),                    # concordant 1 in 4
])
def test_null_parity_and_same_number(c):
    out = assess_couple(c)
    assert_schema_valid(out)
    for o in out:
        assert_ar_parity(o)
        for en, (ar, _, _) in AR_SIBLINGS.items():
            if en in o:
                assert (o[en] is None) == (o[ar] is None)


def test_r0_relative_ar_is_null_and_numberless_record_has_null_ar():
    (o,) = assess_couple(couple("unrelated", [call(CYP, "CYP21A2")], [], b_assays={str(CYP): "initial"}))
    assert o["relative_to_unrelated_display_ar"] is None and o["reference_unrelated_one_in_ar"] == "1 من كل 426"
    (o,) = assess_couple(couple("unrelated", [call(MEFV, "MEFV")], [], b_assays={str(MEFV): "initial"}))
    assert o["offspring_risk_one_in_ar"] is None and "posterior_carrier_b_one_in_ar" not in o


def test_zero_risk_has_null_ar():
    o = lock(discordant(0, "0.92"), gene="SYNG1", hgnc_id=99999, audience="carrier_partner_only", carrier_role="A")
    assert o["offspring_risk_one_in"] is None and o["offspring_risk_one_in_ar"] is None
    assert_schema_valid([o])


def test_parity_checker_rejects_drift():
    o = dict(_smn1_cousins(), offspring_risk_one_in_ar="1 من كل 320")
    with pytest.raises(AssertionError):
        assert_ar_parity(o)
    o = dict(_smn1_cousins(), relative_to_unrelated_display_ar=None)
    with pytest.raises(AssertionError):
        assert_ar_parity(o)
