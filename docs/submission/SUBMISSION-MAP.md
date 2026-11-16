# Submission deck — fill plan (fill AFTER the final gate; DECISIONS #56)
Template: `submission-template.pptx` (official, 16 slides). Output will be `evolve-submission.pptx` — template layout kept, only content filled. Every number cites a source (docs/demo/CLAIMS-LEDGER.md).

| # | Template slide | Source in this repo | Needs team input |
|---|---|---|---|
| 1 | Team name · size · problem statement | docs/00-CHARTER.md (Problem) | **Team name (évolvé?), team size** |
| 2 | Team members table (name, country, role, org, age confirmation) | — | **All rows** |
| 3 | Team capability summary (≤1,000 chars) | docs/06 roles + what was built | **Real people's skills** |
| 4 | Architecture / workflow diagram | docs/02 §3, README mermaid, 7 agents + APSI + closed templates | — |
| 5 | Target users & intended outcome | docs/00 goal, docs/09 §4 (citizens, couples, counselors, ADPHC/DoH) | — |
| 6 | How success will be measured | charter metrics + services/eval/out/evidence.json (honest: met / not met, SIMULATED) | — |
| 7 | Evidence supporting the approach | source doc citations (§1–§5), test matrix, held-out results (v2 62.4%), 25,508-combination closure | — |
| 8 | Data sources & legal right to use | synthetic only (services/synth), public reference data named in source §2.1 (not ingested), no personal data | Confirm no real data used |
| 9 | Risks & safeguards | docs/01 guardrails, THREAT_MODEL.md, DECISIONS #37/#49 (why patient text is templates-only) | — |
| 10 | Hardware requirements | "None — software only" | — |
| 11 | Login / guest access | simulated sign-in picker = no credentials; demo partner IDs from scripts/demo | Hosted URL if any |
| 12 | Path to pilot & scale | docs/05 §4 (S0–S4), Malaffi/SEHA integration targets (SIMULATED today) | Timeline assumptions |
| 13 | Pre-existing IP & third-party | dependency list (scripts/allowed_deps.txt + package.json), licenses, fonts (free), HL7 validator / phenopacket-tools (tools only, not shipped), logo (team-owned) | Confirm team owns évolvé brand |
| 14 | Conflict of interest | — | **Team declaration** |
| 15 | Additional slide | Demo screenshots (citizen V4/V1/V3, counselor case, eval dashboard) | — |
| 16 | Closing | — | — |
