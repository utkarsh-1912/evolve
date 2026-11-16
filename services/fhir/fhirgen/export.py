"""Write partner bundles + couple report (for the HL7 validator CLI) and, with --phenopackets, partner
phenopackets + family JSON (for phenopacket-tools `validate`) to a directory.

python -m fhirgen.export <out_dir> <cohort.json> [...] [--phenopackets] [--limit N]   (synthetic data only; output is untracked)
The couple report uses the harness-only intersection from validate.py (not an APSI result).
"""
from __future__ import annotations

import json
import pathlib
import sys

from .bundle import build_couple_report, build_partner_bundle
from .phenopacket import build_family, build_phenopacket, to_dict
from .validate import _test_intersection


def main(argv: list[str]) -> int:
    pheno = "--phenopackets" in argv
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--limit")]
    out = pathlib.Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for path in args[1:]:
        for couple in json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["couples"][:limit]:
            if pheno:
                for p in couple["partners"]:
                    (out / f"{p['partner_id']}-phenopacket.json").write_text(
                        json.dumps(to_dict(build_phenopacket(p)), indent=1))
                    n += 1
                (out / f"{couple['couple_id']}-family.json").write_text(json.dumps(to_dict(build_family(couple)), indent=1))
                n += 1
                continue
            for p in couple["partners"]:
                (out / f"{p['partner_id']}-bundle.json").write_text(json.dumps(build_partner_bundle(p), indent=1))
                n += 1
            (out / f"{couple['couple_id']}-couple-bundle.json").write_text(
                json.dumps(build_couple_report(couple, _test_intersection(couple)), indent=1))
            n += 1
    print(f"wrote {n} files to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
