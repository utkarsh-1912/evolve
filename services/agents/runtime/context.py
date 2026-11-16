"""Per-user context objects (P-08) and the couple workspace (intersection only, P-06)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PartnerContext:
    """Everything the runtime holds for ONE partner. Never shared with the other partner's context."""
    partner_id: str
    couple_id: str
    role: str                     # "A" | "B"
    lang: str = "en"
    records: list = field(default_factory=list)       # own carrier_partner_only RiskOutputs
    messages: list = field(default_factory=list)      # delivered messages addressed to this partner
    llm_history: list = field(default_factory=list)   # this partner's LLM conversation only
    teachback: Optional[dict] = None
    sure: Optional[dict] = None
    notifications: list = field(default_factory=list)  # [{id, ts, kind, title_key, href, read}]


@dataclass
class CoupleWorkspace:
    """Holds only the APSI result (intersection) and the audience=couple records derived from it."""
    couple_id: str
    token: str                    # privacy.consent.WorkspaceStore token (revocation kills it)
    apsi: dict
    records: list = field(default_factory=list)
