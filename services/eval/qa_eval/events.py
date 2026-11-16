"""Event shapes the harness consumes (plug points). Producers: simulated persona runner, loop bus,
API /api/guardrail/events, red-team corpus report, cohort sweep, FHIR validator. Synthetic only (P-11).

Every event is a dict with "type" and, for user-level events, "persona": {"lang", "literacy", "gender"}.

  comprehension    {"items": {<teach-back key>: bool correct}, "passed": bool (backend verdict), "attempt": 1|2}
  gcos             {"pre": float, "post": float}            GCOS-24 / GOS empowerment score, same persona
  sure             {"score": int 0..4, "phase": "post"}     SURE after counseling
  coercion_flag    {"source": str}                          any directive/coercion flag raised in a session
  booking          {"couple_id": str, "incompatible": bool, "result_ts": iso8601, "booked_ts": iso8601|None}
  task             {"kind": "confirmatory", "completed": bool}
  arithmetic_sweep {"records": int, "mismatches": int}      from tests/integration cohort sweep
  fhir_validation  {"errors": int}
  redteam          {"category": str, "n": int, "intercepted": int, "leaks": int}
  leak_scan        {"responses": int, "leaks": int}         live API responses scanned for the other partner's terms
  guardrail        {"ts", "rule", "outcome", "message_id"}  contracts/api.md feed, no text, no genes
"""
EVENT_TYPES = ("comprehension", "gcos", "sure", "coercion_flag", "booking", "task", "arithmetic_sweep",
               "fhir_validation", "redteam", "leak_scan", "guardrail")
# teach-back knowledge items (MMIC-style), keyed as the API's /api/me/teachback/start question keys
COMPREHENSION_ITEMS = ("carrier_not_diagnosis", "each_pregnancy", "negative_not_zero", "you_decide")
GUARDRAIL_KEYS = {"ts", "rule", "outcome", "message_id"}
GUARDRAIL_OUTCOMES = ("blocked", "rewritten", "escalated", "passed")
