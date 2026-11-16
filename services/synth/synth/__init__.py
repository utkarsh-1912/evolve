"""data-synth: synthetic Emirati-calibrated couple cohort + V1-V5 vignettes. SYNTHETIC DATA ONLY."""
from .cohort import dumps, generate_cohort, load_panel
from .report import build_report, format_report
from .vignettes import build_vignettes

__all__ = ["generate_cohort", "dumps", "load_panel", "build_report", "format_report", "build_vignettes"]
