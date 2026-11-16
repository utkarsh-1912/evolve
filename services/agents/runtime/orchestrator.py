"""Runtime orchestration (R-AGT-1/2/3). One `Runtime` holds the in-memory demo state and the seven agents.

Data path for a compatibility check (docs/02 §3):
  ConsentGuardian (both consents) -> privacy.apsi.run -> couple workspace (intersection only)
  -> PedigreeRiskEngine (risk_engine.assess_couple, locked records) + VariantInterpreter (set logic)
  -> route records strictly by audience / carrier_role (P-06)
  -> CounselorCopilot triggers (a)-(c) -> cases
  -> CulturalCommunicator drafts (templates, locked slots) -> BioethicsSupervisor -> deliver | escalate
Every user-visible message goes through `_deliver`, and `_deliver` only stores a message the gate passed.
"""
from __future__ import annotations

import copy
import json
import logging
import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from . import _paths

_paths.ensure()

from loopbus import LoopBus, default_adapters  # noqa: E402
from privacy.apsi import ApsiService  # noqa: E402
from privacy.audit import AuditLog  # noqa: E402
from privacy.authority import Authority  # noqa: E402
from privacy.consent import ConsentService  # noqa: E402

from .agents import (  # noqa: E402
    AgentError,
    BioethicsSupervisor,
    CareNavigator,
    ConsentGuardian,
    ConsentRequired,
    CounselorCopilot,
    CulturalCommunicator,
    Draft,
    PedigreeRiskEngine,
    VariantInterpreter,
)
from privacy.cascade import CascadeIssuer  # noqa: E402

from . import policy, templates  # noqa: E402
from .bioethics import GateContext  # noqa: E402
from .enterprise import SLA, TASK_DUE, DisclosureRegistry, InvalidRequest, Portal, Workbench  # noqa: E402,F401
from .context import CoupleWorkspace, PartnerContext  # noqa: E402
from .llm import StubLLM  # noqa: E402

log = logging.getLogger("runtime.orchestrator")

ROOT = _paths.ROOT
VIGNETTES = ("V1", "V2", "V3", "V4", "V5")
GATE_RULE_GROUPS = ["numeric", "leakage", "nondirective", "uae_law"]


class NotFound(AgentError):
    pass


