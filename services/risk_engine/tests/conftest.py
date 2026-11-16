"""Shared helpers for risk_engine tests. Synthetic data only (P-11)."""
import json
import pathlib
import re

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
RISK_SCHEMA = json.loads((ROOT / "contracts" / "risk_output.schema.json").read_text(encoding="utf-8"))
COHORT_SCHEMA = json.loads((ROOT / "contracts" / "cohort.schema.json").read_text(encoding="utf-8"))
RISK_VALIDATOR = jsonschema.Draft202012Validator(RISK_SCHEMA)

PATHS = {
    "unrelated": [],
    "second_cousins": [[3, 3, "0"], [3, 3, "0"]],
    "first_cousins": [[2, 2, "0"], [2, 2, "0"]],
    "double_first_cousins": [[2, 2, "0"]] * 4,
}


def call(hgnc_id, gene, cls="P", zyg="het", roh=False, vtype="snv"):
    return {"hgnc_id": hgnc_id, "gene": gene, "hgvs_c": "c.SYN1A>G", "hgvs_p": None, "refseq": None,
            "zygosity": zyg, "classification": cls, "variant_type": vtype,
            "absent_gnomad": False, "absent_clinvar": False, "in_roh_gt_10mb": roh}


def couple(rel="unrelated", a_calls=(), b_calls=(), a_assays=None, b_assays=None, cid="SYN-C0001", paths=None):
    return {
        "couple_id": cid,
        "relationship": {"type": rel, "paths": PATHS[rel] if paths is None else paths},
        "partners": [
            {"partner_id": cid.replace("C", "P", 1) + "A" if cid.startswith("SYN") else cid + "A", "role": "A",
             "sex": "female", "age": 28, "bmi": 24.0, "calls": list(a_calls), "assays": a_assays or {}},
            {"partner_id": cid.replace("C", "P", 1) + "B" if cid.startswith("SYN") else cid + "B", "role": "B",
             "sex": "male", "age": 30, "bmi": 26.0, "calls": list(b_calls), "assays": b_assays or {}},
        ],
    }


# EN display field -> (AR sibling, EN regex, AR regex); the captured group is the locked number (DECISIONS #48)
_NUM = r"([0-9][0-9,]*(?:\.[0-9]+)?)"
AR_SIBLINGS = {
    "offspring_risk_one_in": ("offspring_risk_one_in_ar", rf"1 in {_NUM}", rf"1 من كل {_NUM}"),
    "posterior_carrier_b_one_in": ("posterior_carrier_b_one_in_ar", rf"1 in {_NUM}", rf"1 من كل {_NUM}"),
    "reference_unrelated_one_in": ("reference_unrelated_one_in_ar", rf"1 in {_NUM}", rf"1 من كل {_NUM}"),
    "relative_to_unrelated_display": ("relative_to_unrelated_display_ar", rf"about {_NUM}x", rf"حوالي {_NUM} ضعفاً"),
}


def assert_ar_parity(o):
    """Every _ar field: present iff EN sibling present, null iff EN null, same number string."""
    for en, (ar, en_rx, ar_rx) in AR_SIBLINGS.items():
        assert (en in o) == (ar in o), (en, ar, o)
        if en not in o:
            continue
        assert (o[en] is None) == (o[ar] is None), (en, o[en], o[ar])  # null parity both ways
        if o[en] is None:
            continue
        m_en, m_ar = re.fullmatch(en_rx, o[en]), re.fullmatch(ar_rx, o[ar])
        assert m_en and m_ar, (o[en], o[ar])
        assert m_en.group(1) == m_ar.group(1), (o[en], o[ar])


def assert_schema_valid(outputs):
    for o in outputs:
        errs = sorted(RISK_VALIDATOR.iter_errors(o), key=str)
        assert not errs, [e.message for e in errs]
        assert_ar_parity(o)


@pytest.fixture
def validate():
    return assert_schema_valid
