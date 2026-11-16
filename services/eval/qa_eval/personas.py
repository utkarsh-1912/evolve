"""SIMULATED personas and the deterministic response model (R-EVAL-1, docs/04 §5, TASK-P4-QA-EVAL item 1).

Strata: language (en/ar) x literacy (low/med/high) x sex (female/male) x relationship (unrelated/cousins) = 24 strata.

The response model is a seeded random model with the ASSUMED parameters below. It is NOT a model of real users and NOT an
LLM claim about real users. Its outputs only exercise the system's measurement plumbing; any metric computed from them
describes the assumptions, not the product's real-world effect. Every output is stamped SIMULATED.
"""
from __future__ import annotations

import itertools
import random
from typing import Iterator

STRATA = {
    "lang": ("en", "ar"),
    "literacy": ("low", "med", "high"),
    "sex": ("female", "male"),
    "relationship": ("unrelated", "cousins"),
}

# ASSUMPTIONS (documented, arbitrary, to be replaced by pilot data; they are simulation inputs, not findings)
MODEL_ASSUMPTIONS = {
    "item_accuracy_first_attempt": {"low": 0.78, "med": 0.88, "high": 0.95},
    "item_accuracy_gain_after_counselor_reexplanation": 0.10,
    "item_accuracy_cap": 0.99,
    "sure_item_yes_after_counseling": {"low": 0.95, "med": 0.97, "high": 0.99},
    "language_effect": "none assumed (EN and AR personas use the same parameters)",
    "sex_effect": "none assumed",
    "counselor_booking_delay_hours": {"min": 1, "max": 30, "distribution": "uniform"},
    "confirmatory_completion_share": 0.97,
    "vignette_by_relationship": {"unrelated": ["V2", "V4"], "cousins": ["V1", "V3", "V5"]},
    "note": "Cohort couples are not exposed by the API (sign-in 404), so persona journeys run over V1-V5 by relationship "
            "stratum; cohort couples enter the calibration dimension via the independent oracle.",
}


def persona_grid(per_stratum: int, seed: int = 0) -> Iterator[dict]:
    """Balanced persona list: `per_stratum` synthetic personas in each of the 24 strata."""
    rng = random.Random(seed)
    n = 0
    for combo in itertools.product(*STRATA.values()):
        for _ in range(per_stratum):
            n += 1
            yield {"persona_id": f"SIM-P{n:05d}", **dict(zip(STRATA, combo)), "seed": rng.randrange(1 << 30),
                   "simulated": True}


def stratum_key(persona: dict) -> str:
    return "/".join(str(persona.get(k)) for k in STRATA)


class ResponseModel:
    """Seeded, deterministic answer generator for one persona."""

    def __init__(self, persona: dict, assumptions: dict = MODEL_ASSUMPTIONS):
        self.p = persona
        self.a = assumptions
        self.rng = random.Random(persona["seed"])

    def _accuracy(self, attempt: int) -> float:
        base = self.a["item_accuracy_first_attempt"][self.p["literacy"]]
        gain = self.a["item_accuracy_gain_after_counselor_reexplanation"] if attempt > 1 else 0.0
        return min(self.a["item_accuracy_cap"], base + gain)

    def teachback(self, truths: list[bool], attempt: int = 1) -> list[bool]:
        acc = self._accuracy(attempt)
        return [t if self.rng.random() < acc else (not t) for t in truths]

    def sure(self) -> list[bool]:
        yes = self.a["sure_item_yes_after_counseling"][self.p["literacy"]]
        return [self.rng.random() < yes for _ in range(4)]

    def booking_delay_hours(self) -> float:
        d = self.a["counselor_booking_delay_hours"]
        return self.rng.uniform(d["min"], d["max"])

    def confirmatory_completed(self) -> bool:
        return self.rng.random() < self.a["confirmatory_completion_share"]

    def vignette(self) -> str:
        return self.rng.choice(self.a["vignette_by_relationship"][self.p["relationship"]])
