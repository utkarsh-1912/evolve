# Sarvam AI — API notes (from docs.sarvam.ai, fetched 2026-11-16)

- Endpoint: `POST https://api.sarvam.ai/v1/chat/completions` (JSON). Models: `sarvam-105b` (128K ctx), `sarvam-105b-conversations` (32K).
- Auth header: `api-subscription-key: <SARVAM_API_KEY>` (also accepts `Authorization: Bearer <key>`).
- Body: `model`, `messages` [{role: system|user|assistant, content}], `temperature` (default 0.2, 0–2), `max_tokens` (default 2048; reasoning tokens count), `reasoning_effort` (`none|low|medium|high|max`; docs conflict on default — send `"none"` explicitly, and if a 400/422 mentions it, retry without the field).
- Response text: `choices[0].message.content` (reasoning, if any, in `choices[0].message.reasoning_content` — ignore it). `finish_reason`: stop|length|content_filter…
- Errors: `{"error": {"message","code","request_id"}}`; 402 `insufficient_quota_error`, 429 `rate_limit_exceeded_error` (60 req/min pay-as-you-go), 503 under load → backoff.
- Languages: 10 Indian + English for chat. **No Arabic** → counselor AI drafts are English only.
- Pricing: ₹15 / 1M input, ₹60 / 1M output tokens; ₹100 free credits per verified user.
- Data retention / privacy policy: **not found in docs** → send only synthetic, minimized, consented-scope data; TODO(verify) before any real patient data.
