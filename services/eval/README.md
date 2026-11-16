# services/eval - evaluation harness + evidence pack (R-EVAL-1, R-EVAL-2; owner: qa-redteam)

Computes the five charter success dimensions (docs/00-CHARTER.md "Success metrics") from real backend events and
writes the evidence pack. **Everything persona-derived is SIMULATED**: answers come from a seeded response model with
documented assumptions (`qa_eval/personas.py::MODEL_ASSUMPTIONS`), not from real users, and are never clinical findings.
No risk arithmetic happens here (P-02). The independent math oracle lives in `tests/_support/oracle.py` and is only
used to verify the engine.

## Run (repo root)
```
python -m services.eval                      # re-runs every suite (junit), 240 persona runs, writes services/eval/out/
python -m services.eval --skip-tests         # reuse services/eval/out/junit/*.xml
python -m services.eval --per-stratum 1 --out /tmp/x   # quick smoke (24 runs)
```
Outputs: `services/eval/out/evidence.json`, `evidence.md`, `junit/*.xml`.

## Layout
- `qa_eval/personas.py` - 24 strata (lang x literacy x sex x relationship), the seeded ResponseModel, and its assumptions
- `qa_eval/runner.py` - drives each persona through the real FastAPI app (TestClient) on a SIMULATED clock: consent,
  compatibility, teach-back (one re-explanation on failure), SURE, counselor booking, confirmatory Tasks, loop timer.
  It also runs a live leakage scan of every response.
- `qa_eval/metrics.py` - Wilson 95% CIs, by-stratum breakdowns, the five dimensions, leakage table, guardrail feed
- `qa_eval/evidence.py` - the evidence pack: metrics, tests per suite, guardrail_check, red-team v1 + held-out,
  DECISIONS #37 G2 block, contract versions, build stamp (UTC + sha256 of contracts/*), simulated-vs-real table
- `qa_eval/events.py` - the event shapes consumed

## Known limits
- GCOS-24/GOS: not instrumented in the backend, so it is reported as "not instrumented" and the comprehension
  dimension's `meets` is null (unknown). No values are invented.
- Cohort couples are not exposed by the API, so persona journeys use V1-V5 mapped by relationship stratum.
  Cohort couples enter calibration through the oracle.
- Loop velocity and confirmatory completion reflect the SIMULATED counselor model, not real operations. They
  demonstrate the measurement path: backend timer, booking and Task status.
