#!/usr/bin/env python3
"""Mechanical guardrail checks (docs/01-GUARDRAILS.md §C). Exit 1 on any violation.

Usage: python scripts/guardrail_check.py [--pr-body FILE]
Stdlib only. Run locally, in pre-commit and CI.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".next", "dist", "source"}
TEXT_EXT = {".py", ".ts", ".tsx", ".js", ".json", ".md", ".yaml", ".yml", ".html", ".css"}
# files that legitimately discuss the forbidden things (the rules/tests themselves)
EXEMPT = {"docs", "AGENTS.md", "tests", "agents", ".claude", "scripts", "handoffs", "README.md"}

errors: list[str] = []


def err(rule: str, path: pathlib.Path, msg: str) -> None:
    errors.append(f"[{rule}] {path.relative_to(ROOT)}: {msg}")


def files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in TEXT_EXT and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            yield p


def exempt(p: pathlib.Path) -> bool:
    return p.relative_to(ROOT).parts[0] in EXEMPT


# G-03: roster is exactly the seven runtime agents
def check_roster():
    cfg = ROOT / "contracts" / "agents.json"
    expected = ["ConsentGuardian", "VariantInterpreter", "PedigreeRiskEngine", "CulturalCommunicator",
                "CareNavigator", "BioethicsSupervisor", "CounselorCopilot"]
    got = json.loads(cfg.read_text())["runtime_agents"]
    if got != expected:
        err("G-03", cfg, f"runtime agent roster changed: {got}")


# P-13/P-15: directive marriage language and marriage-outcome metrics in shipped code/copy
DIRECTIVE = re.compile(r"\byou should (not )?(marry|cancel|proceed with (the )?marriage|terminate|abort)", re.I)
METRIC = re.compile(r"(cancel(l)?ed[_ ]marriages?|marriage[_ ]cancel(l)?ation[_ ](rate|count|metric)|divorce[_ ]rate)", re.I)
DONOR = re.compile(r"\b(donor (sperm|egg|embryo|gamete)s?|sperm donor|egg donor)\b", re.I)
# P-10: wildcard scopes
WILDCARD_SCOPE = re.compile(r"(patient|user|system)/\*(\.\*|\.[a-z]*)?")
# P-11: secrets / real identifiers
SECRET = re.compile(r"(-----BEGIN (RSA |EC )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|784-\d{4}-\d{7}-\d)")
# P-12: gene/HGVS in logging calls
LOG_GENE = re.compile(r"log(ger)?\.\w+\(.*(c\.\d+|p\.\(|HGVS|gene_symbol)", re.I)


def check_text():
    for p in files():
        if exempt(p):
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        # the BioethicsSupervisor gate must contain the banned phrases it blocks;
        # exempt it from the phrase rules only (P-13/P-15/P-16), never from P-10/P-11/P-12.
        is_gate = "bioethics" in p.name.lower() or "lexicon" in p.name.lower()
        for rx, rule, msg in [
            (DIRECTIVE, "P-13", "directive marriage/pregnancy phrasing"),
            (METRIC, "P-15", "marriage-outcome metric"),
            (DONOR, "P-16", "donor-gamete reference outside the blocklist"),
            (WILDCARD_SCOPE, "P-10", "wildcard SMART scope"),
            (SECRET, "P-11", "secret or real-looking identifier"),
            (LOG_GENE, "P-12", "gene/variant in log call"),
        ]:
            if is_gate and rule in {"P-13", "P-15", "P-16"}:
                continue
            m = rx.search(s)
            if m:
                err(rule, p, f"{msg}: '{m.group(0)[:60]}'")


# P-02: arithmetic on risk-ish names outside services/risk_engine
RISKY = re.compile(r"(risk|prob|freq|posterior|prior|carrier_rate)", re.I)


def _names(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            yield n.id
        elif isinstance(n, ast.Attribute):
            yield n.attr


def check_risk_arithmetic():
    for p in (ROOT / "services").rglob("*.py"):
        if "risk_engine" in p.parts or "tests" in p.parts or "synth" in p.parts:
            continue  # synth samples frequencies; allowed, but it never computes risk output
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Mult, ast.Div, ast.Add, ast.Sub, ast.Pow)):
                if any(RISKY.search(x) for x in _names(n)):
                    err("P-02", p, f"line {n.lineno}: arithmetic on risk-like value outside risk_engine")
                    break


# Mocks must be labelled
def check_mocks():
    for p in files():
        if exempt(p) or p.suffix not in {".py", ".ts", ".tsx"}:
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(malaffi|seha|thiqa|judicial)", p.name, re.I) and "SIMULATED" not in s:
            err("P-19", p, "adapter for government system must be labelled SIMULATED")


def check_pr_body(path: str):
    s = pathlib.Path(path).read_text(encoding="utf-8")
    if not re.search(r"\b(R-(DATA|FHIR|RISK|PRIV|AGT|UX|EVAL|DEMO)-\d+)\b", s):
        errors.append("[G-01] PR body cites no requirement ID (e.g. R-RISK-2)")
    if "Guardrail Attestation" not in s:
        errors.append("[PROC] PR body missing 'Guardrail Attestation' section")


def main():
    check_roster()
    check_text()
    check_risk_arithmetic()
    check_mocks()
    if "--pr-body" in sys.argv:
        check_pr_body(sys.argv[sys.argv.index("--pr-body") + 1])
    if errors:
        print("GUARDRAIL VIOLATIONS:\n" + "\n".join(errors))
        sys.exit(1)
    print("guardrail_check: OK")


if __name__ == "__main__":
    main()
