"""Summarize HL7 validator CLI output (OperationOutcome or Bundle of them) per source file.

python -m fhirgen.hl7_summary <validator-output.json> [--detail]
Run the CLI first, e.g. (from services/fhir/.tools, jar per ig-lock.json):
  java -jar validator_cli.jar out -version 4.0.1 -ig hl7.fhir.uv.genomics-reporting#3.0.0 -output val.json
Output contains issue text from the validator, which can quote synthetic HGVS strings; do not pipe it to logs.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys


def summarize(path: str) -> list[tuple[str, int, int, int, list[str]]]:
    d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    oos = [e["resource"] for e in d.get("entry", [])] if d.get("resourceType") == "Bundle" else [d]
    rows = []
    for oo in oos:
        src = next((x.get("valueString") for x in oo.get("extension", []) if "file" in x.get("url", "")), path)
        c = collections.Counter(i["severity"] for i in oo.get("issue", []))
        detail = [f"[{i['severity']}] {(i.get('expression') or [''])[0]}: {i.get('details', {}).get('text', '')[:240]}"
                  for i in oo.get("issue", []) if i["severity"] in ("fatal", "error", "warning")]
        rows.append((pathlib.Path(src).name, c["error"] + c["fatal"], c["warning"], c["information"], detail))
    return rows


def main(argv: list[str]) -> int:
    rows = summarize(argv[0])
    for name, e, w, i, detail in sorted(rows):
        print(f"{name}: errors={e} warnings={w} info={i}")
        if "--detail" in argv:
            print("\n".join("  " + x for x in detail))
    print(f"TOTAL: files={len(rows)} errors={sum(r[1] for r in rows)} warnings={sum(r[2] for r in rows)}")
    return 0 if sum(r[1] for r in rows) == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