class Forbidden(AgentError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_vignettes() -> list[dict]:
    out = []
    for v in VIGNETTES:
        p = ROOT / "tests" / "golden" / "cohort" / f"{v}.json"
        out += json.loads(p.read_text(encoding="utf-8"))["couples"]
    return out


def cohort_size() -> int:
    p = ROOT / "services" / "synth" / "out" / "cohort.json"
    try:
        return len(json.loads(p.read_text(encoding="utf-8"))["couples"])
    except (OSError, ValueError, KeyError):
        return 0


class Runtime:
    def __init__(self, *, clock: Callable[[], datetime] = utcnow, llm=None, authority: Optional[Authority] = None,
                 use_llm: bool = False):
        self.clock = clock
        self.use_llm = bool(use_llm or llm is not None)
        if self.use_llm and not policy.llm_paraphrase_allowed():
            # DECISIONS #37: closed templates for patients; LLM paraphrase is hard-off unless authorized
            raise policy.LLMPolicyError("LLM paraphrase is disabled (closed templates for patients)")
        self.llm = llm or StubLLM()
        self.authority = authority or Authority(clock=clock)  # key generation is slow: kept across resets
        self._lock = threading.RLock()
        self.reset()

    # ================================================================== state
    def reset(self, couples: Optional[list[dict]] = None) -> dict:
        with self._lock:
            self.audit = AuditLog(clock=self.clock)
            self.consent_service = ConsentService(audit=self.audit, clock=self.clock)
            self.apsi_service = ApsiService(authority=self.authority.public_key, consents=self.consent_service,
                                            audit=self.audit, clock=self.clock)
            self.loop = LoopBus(clock=self.clock)
            self.adapters = default_adapters(self.clock)
            self.guardian = ConsentGuardian(consents=self.consent_service, apsi_service=self.apsi_service,
                                            authority=self.authority, audit=self.audit)
            self.interpreter = VariantInterpreter()
            self.pedigree = PedigreeRiskEngine()
            self.communicator = CulturalCommunicator(self.llm)
            self.navigator = CareNavigator()
            self.supervisor = BioethicsSupervisor()
            self.copilot = CounselorCopilot()
            self.couples: dict[str, dict] = {}
            self.partners: dict[str, tuple[str, str]] = {}
            self.contexts: dict[str, PartnerContext] = {}
            self.consents: dict[str, dict] = {}
            self.workspaces: dict[str, CoupleWorkspace] = {}
            self.counselor_records: dict[str, list[dict]] = {}
            self.cases: dict[str, dict] = {}
            self.guardrail_events: list[dict] = []
            self.tasks: dict[str, dict] = {}
            self.appointments: list[dict] = []
            self.disclosures = DisclosureRegistry(self.consent_service)
            self.cascade = CascadeIssuer(clock=self.clock)
            self.portal = Portal(self)
            self.workbench = Workbench(self)
            self.loop.listeners.append(self.portal.on_loop)
            for c in couples if couples is not None else load_vignettes():
                self.add_couple(c)
            return {"status": "ok", "vignettes": len(self.couples), "cohort_couples": cohort_size()}

    def add_couple(self, couple: dict) -> None:
        cid = couple["couple_id"]
        self.couples[cid] = copy.deepcopy(couple)
        for p in couple["partners"]:
            self.partners[p["partner_id"]] = (cid, p["role"])
            self.contexts[p["partner_id"]] = PartnerContext(p["partner_id"], cid, p["role"])

    def vignettes(self) -> list[dict]:
        return [{"couple_id": cid, "label": f"Vignette {cid[1:]} - {c['relationship']['type'].replace('_', ' ')}",
                 "partner_ids": [p["partner_id"] for p in sorted(c["partners"], key=lambda p: p["role"])]}
                for cid, c in self.couples.items()]

    def _partner(self, partner_id: str) -> dict:
        if partner_id not in self.partners:
            raise NotFound("unknown partner")
        cid, role = self.partners[partner_id]
        return next(p for p in self.couples[cid]["partners"] if p["role"] == role)

    def couple_of(self, partner_id: str) -> str:
        if partner_id not in self.partners:
            raise NotFound("unknown partner")
        return self.partners[partner_id][0]

    def other_partner(self, partner_id: str) -> dict:
        cid, role = self.partners[partner_id]
        return next(p for p in self.couples[cid]["partners"] if p["role"] != role)

    def set_lang(self, partner_id: str, lang: str) -> None:
        if lang in ("en", "ar"):
            self.contexts[partner_id].lang = lang

    # ================================================================== consent
    def request_consent(self, partner_id: str, counterpart: str) -> dict:
        with self._lock:
            if self.other_partner(partner_id)["partner_id"] != counterpart:
                raise Forbidden("consent counterpart must be your partner")
            c = self.guardian.request(partner_id, counterpart)
            self.consents[c["id"]] = c
            self.portal.notify(counterpart, "consent", "notif.consent_received", "/compatibility")
            return c

    def list_consents(self, partner_id: str) -> list[dict]:
        """Caller's consents, both directions (given and received); api.md v1.1.0. Includes disclosure consents."""
        both = list(self.consents.values()) + list(self.disclosures.items.values())
        return [dict(c) for c in both if partner_id in (c["patient"], c["counterpart"])]

    def simulate_partner_consent(self, couple_id: str) -> list[dict]:
        """SIMULATED demo helper: create any missing active consent for both partners of a couple."""
        with self._lock:
            couple = self.couples.get(couple_id)
            if couple is None:
                raise NotFound("unknown couple")
            made = []
            ids = [p["partner_id"] for p in sorted(couple["partners"], key=lambda p: p["role"])]
            for me, other in ((ids[0], ids[1]), (ids[1], ids[0])):
                have = [c for c in self.consents.values() if c["patient"] == me and c["counterpart"] == other
                        and self.guardian.verify(c) is None]
                if not have:
                    made.append(self.request_consent(me, other))
            return made

    def revoke_consent(self, partner_id: str, consent_id: str) -> dict:
        with self._lock:
            if consent_id in self.disclosures.items:
                return self._revoke_disclosure(partner_id, consent_id)
            c = self.consents.get(consent_id)
            if c is None:
                raise NotFound("unknown consent")
            if c["patient"] != partner_id:
                raise Forbidden("not your consent")
            revoked = self.guardian.revoke(c)
            self.consents[consent_id] = revoked
            cid = self.couple_of(partner_id)
            self._purge_couple(cid)
            for p in self.couples[cid]["partners"]:
                self.portal.notify(p["partner_id"], "consent", "notif.consent_revoked", "/privacy")
            return revoked

    def _purge_couple(self, couple_id: str) -> None:
        """P-07: revocation purges couple state (workspace, derived records and messages, loop)."""
        self.workspaces.pop(couple_id, None)
        self.counselor_records.pop(couple_id, None)
        self.loop.purge(couple_id)
        for p in self.couples[couple_id]["partners"]:
            ctx = self.contexts[p["partner_id"]]
            ctx.records = []
            ctx.messages = [m for m in ctx.messages if not m.get("_compat")]

    # ================================================================== compatibility
    def run_compatibility(self, couple_id: str) -> dict:
        with self._lock:
            couple = self.couples.get(couple_id)
            if couple is None:
                raise NotFound("unknown couple")
            parts = {p["role"]: p for p in couple["partners"]}
            pa, pb = parts["A"], parts["B"]
            pair = self.guardian.active_pair(list(self.consents.values()), pa["partner_id"], pb["partner_id"])
            if pair is None:
                raise ConsentRequired("both partners' active consents are required")
            apsi = self.guardian.invoke_apsi(pair[0], pair[1], self.interpreter.carrier_set(pa),
                                             self.interpreter.carrier_set(pb))
            self._purge_couple(couple_id)
            token = self.guardian.open_workspace(apsi)

            records = self.pedigree.assess(couple)
            scenarios = self.interpreter.scenarios(couple)
            shared = set(apsi["shared_hgnc_ids"])
            couple_recs, own, counselor = [], {"A": [], "B": []}, []
            for r in records:
                if r["audience"] == "couple" and r["hgnc_id"] in shared:
                    couple_recs.append(r)
                elif r["audience"] == "carrier_partner_only" and r.get("carrier_role") in ("A", "B"):
                    own[r["carrier_role"]].append(r)
                else:  # counselor_only, or a couple record outside the intersection (fail closed)
                    counselor.append(r)
            self.workspaces[couple_id] = CoupleWorkspace(couple_id, token, apsi, couple_recs)
            self.counselor_records[couple_id] = records
            for role, p in parts.items():
                self.contexts[p["partner_id"]].records = own[role]

            triggers = self.copilot.triggers(apsi=apsi, records=records, scenarios=scenarios, couple=couple)
            for t, roles in triggers.items():
                self.open_case(couple_id, t, subjects=[parts[r]["partner_id"] for r in sorted(roles)])
            for p in parts.values():  # confirmatory Task for the carrier's own call at a complex locus
                for call in self.interpreter.own_calls(p):
                    if call["confirmatory_recommended"] and call["classification"] in ("P", "LP"):
                        self.new_task(couple_id, p["partner_id"], "confirmatory_test", hgnc_id=call["hgnc_id"])
            self.loop.start(couple_id, booking_required="a" in triggers)
            self.adapters["Judicial"].send("certificate_issued_regardless_of_result", couple_id=couple_id)

            shared_genes = sorted({r["gene"] for r in couple_recs} | {self._symbol(h) for h in shared})
            delivered: dict[str, list[dict]] = {}
            for role, p in parts.items():
                pid = p["partner_id"]
                ctx = self.contexts[pid]
                review = "c" in triggers and role in triggers["c"]
                msgs = []
                d = self.communicator.couple_result(ctx.lang, compatible=bool(apsi["compatible"]),
                                                    shared_genes=shared_genes, couple_records=couple_recs,
                                                    review_required=review)
                msgs.append(self._deliver(ctx, d, couple_level=True, compat=True))
                if own[role]:
                    complex_genes = {r["gene"] for r in own[role] if self.interpreter.is_complex(r["hgnc_id"])}
                    msgs.append(self._deliver(ctx, self.communicator.own_explainer(ctx.lang, own[role], complex_genes),
                                              compat=True))
                for t in sorted(triggers):
                    if role in triggers[t]:
                        msgs.append(self._deliver(ctx, self.communicator.escalation(ctx.lang, t), compat=True))
                delivered[pid] = [m for m in msgs if m is not None]
            if any(delivered.values()):
                self.loop.advance(couple_id, "PatientNotified", actor_role="system")
            # per-partner views only: trigger letters are counselor data (a "b" would reveal A's private result)
            review = {p["partner_id"]: ("c" in triggers and role in triggers["c"]) for role, p in parts.items()}
            return {"apsi": apsi, "records": couple_recs, "messages": delivered, "review_required": review}

    def _symbol(self, hgnc_id: int) -> str:
        g = self.interpreter.lookup(hgnc_id)
        return g["symbol"] if g else f"HGNC:{hgnc_id}"

    # ================================================================== outbound path
    def forbidden_terms(self, partner_id: str, *, couple_level: bool) -> list[str]:
        """Other partner's genes/IDs/variants/conditions not in the consented intersection (+ for couple-level
        messages, the recipient's own non-intersection genes as well: the couple view shows only the intersection)."""
        cid = self.couple_of(partner_id)
        ws = self.workspaces.get(cid)
        shared = set(ws.apsi["shared_hgnc_ids"]) if ws else set()
        shared |= self.disclosures.active_for_recipient(partner_id)
        sources = [self.other_partner(partner_id)]
        if couple_level:
            sources.append(self._partner(partner_id))
        terms: list[str] = []
        for p in sources:
            for c in p.get("calls") or []:
                if c["hgnc_id"] in shared:
                    continue
                terms += [c["gene"], f"HGNC:{c['hgnc_id']}"]
                terms += [c[k] for k in ("hgvs_c", "hgvs_p") if c.get(k)]
                g = self.interpreter.lookup(c["hgnc_id"])
                if g:
                    terms.append(g["condition"])
        return list(dict.fromkeys(terms))

    def _gate_context(self, partner_id: str, lang: str, locked: list, kind: str, *, couple_level: bool) -> GateContext:
        """GateContext v1.1.0: hidden counterpart status unless the APSI intersection is non-empty (DECISIONS #23);
        escalation_required from every record this recipient may see (DECISIONS #24)."""
        ctx = self.contexts[partner_id]
        ws = self.workspaces.get(ctx.couple_id)
        shared = sorted(set(ws.apsi["shared_hgnc_ids"] if ws else []) | self.disclosures.active_for_recipient(partner_id))
        visible = list(ctx.records) + (list(ws.records) if ws else [])
        return GateContext(recipient_partner_id=partner_id, lang=lang, locked_records=locked,
                           forbidden_terms=self.forbidden_terms(partner_id, couple_level=couple_level), kind=kind,
                           counterpart_status_hidden=not shared, shared_hgnc_ids=shared,
                           escalation_required=any(r.get("escalate") or r["status"] == "needs_counselor" for r in visible))

    def _deliver(self, ctx: PartnerContext, draft: Draft, *, couple_level: bool = False,
                 compat: bool = False) -> Optional[dict]:
        msg_id = "msg-" + secrets.token_hex(6)
        gate_ctx = self._gate_context(ctx.partner_id, draft.lang, list(draft.locked_records), draft.kind,
                                      couple_level=couple_level)
        try:
            first = self.communicator.paraphrase(draft, ctx.llm_history) if self.use_llm else draft.text
        except Exception:  # noqa: BLE001 - LLM failure: fall back to the template, still gated
            first = draft.text
        review = self.supervisor.review(first, draft, gate_ctx)
        ts = _iso(self.clock())
        for i, res in enumerate(review.attempts):
            if res.passed:
                self.guardrail_events.append({"ts": ts, "rule": "all", "outcome": review.outcome, "message_id": msg_id})
            else:
                last = i == len(review.attempts) - 1 and review.text is None
                for rule in res.rules:
                    self.guardrail_events.append({"ts": ts, "rule": rule, "outcome": "escalated" if last else "blocked",
                                                  "message_id": msg_id})
        if review.text is None:
            # Nothing is sent. Route to a human (P-18); fetal-anomaly content routes to MFM + counselor (P-16).
            self.open_case(ctx.couple_id, "gate", subjects=[ctx.partner_id])
            return None
        msg = {"id": msg_id, "to": ctx.partner_id, "lang": draft.lang, "kind": draft.kind, "text": review.text,
               "locked_digests": draft.digests, "gate": {"passed": True, "rules": list(GATE_RULE_GROUPS)},
               "simulated": True, "created_at": ts, "_compat": compat}
        ctx.messages.append(msg)
        if draft.kind in ("result", "escalation"):
            res = draft.kind == "result"
            self.portal.notify(ctx.partner_id, draft.kind, "notif.result_ready" if res else "notif.counselor_contact",
                               "/results" if res else "/care-plan")
        return self.public_message(msg)

    @staticmethod
    def public_message(msg: dict) -> dict:
        return {k: v for k, v in msg.items() if not k.startswith("_")}

    def gate_probe(self, recipient_partner_id: str, draft: str, lang: str = "en", kind: str = "result") -> dict:
        """Run a draft through BioethicsSupervisor only (demo). Nothing is delivered."""
        ctx = self.contexts.get(recipient_partner_id)
        if ctx is None:
            raise NotFound("unknown partner")
        ws = self.workspaces.get(ctx.couple_id)
        locked = list(ctx.records) + (list(ws.records) if ws else [])
        gctx = self._gate_context(recipient_partner_id, lang, locked, kind, couple_level=False)
        res = self.supervisor._run_gate(draft, gctx)
        self.guardrail_events.append({"ts": _iso(self.clock()), "rule": "all" if res.passed else ",".join(res.rules),
                                      "outcome": "passed" if res.passed else "blocked", "message_id": "probe"})
        return res.to_dict()

    # ================================================================== partner views
    def vault(self, partner_id: str) -> dict:
        ctx = self.contexts[partner_id]
        ws = self.workspaces.get(ctx.couple_id)
        return {"partner_id": partner_id,
                "calls": self.interpreter.own_calls(self._partner(partner_id)),
                "records": list(ctx.records) + (list(ws.records) if ws else []),
                "notice": "Decision support - not a diagnosis or medical advice. Synthetic data (SIMULATED).",
                "simulated": True}

    def messages(self, partner_id: str) -> list[dict]:
        return [self.public_message(m) for m in self.contexts[partner_id].messages]

    def teachback(self, partner_id: str, answers: list) -> dict:
        with self._lock:
            ctx = self.contexts[partner_id]
            score, passed = self.communicator.score_teachback(answers)
            ctx.teachback = {"score": score, "passed": passed}
            escalated = not passed
            if escalated:
                self.open_case(ctx.couple_id, "d", subjects=[ctx.partner_id])
                self._deliver(ctx, self.communicator.escalation(ctx.lang, "d"))
            else:
                self._maybe_comprehension(ctx.couple_id)
            return {"passed": passed, "score": score, "escalated": escalated}

    def sure(self, partner_id: str, answers: list) -> dict:
        with self._lock:
            if not isinstance(answers, list) or len(answers) != 4 or not all(isinstance(a, bool) for a in answers):
                raise ValueError("SURE needs exactly four yes/no answers")
            ctx = self.contexts[partner_id]
            score = sum(1 for a in answers if a)
            escalated = score < 4
            ctx.sure = {"score": score}
            if escalated:
                self.open_case(ctx.couple_id, "d", subjects=[ctx.partner_id])
                self._deliver(ctx, self.communicator.escalation(ctx.lang, "d"))
            return {"score": score, "escalated": escalated}

    def _maybe_comprehension(self, couple_id: str) -> None:
        if not self.loop.has(couple_id):
            return
        ctxs = [self.contexts[p["partner_id"]] for p in self.couples[couple_id]["partners"]]
        if all(c.teachback and c.teachback["passed"] for c in ctxs) and self.loop.get(couple_id)["state"] == "PatientNotified":
            self.loop.advance(couple_id, "ComprehensionConfirmed", actor_role="system")

    # ================================================================== counselor
    def open_case(self, couple_id: str, trigger: str, subjects: Optional[list] = None) -> dict:
        subjects = list(subjects or [p["partner_id"] for p in self.couples[couple_id]["partners"]])
        for c in self.cases.values():
            if c["couple_id"] == couple_id and c["trigger"] == trigger and c["status"] == "open":
                c["subjects"] = sorted(set(c["subjects"]) | set(subjects))
                return c
        now = self.clock()
        case = self.copilot.new_case(couple_id, trigger, _iso(now))
        case.update({"subjects": sorted(set(subjects)), "status": "open", "assigned_to": None,
                     "sla_due_at": _iso(now + SLA)})
        self.cases[case["case_id"]] = case
        self.audit.append("counselor.case_open", "success", entity=[case["case_id"], couple_id], agent="CounselorCopilot")
        self.adapters["Malaffi"].send("consultation_brief_ready", couple_id=couple_id)
        return case

    def queue(self) -> list[dict]:
        keys = ("case_id", "couple_id", "trigger", "created_at")
        return sorted(({k: c[k] for k in keys} for c in self.cases.values()), key=lambda c: c["created_at"])

    # ================================================================== P3 helpers
    def involved(self, couple_id: str) -> set:
        """Partners who may see escalation-specific state: case subjects + disclosed recipients."""
        out = set()
        for c in self.cases.values():
            if c["couple_id"] == couple_id:
                out |= set(c["subjects"])
        return out | self.disclosed_recipients(couple_id)

    def disclosed_recipients(self, couple_id: str) -> set:
        return {p["partner_id"] for p in self.couples[couple_id]["partners"]
                if self.disclosures.active_for_recipient(p["partner_id"])}

    def new_task(self, couple_id: str, partner_id: str, kind: str, *, case_id: Optional[str] = None,
                 hgnc_id: Optional[int] = None) -> dict:
        """FHIR-shaped Task (R4 Task subset). Partner-facing views show only {id, kind, status, due}."""
        now = self.clock()
        t = {"resourceType": "Task", "id": "task-" + secrets.token_hex(6), "status": "requested", "intent": "order",
             "code": {"text": kind}, "description_key": f"task.{kind}", "for": {"reference": f"Patient/{partner_id}"},
             "authoredOn": _iso(now), "restriction": {"period": {"end": _iso(now + TASK_DUE)}},
             "owner": {"display": "genetic counselor"},
             "meta": {"tag": [{"system": "urn:evolve:demo", "code": "SIMULATED"}]},
             "_kind": kind, "_for": partner_id, "_couple": couple_id, "_case": case_id}
        if hgnc_id is not None:
            t["focus"] = {"display": f"HGNC:{hgnc_id}"}  # counselor view only; partner view drops it
        self.tasks[t["id"]] = t
        self.audit.append("task.create", "success", entity=[t["id"], partner_id], agent="CounselorCopilot")
        self.portal.notify(partner_id, "task", "notif.task_created", "/care-plan")
        if kind == "appointment":
            self.appointments.append({"id": "appt-" + secrets.token_hex(5), "ts": _iso(now + timedelta(hours=24)),
                                      "with_role": "genetic_counselor", "status": "proposed", "simulated": True,
                                      "_for": partner_id, "_task": t["id"]})
            self.portal.notify(partner_id, "appointment", "notif.appointment", "/care-plan")
            if self.loop.has(couple_id):
                self.loop.book_counseling(couple_id, actor_role="counselor")
        return t

    def copy_passes_gate(self, partner_id: str, *keys: str) -> bool:
        """The EN reference copy behind i18n keys goes through the gate before it is offered (fail closed)."""
        if not all(templates.I18N_EN.get(k) for k in keys):
            return False
        text = " ".join(templates.I18N_EN[k] for k in keys)
        ctx = self._gate_context(partner_id, "en", [], "care", couple_level=False)
        return self.supervisor._run_gate(text, ctx).passed

    def disclose_gene(self, partner_id: str, hgnc_id: int) -> dict:
        """DECISIONS #16: the carrier opts in to share ONE discordant complex-locus gene with the partner."""
        with self._lock:
            ctx = self.contexts[partner_id]
            rec = next((r for r in ctx.records if r["hgnc_id"] == hgnc_id and r["audience"] == "carrier_partner_only"
                        and r.get("carrier_role") == ctx.role), None)
            if rec is None:
                raise InvalidRequest("only your own private carrier result can be shared")
            if not self.interpreter.is_complex(hgnc_id):
                raise InvalidRequest("sharing to unlock a confirmatory test applies to technically complex genes")
            other = self.other_partner(partner_id)
            c = self.disclosures.create(partner_id, other["partner_id"], hgnc_id)  # audited by privacy.consent
            octx = self.contexts[other["partner_id"]]
            self.new_task(ctx.couple_id, other["partner_id"], "confirmatory_test", hgnc_id=hgnc_id)
            self._deliver(octx, self.communicator.disclosure(octx.lang, rec["gene"]), compat=True)
            self.portal.notify(other["partner_id"], "consent", "notif.shared_gene", "/results")
            return c

    def _revoke_disclosure(self, partner_id: str, consent_id: str) -> dict:
        c = self.disclosures.items[consent_id]
        if c["patient"] != partner_id:
            raise Forbidden("not your consent")
        out = self.disclosures.revoke(consent_id)  # audited by privacy.consent
        focus = f"HGNC:{c['scope']['hgnc_id']}"
        for t in self.tasks.values():
            if t["_for"] == c["counterpart"] and t.get("focus", {}).get("display") == focus and t["status"] != "completed":
                t["status"] = "cancelled"
        return out

    def brief(self, case_id: str) -> dict:
        case = self.cases.get(case_id)
        if case is None:
            raise NotFound("unknown case")
        cid = case["couple_id"]
        couple = self.couples[cid]
        records = self.counselor_records.get(cid)
        purged = records is None
        scoped = [] if purged else self.workbench.scoped_variants(case)
        tasks = [] if purged else [t for p in couple["partners"] if p["partner_id"] in case["subjects"]
                                   for t in self.interpreter.pending_tasks(p)]
        scores = {p["partner_id"]: {"teachback": self.contexts[p["partner_id"]].teachback,
                                    "sure": self.contexts[p["partner_id"]].sure} for p in couple["partners"]}
        return self.copilot.assemble_brief(
            case, pedigree=None if purged else self.pedigree.pedigree_summary(couple, records),
            records=scoped, tasks=tasks, questions=[], scores=scores, purged=purged)


_default: Optional[Runtime] = None


def default_runtime() -> Runtime:
    global _default
    if _default is None:
        _default = Runtime()
    return _default


def run_compatibility(couple_id: str, runtime: Optional[Runtime] = None) -> dict:
    """Module-level entry point (task card): orchestrate one couple's compatibility check."""
    return (runtime or default_runtime()).run_compatibility(couple_id)
