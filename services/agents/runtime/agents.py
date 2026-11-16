"""The seven runtime agents (R-AGT-1; docs/02 §4). Plain Python classes with explicit tool bindings.

Neuro-symbolic rule: symbolic agents contain no LLM calls; only CulturalCommunicator (and later the
CareNavigator/CounselorCopilot wording) may use the LLMClient, and only to paraphrase rendered templates.
No agent computes a probability (P-02): every number comes from risk_engine via a locked RiskOutput.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import _paths

_paths.ensure()

import jsonschema  # noqa: E402

from privacy import authority as _authority  # noqa: E402
from privacy._common import hgnc_universe  # noqa: E402
import risk_engine  # noqa: E402

from . import bioethics, templates  # noqa: E402
from .bioethics import GateContext, GateResult  # noqa: E402

log = logging.getLogger("runtime.agents")

ROOT = _paths.ROOT
RISK_SCHEMA = json.loads((ROOT / "contracts" / "risk_output.schema.json").read_text(encoding="utf-8"))
_PANEL = {g["hgnc_id"]: g for g in json.loads((ROOT / "contracts" / "gene_panel.json").read_text(encoding="utf-8"))["genes"]}
PLP = ("P", "LP")
RED_FLAG_RX = re.compile(r"congenital\s+anomal|intellectual\s+disabilit|infant\s+death|neonatal\s+death", re.I)


class AgentError(Exception):
    """An agent refused to proceed (fail closed)."""


class ConsentRequired(AgentError):
    """Both partners' active consents are required (API maps this to 409)."""


# ============================================================================== ConsentGuardian
class ConsentGuardian:
    name = "ConsentGuardian"
    kind = "symbolic"
    TOOLS = ("consent.verify", "consent.request", "token.scope_check", "apsi.invoke", "audit.write", "workspace.purge")

    def __init__(self, *, consents, apsi_service, authority, audit):
        self._consents = consents
        self._apsi = apsi_service
        self._authority = authority
        self._audit = audit
        self._universe = hgnc_universe()

    # consent.request
    def request(self, patient: str, counterpart: str) -> dict:
        return self._consents.create(patient, counterpart)

    # consent.verify
    def verify(self, consent: Optional[dict]) -> Optional[str]:
        """APSI consents only: a disclosure consent can never stand in for an APSI one (ANSWER-AR-3)."""
        return self._consents.check(consent, purpose="apsi-couple-compatibility")

    def active_pair(self, consents: list[dict], a: str, b: str) -> Optional[tuple[dict, dict]]:
        def latest(p, q):
            mine = [c for c in consents if c["patient"] == p and c["counterpart"] == q and self.verify(c) is None]
            return mine[-1] if mine else None
        ca, cb = latest(a, b), latest(b, a)
        if ca is None or cb is None or self._consents.check_pair(ca, cb) is not None:
            return None
        return ca, cb

    # token.scope_check
    @staticmethod
    def scope_check(scopes: list[str], needed: str) -> bool:
        return needed in scopes

    # apsi.invoke
    def invoke_apsi(self, ca: dict, cb: dict, ids_a, ids_b) -> dict:
        """Authority certifies each partner's P/LP carrier set (fresh, single-use), then APSI runs."""
        sa = self._authority.sign_carrier_set(ca["patient"], [h for h in ids_a if h in self._universe])
        sb = self._authority.sign_carrier_set(cb["patient"], [h for h in ids_b if h in self._universe])
        res = self._apsi.run(ca, cb, sa, sb)
        if res["status"] != "ok":
            raise ConsentRequired(res["status"])
        return res

    def open_workspace(self, apsi_result: dict) -> str:
        return self._consents.workspaces.open(apsi_result)

    def read_workspace(self, token: str) -> dict:
        return self._consents.workspaces.read(token)

    # workspace.purge (via revocation)
    def revoke(self, consent: dict) -> dict:
        return self._consents.revoke(consent)

    # audit.write
    def audit(self, action: str, outcome: str, entity: list[str], detail: Optional[dict] = None) -> str:
        return self._audit.append(action, outcome, entity=entity, agent=self.name, detail=detail)


