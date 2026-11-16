"""LLMClient interface (docs/02 §4). Template-first communicator (docs/08 #7): the LLM is optional and
may only paraphrase already-rendered template text; every output still passes BioethicsSupervisor.

Per-user context (P-08): callers pass the history list of ONE partner; clients never keep shared memory.
"""
from __future__ import annotations

from typing import Iterable, Protocol


class LLMClient(Protocol):
    def paraphrase(self, text: str, *, lang: str, history: list) -> str: ...


class StubLLM:
    """Deterministic offline stub: returns the template text unchanged. Records what it was shown,
    keyed by the identity of the per-user history list, so tests can assert context isolation."""

    def __init__(self):
        self.calls: list[dict] = []

    def paraphrase(self, text: str, *, lang: str, history: list) -> str:
        self.calls.append({"history_id": id(history), "lang": lang, "text": text})
        history.append({"role": "assistant", "text": text})
        return text


class ScriptedLLM(StubLLM):
    """Test double: returns scripted outputs in order (then falls back to the template). Used to prove
    that a bad LLM draft is caught and regenerated from the template."""

    def __init__(self, outputs: Iterable[str]):
        super().__init__()
        self._outputs = list(outputs)

    def paraphrase(self, text: str, *, lang: str, history: list) -> str:
        super().paraphrase(text, lang=lang, history=history)
        return self._outputs.pop(0) if self._outputs else text


class ClaudeLLM:
    """Placeholder for the real Claude client (P3). Not wired in P2: the walking skeleton runs
    template-first and offline. It would receive only locked display strings + non-identifying context."""

    def paraphrase(self, text: str, *, lang: str, history: list) -> str:  # pragma: no cover
        raise NotImplementedError("real LLM client is P3; P2 runs template-first")
