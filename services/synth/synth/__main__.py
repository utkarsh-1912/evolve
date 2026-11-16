"""CLI: python -m synth --seed 42 --n 1000 --out services/synth/out/cohort.json [--vignettes-dir DIR]"""
from __future__ import annotations

import argparse
import json
import pathlib

from .cohort import ROOT, dumps, generate_cohort
from .report import build_report, format_report
from .vignettes import build_vignettes

DEFAULT_OUT = ROOT / "services" / "synth" / "out" / "cohort.json"
DEFAULT_VIGNETTES = ROOT / "tests" / "golden" / "cohort"


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="synth", description="Generate the SYNTHETIC couple cohort.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--vignettes-dir", type=pathlib.Path, default=None,
                    help="also write V1..V5 fixtures to this directory (golden: tests/golden/cohort)")
    args = ap.parse_args(argv)
    out = args.out if args.out.is_absolute() else (pathlib.Path.cwd() / args.out)
    doc = generate_cohort(args.seed, args.n)
    _write(out, dumps(doc))
    rep = build_report(doc)
    _write(out.with_name(out.stem + "_report.json"), json.dumps(rep, indent=2) + "\n")
    print(format_report(rep))
    print(f"wrote {out}")
    if args.vignettes_dir is not None:
        for vid, vdoc in build_vignettes().items():
            _write(args.vignettes_dir / f"{vid}.json", dumps(vdoc))
        print(f"wrote V1..V5 to {args.vignettes_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