# ============================================================================== VariantInterpreter
class VariantInterpreter:
    name = "VariantInterpreter"
    kind = "symbolic"
    TOOLS = ("fhir.parse_bundle", "curation.lookup", "fhir.make_task")

    def __init__(self):
        self._bundles: dict[str, dict] = {}

    # curation.lookup (panel contract + novelty flags carried on the synthetic call)
    @staticmethod
    def lookup(hgnc_id: int) -> Optional[dict]:
        return _PANEL.get(hgnc_id)

    def is_complex(self, hgnc_id: int) -> bool:
        g = self.lookup(hgnc_id)
        return bool(g and g.get("complex_locus"))

    @staticmethod
    def carrier_set(partner: dict) -> list[int]:
        """HGNC IDs of this partner's P/LP calls (the set the authority certifies for APSI)."""
        return sorted({c["hgnc_id"] for c in partner.get("calls") or [] if c["classification"] in PLP})

    def own_calls(self, partner: dict) -> list[dict]:
        """Own calls in plain language (vault). Only this partner's data; no variant strings."""
        plain = {"P": "pathogenic (disease-causing) change", "LP": "likely pathogenic change",
                 "VUS": "change of uncertain significance", "LB": "likely benign change", "B": "benign change"}
        out = []
        for c in partner.get("calls") or []:
            g = self.lookup(c["hgnc_id"]) or {}
            stage = (partner.get("assays") or {}).get(str(c["hgnc_id"]))
            plain_en = (f"You carry one {plain.get(c['classification'], 'change')} in {c['gene']}. "
                        "Being a carrier is not a diagnosis of disease.")
            out.append({  # api.md v1.1.0 pinned body; extra keys are additive
                "gene": c["gene"], "hgnc_id": c["hgnc_id"], "classification": c["classification"],
                "zygosity": c.get("zygosity"), "plain_en": plain_en,
                "plain_ar": plain_en,  # TODO(ar): English placeholder pending native translation
                "confirmatory_recommended": bool(g.get("complex_locus")) and stage != "confirmatory",
                "condition": g.get("condition"),
                "novelty": {"absent_gnomad": bool(c.get("absent_gnomad")), "absent_clinvar": bool(c.get("absent_clinvar"))},
            })
        return out

    def scenarios(self, couple: dict):
        """Set logic only (who carries what), from risk_engine; used for routing escalations."""
        return risk_engine.gene_scenarios(couple)

    # fhir.parse_bundle / fhir.make_task
    def pending_tasks(self, partner: dict) -> list[dict]:
        pid = partner["partner_id"]
        if pid not in self._bundles:
            import fhirgen  # lazy: heavy import
            self._bundles[pid] = fhirgen.build_partner_bundle(partner)
        tasks = []
        for e in self._bundles[pid]["entry"]:
            r = e["resource"]
            if r["resourceType"] == "Task":
                tasks.append({"for": pid, "status": r["status"], "intent": r["intent"],
                              "code": r["code"]["text"], "description": r.get("description")})
        return tasks


# ============================================================================== PedigreeRiskEngine
class PedigreeRiskEngine:
    name = "PedigreeRiskEngine"
    kind = "symbolic"
    TOOLS = ("pedigree.build", "risk.wright", "risk.bayes", "risk.lock")

    def assess(self, couple: dict) -> list[dict]:
        """All numbers come from risk_engine.assess_couple; each record is schema- and digest-verified."""
        records = risk_engine.assess_couple(couple)
        for r in records:
            jsonschema.validate(r, RISK_SCHEMA)
            body = {k: v for k, v in r.items() if k != "digest"}
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != r["digest"]:
                raise AgentError("locked record digest mismatch")
        return records

    @staticmethod
    def pedigree_summary(couple: dict, records: list[dict]) -> dict:
        rel = couple.get("relationship") or {}
        f_values = sorted({r["F"] for r in records if r.get("F") is not None})
        return {
            "relationship": rel.get("type"),
            "wright_paths": len(rel.get("paths") or []),
            "F": f_values[0] if len(f_values) == 1 else None,
            "fusage": "genome_wide_context_only",
            "family_history": [{"finding": h.get("finding"), "hpo": h.get("hpo")} for h in couple.get("family_history") or []],
        }


# ============================================================================== CulturalCommunicator
@dataclass
class Section:
    text: str
    required: bool = True


@dataclass
class Draft:
    kind: str
    lang: str
    sections: list = field(default_factory=list)
    locked_records: list = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.sections)

    @property
    def digests(self) -> list[str]:
        return [r["digest"] for r in self.locked_records]


