"""Counselor-side AI case summary draft (DECISIONS #62, api.md v1.3.0, guardrail P-21).

- Input: the case's CONSENTED-SCOPE brief only, minimized to trigger, scenario/status/reason, locked display strings,
  pedigree relationship and pending task kinds. No partner IDs, no counselor notes, no free text, no HGVS.
- Output: English only (Sarvam has no Arabic). Gated with runtime.bioethics.check (public API, gate files untouched).
  Applied rules: numeric_drift (against the case's scoped locked records), directive, uae_law, stigma,
  false_reassurance, gate_error, and term leakage of anything outside the consented scope. On fail: violations, no text.
- Never stored on the case, never routed to a patient: this module returns a dict and writes only an audit event
  with ids and pass/fail status (no draft text, no prompt).
"""
from __future__ import annotations

from datetime import timezone
from typing import TYPE_CHECKING

from . import bioethics
from .llm_sarvam import LLMUnavailable  # noqa: F401  (re-exported for the API layer)

if TYPE_CHECKING:  # pragma: no cover
    from .orchestrator import Runtime

SYSTEM_PROMPT = (
    "You summarize a genetic-counseling case for a licensed genetic counselor. Write 3 to 6 short, neutral sentences "
    "in English. Use ONLY the facts and numbers given, written exactly as given; do not compute, round or add any "
    "number. Be non-directive: never advise on marriage, cancelling or continuing a marriage, pregnancy, or ending a "
    "pregnancy, and never suggest gametes or embryos from a third party. Do not reassure; say what still needs review or confirmation. "
    "Being a carrier is not a diagnosis. Do not mention names or identifiers."
)
APPLIED_RULES = {"numeric_drift", "directive", "uae_law", "stigma", "false_reassurance", bioethics.GATE_ERROR}
RECORD_FIELDS = ("gene", "scenario", "status", "reason", "offspring_risk_one_in", "posterior_carrier_b_one_in",
                 "reference_unrelated_one_in", "relative_to_unrelated_display", "escalate")
INPUT_FIELDS = ["case.trigger", "pedigree.relationship"] + [f"variants[].{f}" for f in RECORD_FIELDS] + \
               ["pending_tasks[].kind", "pending_tasks[].status"]
TRIGGER_TEXT = {"a": "both partners carry a change in the same gene (incompatible)",
                "b": "discordant result with elevated residual risk or a technically complex gene",
                "c": "uncertain variant in a long run of homozygosity, ambiguous genotype or red-flag family history",
                "d": "unresolved decisional conflict or a teach-back check that needs follow-up",
                "gate": "a message could not be generated safely and needs a human"}


def build_prompt(rt: "Runtime", case: dict) -> tuple[str, list[dict]]:
    """User prompt from consented-scope fields only. Returns (prompt, scoped locked records used)."""
    cid = case["couple_id"]
    scoped = [r for r in rt.workbench.scoped_variants(case) if not r.get("outside_consent")]
    lines = [f"- Escalation trigger ({case['trigger']}): {TRIGGER_TEXT.get(case['trigger'], 'other')}",
             f"- Relationship: {rt.couples[cid]['relationship']['type'].replace('_', ' ')}"]
    for r in scoped:
        parts = [f"gene {r['gene']}", f"scenario {r['scenario'].replace('_', ' ')}", f"status {r['status'].replace('_', ' ')}"]
        if r.get("reason"):
            parts.append(f"reason {r['reason'].replace('_', ' ')}")
        for key, label in (("offspring_risk_one_in", "chance per pregnancy"),
                           ("posterior_carrier_b_one_in", "residual carrier chance after a negative screen"),
                           ("reference_unrelated_one_in", "figure for an unrelated couple"),
                           ("relative_to_unrelated_display", "relative to an unrelated couple")):
            if r.get(key):
                parts.append(f"{label} {r[key]}")
        parts.append("escalated" if r.get("escalate") else "not escalated")
        lines.append("- Variant: " + "; ".join(parts))
    pending = [t for t in rt.tasks.values() if t["_couple"] == cid and t["status"] not in ("completed", "cancelled")]
    for t in pending:
        lines.append(f"- Pending task: {t['_kind'].replace('_', ' ')} ({t['status']})")
    if not scoped:
        lines.append("- Variant: none in the consented scope")
    return "Case facts:\n" + "\n".join(lines), scoped


def _out_of_scope_terms(rt: "Runtime", case: dict, scoped: list[dict]) -> list[str]:
    in_scope = {r["gene"] for r in scoped}
    out = []
    for p in rt.couples[case["couple_id"]]["partners"]:
        for c in p.get("calls") or []:
            if c["gene"] not in in_scope:
                out += [c["gene"], f"HGNC:{c['hgnc_id']}"] + [c[k] for k in ("hgvs_c", "hgvs_p") if c.get(k)]
    return list(dict.fromkeys(out))


def summary_draft(rt: "Runtime", case_id: str, client) -> dict:
    case = rt.cases.get(case_id)
    if case is None:
        raise KeyError("unknown case")
    prompt, scoped = build_prompt(rt, case)
    text = client.complete(SYSTEM_PROMPT, prompt)  # raises LLMUnavailable on provider error
    ctx = bioethics.GateContext(
        recipient_partner_id="COUNSELOR", lang="en", locked_records=scoped,
        forbidden_terms=_out_of_scope_terms(rt, case, scoped), kind="care",
        counterpart_status_hidden=False, shared_hgnc_ids=sorted({r["hgnc_id"] for r in scoped}),
        escalation_required=any(r.get("escalate") or r.get("status") == "needs_counselor" for r in scoped))
    res = bioethics.check(text, ctx)
    violations = [v for v in res.violations if v["rule"] in APPLIED_RULES or
                  (v["rule"] == "leakage" and ("forbidden term" in v["detail"] or "nomenclature" in v["detail"]))]
    passed = not violations
    rt.audit.append("ai_draft.generate", "success" if passed else "denied", entity=[case_id], agent="CounselorCopilot",
                    detail={"status": "passed" if passed else "blocked"})
    return {"draft": text if passed else None, "provider": client.provider, "model": client.model,
            "generated_at": rt.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "ai_generated": True, "gate": {"passed": passed, "violations": violations},
            "input_fields": list(INPUT_FIELDS), "label": "AI draft for counselor review; not sent to patients"}
