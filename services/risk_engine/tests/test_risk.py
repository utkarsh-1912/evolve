import json
import pathlib
import random
from fractions import Fraction

import pytest

from risk_engine import Path, concordant_negative, concordant_positive, discordant, lock, wright

VEC = json.loads((pathlib.Path(__file__).parents[3] / "tests/golden/risk_vectors.json").read_text())


@pytest.mark.parametrize("v", VEC["wright"], ids=lambda v: v["id"])
def test_wright_golden(v):
    f, r = wright(Path(n1, n2, fa) for n1, n2, fa in v["paths"])
    assert f == Fraction(v["F"]) and r == Fraction(v["R"])


@pytest.mark.parametrize("v", VEC["discordant"], ids=lambda v: v["id"])
def test_discordant_golden(v):
    res = discordant(v["q"], v["d"], v["r"])
# vectors are rounded to 3 significant figures, so compare at that precision
    assert float(res["prior_carrier_b"]) == pytest.approx(v["prior"], abs=1e-5)
    assert float(res["posterior_carrier_b"]) == pytest.approx(v["posterior"], abs=1e-5)
    assert float(1 / res["posterior_carrier_b"]) == pytest.approx(v["posterior_one_in"], rel=1e-3)
    assert float(1 / res["offspring_risk"]) == pytest.approx(v["offspring_one_in"], rel=1e-3)


def test_concordant_positive_is_quarter():
    assert concordant_positive()["offspring_risk"] == Fraction(1, 4)


def test_properties_random():
    rng = random.Random(7)
    for _ in range(2000):
        q = Fraction(rng.randint(1, 200), 1000)
        d = Fraction(rng.randint(0, 100), 100)
        r = rng.choice([Fraction(0), Fraction(1, 8), Fraction(1, 4)])
        res = discordant(q, d, r)
        prior, post = res["prior_carrier_b"], res["posterior_carrier_b"]
        assert 0 <= post <= 1 and post <= prior          # a negative test never raises risk
        if d == 1:
            assert post == 0                              # perfect assay
        if d == 0:
            assert post == prior                          # useless assay
        assert discordant(q, min(d + Fraction(1, 100), 1), r)["posterior_carrier_b"] <= post  # monotone in d


def test_concordant_negative_related_refuses_to_guess():
    res = concordant_negative("0.013", "0.92", r="1/8")
    assert res["status"] == "needs_counselor" and res["offspring_risk"] is None
    locked = lock(res, gene="SMN1", hgnc_id=11117)
    assert locked["escalate"] is True and locked["offspring_risk"] is None


def test_lock_is_deterministic_and_carries_digest():
    res = discordant("0.013", "0.92", "1/8")
    ref = discordant("0.013", "0.92", "0")
    a = lock(res, gene="SMN1", hgnc_id=11117, f=Fraction(1, 16), reference_unrelated=ref)
    b = lock(res, gene="SMN1", hgnc_id=11117, f=Fraction(1, 16), reference_unrelated=ref)
    assert a == b and len(a["digest"]) == 64
    assert a["offspring_risk_one_in"] == "1 in 321" and a["fusage"] == "genome_wide_context_only"
    assert 11 < a["relative_to_unrelated"] < 13


def test_input_validation():
    with pytest.raises(ValueError):
        discordant("1.5", "0.9")
    with pytest.raises(ValueError):
        wright([Path(0, 2)])
