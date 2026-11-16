"""Small-cell suppression for population views (guardrail P-11, k >= 10).

Any cell with a count below ``k`` (including 0) is replaced by ``None`` so small groups cannot be
singled out. Primary suppression only: callers must not publish exact totals alongside suppressed
cells (complementary suppression is out of scope for P1; see THREAT_MODEL.md).
"""
from __future__ import annotations

from typing import Mapping, TypeVar

K = TypeVar("K")
SUPPRESSED = None


def suppress(counts: Mapping[K, int], k: int = 10) -> dict[K, int | None]:
    if k < 10:
        raise ValueError("k must be >= 10 (P-11)")
    out: dict[K, int | None] = {}
    for key, n in counts.items():
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("counts must be non-negative integers")
        out[key] = n if n >= k else SUPPRESSED
    return out