class CulturalCommunicator:
    name = "CulturalCommunicator"
    kind = "llm"
    TOOLS = ("risk.read_locked", "teachback.generate")

    def __init__(self, llm):
        self._llm = llm

    def couple_result(self, lang: str, *, compatible: bool, shared_genes: list[str], couple_records: list[dict],
                      review_required: bool) -> Draft:
        r = templates.render
        d = Draft("result", lang, locked_records=list(couple_records))
        d.sections.append(Section(r(lang, "header_result") + " " + r(lang, "notice")))
        if not compatible:
            d.sections.append(Section(r(lang, "apsi_incompatible", genes=shared_genes)))
            for rec in couple_records:
                key = "couple_record_ok" if rec["status"] == "ok" and rec.get("offspring_risk_one_in") else "couple_record_counselor"
                d.sections.append(Section(r(lang, key, record=rec, gene=rec["gene"])))
            d.sections.append(Section(r(lang, "options"), required=False))
        elif review_required:
            d.sections.append(Section(r(lang, "apsi_review")))
        else:
            d.sections.append(Section(r(lang, "apsi_compatible")))
        for key in ("carrier_not_diagnosis", "counselor_notice", "judicial", "close"):
            d.sections.append(Section(r(lang, key)))
        return d

    def own_explainer(self, lang: str, own_records: list[dict], complex_genes: set[str]) -> Draft:
        r = templates.render
        d = Draft("explainer", lang, locked_records=list(own_records))
        d.sections.append(Section(r(lang, "header_private") + " " + r(lang, "notice")))
        for rec in own_records:
            if rec["status"] == "ok" and rec.get("offspring_risk_one_in") and rec.get("posterior_carrier_b_one_in"):
                d.sections.append(Section(r(lang, "own_discordant_ok", record=rec, gene=rec["gene"])))
                if rec.get("relative_to_unrelated_display") and rec.get("reference_unrelated_one_in"):
                    d.sections.append(Section(r(lang, "own_relative", record=rec)))
            else:
                d.sections.append(Section(r(lang, "own_discordant_counselor", gene=rec["gene"])))
            if rec["gene"] in complex_genes:
                d.sections.append(Section(r(lang, "own_confirmatory", gene=rec["gene"])))
        for key in ("carrier_not_diagnosis", "judicial", "close"):
            d.sections.append(Section(r(lang, key)))
        return d

    def disclosure(self, lang: str, gene: str) -> Draft:
        """Message to the screen-negative partner after the carrier's disclosure consent (DECISIONS #16)."""
        return Draft("care", lang, sections=[Section(templates.render(lang, "disclosed_gene", gene=gene)),
                                             Section(templates.render(lang, "carrier_not_diagnosis")),
                                             Section(templates.render(lang, "counselor_notice"))])

    def escalation(self, lang: str, trigger: str) -> Draft:
        key = {"a": "esc_a", "b": "esc_b", "c": "esc_c", "d": "esc_d"}.get(trigger, "esc_gate")
        return Draft("escalation", lang, sections=[Section(templates.render(lang, key))])

    def paraphrase(self, draft: Draft, history: list) -> str:
        """Optional LLM pass over the rendered template, with this recipient's history only (P-08)."""
        return self._llm.paraphrase(draft.text, lang=draft.lang, history=history)

    @staticmethod
    def teachback_items(lang: str) -> list[dict]:
        """teachback.generate: i18n keys (UI owns wording) + reference statement; one per screen; true/false."""
        return [{"id": t["id"], "key": t["key"], "statement": t.get(lang, t["en"]), "answer_type": "boolean"}
                for t in templates.TEACHBACK]

    @staticmethod
    def score_teachback(answers) -> tuple[int, bool]:
        """answers: list of booleans in bank order, or {id: bool}. Anything else scores 0 (never 'fail' wording in UI)."""
        bank = templates.TEACHBACK
        if isinstance(answers, dict):
            answers = [answers.get(t["id"]) for t in bank]
        if not isinstance(answers, list) or len(answers) != len(bank):
            return 0, False
        score = sum(1 for given, t in zip(answers, bank) if given is t["answer"])
        return score, score == len(bank)


