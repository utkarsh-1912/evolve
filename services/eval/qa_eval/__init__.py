"""qa_eval - five-dimension evaluation harness scaffold (R-EVAL-1). All outputs are SIMULATED."""
from .metrics import (  # noqa: F401
    SIMULATED_STAMP,
    THRESHOLDS,
    evaluate,
    guardrail_feed,
    leakage_table,
    wilson,
)
from .personas import STRATA, persona_grid  # noqa: F401
