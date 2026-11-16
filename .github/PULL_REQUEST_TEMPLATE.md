## What / why
<!-- one paragraph -->

## Requirement IDs (mandatory, G-01)
<!-- e.g. R-RISK-2, R-PRIV-1 -->

## Owner agent & paths touched
<!-- must be inside your owned paths (G-05) -->

## Tests run (paste results)
- [ ] unit / contract tests for my area
- [ ] `python scripts/guardrail_check.py`
- [ ] golden vectors unchanged (or orchestrator sign-off linked)

## Guardrail Attestation
- [ ] No probability computed outside `services/risk_engine` (P-02)
- [ ] No cross-partner data in any outbound path (P-06/P-08)
- [ ] No directive/marriage/pregnancy advice; no marriage-outcome metric (P-13/P-15)
- [ ] No donor-gamete suggestion; UAE statute gate untouched or strengthened (P-16)
- [ ] Escalation paths intact (P-18); safety gates still fail closed
- [ ] Synthetic data only; no secrets; logs redacted (P-11/P-12)
- [ ] Mocks labelled SIMULATED (P-19)
- [ ] No new agent / dependency / metric / gene beyond charter (G-03/G-06)
- [ ] Contracts unchanged, or version bump + DECISIONS.md entry

## Deviations / open questions
<!-- should be "none"; otherwise link handoffs/QUESTION-*.md -->