# ============================================================================== CareNavigator
class CareNavigator:
    """R-AGT-4 rules (docs/02 §4, agents/agent-runtime.md §5). Symbolic; returns i18n keys only.
    Options are unranked and equal weight (P-13); no donor option exists (P-16). Thresholds are the ones in the
    brief (age 18-45, 46-47 with AFC>=5, >47 discouraged; BMI 19-35, Thiqa 19-40 with dietitian referral) and need
    TODO(verify) against Thiqa policy text. Uses ONLY the caller's own data (P-06)."""
    name = "CareNavigator"
    kind = "symbolic+llm_wording"
    TOOLS = ("eligibility.art_thiqa", "directory.centers", "referral.create")

    @staticmethod
    def options(*, incompatible: bool, own_plp: bool) -> list[dict]:
        ids = ["counseling"]
        if incompatible:
            ids += ["ivf_pgtm", "prenatal_diagnosis", "own_choice"]
        if own_plp:
            ids.append("family_screening")
        # alphabetical by id: a stable order that encodes no recommendation
        return [{"id": i, "title_key": f"care.option.{i}.title", "body_key": f"care.option.{i}.body", "rank": None}
                for i in sorted(ids)]

    @staticmethod
    def eligibility(partner: dict, *, own_plp: bool, family_history: bool, pgtm_option: bool) -> dict:
        """eligibility.art_thiqa for one partner from that partner's own record."""
        checks = []
        immediate = bool(own_plp or family_history)  # abnormal premarital result / carrier / family history
        checks.append({"key": "immediate_eligibility", "status": "met" if immediate else "needs_review",
                       "note_key": "eligibility.immediate.met" if immediate else "eligibility.immediate.not_met"})
        female = partner.get("sex") == "female"
        age = partner.get("age")
        if not female:
            checks.append({"key": "age", "status": "met", "note_key": "eligibility.age.female_partner_only"})
        elif not isinstance(age, (int, float)):
            checks.append({"key": "age", "status": "needs_review", "note_key": "eligibility.age.needs_afc"})
        elif age < 18:
            checks.append({"key": "age", "status": "not_met", "note_key": "eligibility.age.under_minimum"})
        elif age <= 45:
            checks.append({"key": "age", "status": "met", "note_key": "eligibility.age.met"})
        elif age <= 47:  # 46-47: needs AFC >= 5; AFC is not in our data -> needs_review
            checks.append({"key": "age", "status": "needs_review", "note_key": "eligibility.age.needs_afc"})
        else:
            checks.append({"key": "age", "status": "not_met", "note_key": "eligibility.age.discouraged"})
        bmi = partner.get("bmi")
        if not female:
            checks.append({"key": "bmi", "status": "met", "note_key": "eligibility.bmi.female_partner_only"})
        elif isinstance(bmi, (int, float)) and 19 <= bmi <= 35:
            checks.append({"key": "bmi", "status": "met", "note_key": "eligibility.bmi.met"})
        elif isinstance(bmi, (int, float)) and 35 < bmi <= 40:
            checks.append({"key": "bmi", "status": "met", "note_key": "eligibility.bmi.dietitian_referral"})
        else:
            checks.append({"key": "bmi", "status": "needs_review", "note_key": "eligibility.bmi.needs_review"})
        checks.append({"key": "cryopreservation", "status": "met", "note_key": "eligibility.cryo.first_year"})
        if pgtm_option:
            checks.append({"key": "post_pgtm_prenatal_confirmation", "status": "needs_review",
                           "note_key": "eligibility.pgtm.prenatal_confirmation"})
        return {"immediate": immediate, "checks": checks}


# ============================================================================== BioethicsSupervisor
@dataclass
class Review:
    text: Optional[str]
    outcome: str                     # passed | rewritten | escalated
    attempts: list = field(default_factory=list)   # list[GateResult]
    route_fetal: bool = False


