"""CLI: python -m services.eval [--per-stratum N] [--seed S] [--skip-tests] [--out DIR]

Builds services/eval/out/evidence.json + evidence.md (SIMULATED evidence pack, TASK-P4-QA-EVAL). Run from the repo root.
--skip-tests reuses the existing junit files in services/eval/out/junit instead of re-running every suite.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from qa_eval.evidence import OUT, build  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m services.eval")
    ap.add_argument("--per-stratum", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    a = ap.parse_args()
    e = build(per_stratum=a.per_stratum, seed=a.seed, skip_tests=a.skip_tests, out_dir=a.out)
    d = e["dimensions"]
    print(f"SIMULATED evidence pack -> {a.out}")
    for k, v in d.items():
        print(f"  {k:16s} meets={v['meets']}")
    print(f"  persona runs={e['persona_runs']['n']} harness problems={len(e['persona_runs']['harness_problems'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
