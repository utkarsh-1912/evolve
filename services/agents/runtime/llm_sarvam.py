"""Sarvam AI chat client behind the LLMClient interface (DECISIONS #62; docs/SARVAM-API-NOTES.md; guardrail P-21).

Use: COUNSELOR-SIDE AI drafts only (runtime.counselor_draft). Patient text stays closed templates: the patient Runtime
refuses any LLM unless runtime.policy authorizes paraphrase (DECISIONS #37), and that has not happened.

- Endpoint POST https://api.sarvam.ai/v1/chat/completions, header `api-subscription-key`.
- Body: model (env SARVAM_MODEL, default sarvam-105b), messages, temperature 0.2, reasoning_effort "none". If a
  400/422 error mentions reasoning_effort, the request is retried once without that field.
- 20 s timeout; one retry on 429/503 (short backoff); 402 / other errors / timeout -> LLMUnavailable.
- Reasoning content in the response is ignored; only choices[0].message.content is returned.
- Logging: status codes and timings only. NEVER the prompt or the response content (P-12).
- No SARVAM_API_KEY -> OfflineStubClient (deterministic, no network).
Data retention by Sarvam is not documented: send only synthetic, minimized, consented-scope data. TODO(verify).
"""
from __future__ import annotations

import json
import logging
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Callable, Optional

log = logging.getLogger("runtime.llm_sarvam")

SARVAM_URL = "https://api.sarvam.ai/v1/chat/completions"
DEFAULT_MODEL = "sarvam-105b"
TIMEOUT_S = 20.0
RETRY_STATUSES = (429, 503)

# transport(url, headers, body_bytes, timeout) -> (status_code, response_bytes); raises TimeoutError on timeout
Transport = Callable[[str, dict, bytes, float], tuple]


class LLMUnavailable(Exception):
    """Provider error, quota, rate limit after retry, or timeout. Carries a short code, never content."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def urllib_transport(url: str, headers: dict, body: bytes, timeout: float) -> tuple:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https URL)
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b""
    except (socket.timeout, TimeoutError) as e:
        raise TimeoutError("provider timeout") from e
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)):
            raise TimeoutError("provider timeout") from e
        raise LLMUnavailable("network_error") from e


class SarvamClient:
    provider = "sarvam"

    def __init__(self, api_key: str, *, model: Optional[str] = None, transport: Optional[Transport] = None,
                 timeout: float = TIMEOUT_S, sleep: Callable[[float], None] = time.sleep, url: str = SARVAM_URL):
        if not api_key:
            raise ValueError("api key required")
        self._key = api_key
        self.model = model or DEFAULT_MODEL
        self._transport = transport or urllib_transport
        self._timeout = timeout
        self._sleep = sleep
        self._url = url

    def _post(self, payload: dict) -> tuple:
        headers = {"Content-Type": "application/json", "Accept": "application/json", "api-subscription-key": self._key}
        t0 = time.monotonic()
        try:
            status, raw = self._transport(self._url, headers, json.dumps(payload).encode("utf-8"), self._timeout)
        except TimeoutError:
            log.warning("sarvam request timed out after %.1fs", time.monotonic() - t0)
            raise LLMUnavailable("timeout")
        log.info("sarvam status=%s elapsed=%.2fs", status, time.monotonic() - t0)  # no content (P-12)
        return status, raw

    @staticmethod
    def _error_message(raw: bytes) -> str:
        try:
            err = json.loads(raw.decode("utf-8")).get("error") or {}
            return f"{err.get('code', '')} {err.get('message', '')}".lower()
        except (ValueError, AttributeError, UnicodeDecodeError):
            return ""

    def complete(self, system: str, user: str, *, max_tokens: int = 700) -> str:
        payload = {"model": self.model, "temperature": 0.2, "max_tokens": max_tokens, "reasoning_effort": "none",
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        status, raw = self._post(payload)
        if status in (400, 422) and "reasoning_effort" in self._error_message(raw):
            payload.pop("reasoning_effort")  # docs conflict on support: retry once without the field
            status, raw = self._post(payload)
        if status in RETRY_STATUSES:
            self._sleep(1.0)  # one retry with a short backoff
            status, raw = self._post(payload)
        if status == 402:
            raise LLMUnavailable("insufficient_quota")
        if status != 200:
            raise LLMUnavailable(f"http_{status}")
        try:
            data = json.loads(raw.decode("utf-8"))
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError, UnicodeDecodeError):
            raise LLMUnavailable("bad_response")
        if not isinstance(text, str) or not text.strip() or choice.get("finish_reason") == "content_filter":
            raise LLMUnavailable("empty_or_filtered")
        return text.strip()

    # LLMClient interface (P-08 history kept per caller). Not used for patients: runtime.policy keeps paraphrase off.
    def paraphrase(self, text: str, *, lang: str, history: list) -> str:
        return self.complete("Rephrase the text plainly. Keep every number exactly as given.", text)


class OfflineStubClient:
    """No API key configured: deterministic, offline 'draft' that restates the structured prompt fields."""
    provider = "offline-stub"
    model = "offline-stub"

    def complete(self, system: str, user: str, *, max_tokens: int = 700) -> str:
        lines = [ln.strip("- ").strip() for ln in user.splitlines() if ln.strip().startswith("-")]
        body = " ".join(ln.rstrip(".") + "." for ln in lines)
        return ("Offline draft (no AI provider configured), restating the consented case fields for counselor review: "
                + body).strip()

    def paraphrase(self, text: str, *, lang: str, history: list) -> str:
        return text


def client_from_env(transport: Optional[Transport] = None):
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        return OfflineStubClient()
    return SarvamClient(key, model=os.environ.get("SARVAM_MODEL") or DEFAULT_MODEL, transport=transport)
