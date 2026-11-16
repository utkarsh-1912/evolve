"""Prints the red-team corpus summary (per-category pass rates, FP rate) at the end of the pytest run."""
import json
import pathlib
import time

REPORT = pathlib.Path(__file__).resolve().parent / "reports" / "corpus_last_run.json"
_START = time.time()


def pytest_terminal_summary(terminalreporter):
    if not REPORT.exists() or REPORT.stat().st_mtime < _START:
        return
    s = json.loads(REPORT.read_text(encoding="utf-8"))
    tr = terminalreporter
    tr.section("red-team corpus summary (R-EVAL-2)")
    for cat, v in s["categories"].items():
        tr.write_line(f"{cat:32s} {v['ok']:3d}/{v['n']:3d} = {v['pass_rate']:.1%}  en {v['en']}  ar {v['ar']}  "
                      f"wrong_rule={v['wrong_rule']} errors={v['errors']}")
    a, b = s["adversarial"], s["benign"]
    tr.write_line(f"ADVERSARIAL intercepted {a['intercepted']}/{a['n']} = {a['rate']:.1%} (non-semantic {a['non_semantic_rate']:.1%})")
    tr.write_line(f"BENIGN false positives {b['false_positives']}/{b['n']} = {b['fp_rate']:.1%} (budget 5%)")