class BioethicsSupervisor:
    """Mandatory outbound gate. All four rule groups must pass; regenerate <=2 times; else escalate.
    Errors or exceptions anywhere in the gate are a FAIL (nothing is sent)."""
    name = "BioethicsSupervisor"
    kind = "symbolic"
    TOOLS = ("gate.numeric", "gate.leakage", "gate.nondirective", "gate.uae_law")
    MAX_REGENERATIONS = 2

    @staticmethod
    def _run_gate(text: str, ctx: GateContext) -> GateResult:
        try:
            res = bioethics.check(text, ctx)  # module attribute lookup: a patched gate is honoured
            if not isinstance(res, GateResult) or not isinstance(res.passed, bool):
                raise TypeError("gate returned an unexpected type")
            return res
        except Exception as exc:  # noqa: BLE001 - fail closed
            return GateResult(False, [{"rule": bioethics.GATE_ERROR, "detail": type(exc).__name__}])

    def review(self, first_text: str, draft: Draft, ctx: GateContext) -> Review:
        rv = Review(None, "escalated")
        text = first_text
        for attempt in range(self.MAX_REGENERATIONS + 1):
            res = self._run_gate(text, ctx)
            rv.attempts.append(res)
            if res.passed:
                rv.text, rv.outcome = text, ("passed" if attempt == 0 else "rewritten")
                return rv
            if res.fetal_route:  # fetal-anomaly content: no rewrite, route to MFM + counselor (P-16)
                rv.route_fetal = True
                return rv
            if attempt == 0:
                text = draft.text                      # regenerate 1: plain template, no LLM
            elif attempt == 1:
                text = self._strip_optional(draft, ctx)  # regenerate 2: drop optional sections that violate
                if text is None:
                    return rv
        return rv

    def _strip_optional(self, draft: Draft, ctx: GateContext) -> Optional[str]:
        sub = GateContext(ctx.recipient_partner_id, ctx.lang, ctx.locked_records, ctx.forbidden_terms, "explainer")
        kept = []
        for s in draft.sections:
            ok = self._run_gate(s.text, sub).passed
            if ok or s.required:
                kept.append(s.text)
            if not ok and s.required:
                return None
        return " ".join(kept)


# ============================================================================== CounselorCopilot
class CounselorCopilot:
    name = "CounselorCopilot"
    kind = "symbolic+llm_summary"
    TOOLS = ("triage.rules", "brief.assemble", "task.create")

    @staticmethod
    def triggers(*, apsi: dict, records: list[dict], scenarios, couple: dict) -> dict[str, set]:
        """triage.rules -> {trigger: set(roles to notify)}. (a) incompatible (b) discordant with elevated
        residual (record escalate=true, DECISIONS #19) (c) shared VUS in ROH / ambiguous genotype / red-flag
        pedigree. (d) is raised from SURE / teach-back. Never auto-cleared (P-18)."""
        out: dict[str, set] = {}
        roles_by_gene = {s.hgnc_id: set(s.carrier_roles) for s in scenarios}
        if apsi.get("compatible") is False:
            out.setdefault("a", set()).update({"A", "B"})
        for r in records:
            if not r.get("escalate"):
                continue
            if r["scenario"] == "concordant_positive":
                out.setdefault("a", set()).update({"A", "B"})
            elif r["scenario"] == "discordant":
                out.setdefault("b", set()).add(r.get("carrier_role") or "A")
                if not r.get("carrier_role"):
                    out["b"].add("B")
            elif r["scenario"] == "shared_vus_roh":
                out.setdefault("c", set()).update({"A", "B"})
            else:  # atypical_genotype and anything unexpected: route, never clear
                out.setdefault("c", set()).update(roles_by_gene.get(r["hgnc_id"]) or {"A", "B"})
        if any(RED_FLAG_RX.search(str(h.get("finding", ""))) for h in couple.get("family_history") or []):
            out.setdefault("c", set()).update({"A", "B"})
        return out

    @staticmethod
    def new_case(couple_id: str, trigger: str, created_at: str) -> dict:
        return {"case_id": "case-" + secrets.token_hex(6), "couple_id": couple_id, "trigger": trigger,
                "created_at": created_at}

    @staticmethod
    def assemble_brief(case: dict, *, pedigree: Optional[dict], records: list[dict], tasks: list[dict],
                       questions: list[dict], scores: dict, purged: bool) -> dict:
        variant_summary = [{"outside_consent": True} if r.get("outside_consent") else
                           {k: r.get(k) for k in ("gene", "hgnc_id", "scenario", "status", "audience", "carrier_role",
                                                  "reason", "offspring_risk_one_in", "posterior_carrier_b_one_in",
                                                  "reference_unrelated_one_in", "relative_to_unrelated_display",
                                                  "escalate", "digest")} for r in records]
        return {"case_id": case["case_id"], "couple_id": case["couple_id"], "trigger": case["trigger"],
                "created_at": case["created_at"], "consent_revoked_data_purged": purged,
                "pedigree": pedigree, "variant_summary": variant_summary, "pending_tasks": tasks,
                "couple_questions": questions, "comprehension": scores,
                "note": "Decision support for the counselor; not a diagnosis. Synthetic data (SIMULATED)."}
