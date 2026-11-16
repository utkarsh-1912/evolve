"""Backend for the enterprise surfaces (docs/09 §4; contracts/api.md v1.2.x; TASK-P3-AR).

- DisclosureRegistry: consent purpose `disclose-gene-to-partner` (DECISIONS #16). A carrier may opt in to share ONE
  gene with the screen-negative partner, which unlocks that partner's confirmatory Task and a gated message.
- Portal: citizen views (home, activity, notifications, care plan, family tokens). i18n keys only.
- Workbench: counselor cases (SLA 48 h, shift-gated in the API), case view, FHIR-shaped Tasks, notes, closure.

Privacy (P-06): every view is built from the caller's own data, the consented intersection, or a disclosure the
carrier made. Loop states beyond the generic ones are shown only to partners involved in an escalation, so a
screen-negative partner's view never differs because of the other partner's private result (DECISIONS #27).
No arithmetic on probabilities here (P-02): numbers appear only as locked display strings.
"""
from __future__ import annotations

import base64
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from . import _paths

_paths.ensure()

import jsonschema  # noqa: E402

from loopbus import STATES, LoopError  # noqa: E402

from .agents import AgentError  # noqa: E402

if TYPE_CHECKING:  # pragma: no cover
    from .orchestrator import Runtime

from privacy.consent import DISCLOSE_PURPOSE, PURPOSE as APSI_PURPOSE  # noqa: E402,F401
CONSENT_SCHEMA = json.loads((_paths.ROOT / "contracts" / "consent.schema.json").read_text(encoding="utf-8"))
SLA = timedelta(hours=48)            # source §5 metric 3: booked for counseling <= 48 h
TASK_DUE = timedelta(days=14)        # source §5: within the 14-day overall turnaround window
GENERIC_STATES = STATES[:3]          # what every partner sees, involved or not
PRIORITY = {"a": "urgent", "gate": "urgent", "b": "high", "c": "high", "d": "normal"}
TASK_KINDS = ("confirmatory_test", "appointment", "follow_up", "referral", "sure_check")
TASK_STATUSES = ("requested", "accepted", "in-progress", "completed", "cancelled")


class InvalidRequest(AgentError):
    """Well-formed but not allowed by the rules (API maps to 422)."""


class Conflict(AgentError):
    """State does not allow the action (API maps to 409)."""


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# ======================================================================== disclosure consent
class DisclosureRegistry:
    """Consents for purpose `disclose-gene-to-partner` (DECISIONS #16, #40), created, signed, checked and revoked by
    privacy.consent.ConsentService (ANSWER-AR-3). The consent service only checks that the gene is in the panel; the
    runtime checks BEFORE calling create() that the grantor really carries it (Runtime.disclose_gene).
    This registry only indexes the signed records for lookup; it holds no key and signs nothing."""

    def __init__(self, consent_service):
        self._cs = consent_service
        self.items: dict[str, dict] = {}

    def create(self, patient: str, counterpart: str, hgnc_id: int) -> dict:
        c = self._cs.create(patient, counterpart, purpose=DISCLOSE_PURPOSE, scope={"hgnc_id": int(hgnc_id)})
        self.items[c["id"]] = c
        return c

    def revoke(self, cid: str) -> dict:
        out = self._cs.revoke(self.items[cid])  # signed inactive copy; revocation registry kills the original
        jsonschema.validate(out, CONSENT_SCHEMA)
        self.items[cid] = out
        return out

    def valid(self, c: dict) -> bool:
        return self._cs.check(c, purpose=DISCLOSE_PURPOSE) is None

    def active_for_recipient(self, recipient: str) -> set[int]:
        return {c["scope"]["hgnc_id"] for c in self.items.values() if c["counterpart"] == recipient and self.valid(c)}


# ======================================================================== portal (citizen)
class Portal:
    def __init__(self, rt: "Runtime"):
        self.rt = rt

    # ---------------------------------------------------------------- notifications
    def notify(self, partner_id: str, kind: str, title_key: str, href: str) -> dict:
        n = {"id": "ntf-" + secrets.token_hex(6), "ts": _iso(self.rt.clock()), "kind": kind, "title_key": title_key,
             "href": href, "read": False}
        self.rt.contexts[partner_id].notifications.append(n)
        return n

    def notifications(self, partner_id: str) -> list[dict]:
        return [dict(n) for n in reversed(self.rt.contexts[partner_id].notifications)]

    def mark_read(self, partner_id: str, notification_id: str) -> dict:
        for n in self.rt.contexts[partner_id].notifications:
            if n["id"] == notification_id:
                n["read"] = True
                return dict(n)
        raise KeyError("unknown notification")

    def on_loop(self, couple_id: str, state: str, actor_role: str) -> None:
        """Loop listener: notify each partner who may see this state."""
        for p in self.rt.couples[couple_id]["partners"]:
            pid = p["partner_id"]
            if state in GENERIC_STATES or pid in self.rt.involved(couple_id):
                self.notify(pid, "care", f"notif.loop.{state}", "/care-plan")

    # ---------------------------------------------------------------- loop as a partner sees it
    def visible_loop(self, partner_id: str) -> Optional[dict]:
        cid = self.rt.couple_of(partner_id)
        if not self.rt.loop.has(cid):
            return None
        lp = self.rt.loop.get(cid)
        hist = [{"state": h["state"], "ts": h["ts"], "actor_role": h["actor_role"]} for h in lp["history"]]
        if partner_id in self.rt.involved(cid):
            return {"state": lp["state"], "history": hist, "timer": lp["timer"]}
        hist = [h for h in hist if h["state"] in GENERIC_STATES]
        state = hist[-1]["state"] if hist else STATES[0]
        return {"state": state, "history": hist, "timer": {"required": False, "deadline": None, "booked_at": None,
                                                          "overdue": False, "simulated": True}}

    # ---------------------------------------------------------------- home
    def couple_status(self, partner_id: str) -> str:
        cid = self.rt.couple_of(partner_id)
        if cid in self.rt.workspaces:
            return "result_ready"
        other = self.rt.other_partner(partner_id)["partner_id"]
        valid = [c for c in self.rt.consents.values() if self.rt.guardian.verify(c) is None
                 and {c["patient"], c["counterpart"]} == {partner_id, other}]
        mine = any(c["patient"] == partner_id for c in valid)
        theirs = any(c["patient"] == other for c in valid)
        if mine and theirs:
            return "both_consented"
        return "invited" if (mine or theirs) else "not_linked"

    def home(self, partner_id: str) -> dict:
        ctx = self.rt.contexts[partner_id]
        cid = ctx.couple_id
        status = self.couple_status(partner_id)
        mine = [c for c in self.rt.consents.values() if c["patient"] == partner_id]
        if status == "not_linked":
            step = ("invite", "home.next.invite", "/compatibility")
        elif status == "invited":
            step = ("wait", "home.next.wait_partner", "/compatibility") if mine else \
                ("consent", "home.next.consent", "/compatibility")
        elif status == "both_consented":
            step = ("run_check", "home.next.run_check", "/compatibility")
        elif not (ctx.teachback and ctx.teachback["passed"]):
            step = ("teachback", "home.next.teachback", "/teachback")
        elif partner_id in self.rt.involved(cid) and self.rt.loop.has(cid) and \
                STATES.index(self.rt.loop.get(cid)["state"]) < STATES.index("CounselingDone"):
            step = ("counseling", "home.next.counseling", "/care-plan")
        else:
            step = ("care_plan", "home.next.care_plan", "/care-plan")
        consent = None
        if mine:
            last = mine[-1]
            consent = {"status": "inactive" if self.rt.guardian.verify(last) else last["status"],
                       "expires_at": last["period"]["end"]}
        vault = self.rt.vault(partner_id)
        return {"next_step": {"kind": step[0], "title_key": step[1], "href": step[2]}, "couple_status": status,
                "consent": consent,
                "counts": {"results": len(vault["calls"]),
                           "notifications_unread": sum(1 for n in ctx.notifications if not n["read"])}}

    # ---------------------------------------------------------------- activity
    _KINDS = (("me/vault", "results"), ("me/messages", "messages"), ("me/home", "home"), ("me/activity", "activity"),
              ("me/notifications", "notification"), ("me/care-plan", "care_plan"), ("me/teachback", "teachback"),
              ("teachback", "teachback"), ("sure", "sure"), ("consents", "consent"), ("compatibility", "compatibility"),
              ("loop", "care_plan"), ("family", "family_token"))
    _ACTIONS = {"GET": "viewed", "POST": "submitted", "DELETE": "withdrew", "PATCH": "updated"}

    def activity(self, partner_id: str, limit: int = 50) -> list[dict]:
        out = []
        for e in self.rt.audit.events():
            ent = e.get("entity") or []
            if e.get("agent") != "evolve-api" or not ent or ent[0] != partner_id or len(ent) < 2:
                continue
            method, _, path = ent[1].partition(" ")
            kind = next((k for frag, k in self._KINDS if f"/api/{frag}" in path or path.endswith(frag)), "other")
            out.append({"ts": e["recorded"], "actor_role": "you", "action": self._ACTIONS.get(method, "used")
                        if e["outcome"] == "success" else "denied", "object_kind": kind})
        return list(reversed(out))[:max(1, min(int(limit), 200))]

    # ---------------------------------------------------------------- care plan
    def care_plan(self, partner_id: str) -> dict:
        rt = self.rt
        ctx = rt.contexts[partner_id]
        cid = ctx.couple_id
        partner = rt._partner(partner_id)
        own_plp = bool(rt.interpreter.carrier_set(partner))
        ws = rt.workspaces.get(cid)
        incompatible = bool(ws and ws.apsi["compatible"] is False)
        options = rt.navigator.options(incompatible=incompatible, own_plp=own_plp)
        options = [o for o in options if rt.copy_passes_gate(partner_id, o["title_key"], o["body_key"])]
        elig = rt.navigator.eligibility(partner, own_plp=own_plp,
                                        family_history=bool(rt.couples[cid].get("family_history")),
                                        pgtm_option=any(o["id"] == "ivf_pgtm" for o in options))
        loop = self.visible_loop(partner_id) or {"state": None, "history": []}
        tasks = [{"id": t["id"], "kind": t["_kind"], "status": t["status"], "due": t["restriction"]["period"]["end"]}
                 for t in rt.tasks.values() if t["_for"] == partner_id]
        appts = [dict(a) for a in rt.appointments if a["_for"] == partner_id]
        return {"loop": {"state": loop["state"], "history": loop["history"]}, "tasks": tasks,
                "appointments": [{k: v for k, v in a.items() if not k.startswith("_")} for a in appts],
                "options": [{k: o[k] for k in ("id", "title_key", "body_key")} for o in options],
                "eligibility": elig, "simulated": True}

    # ---------------------------------------------------------------- family cascade token (R-PRIV-4)
    def family_token(self, partner_id: str, hgnc_id: int) -> dict:
        partner = self.rt._partner(partner_id)
        calls = [c for c in partner.get("calls") or [] if c["hgnc_id"] == hgnc_id and c["classification"] in ("P", "LP")]
        if not calls:
            raise InvalidRequest("a family token can be created only for your own carrier result")
        c = calls[0]
        # HGVS when present; CNV calls (e.g. SMN1 deletion) have none, so use a stable synthetic descriptor
        variant = c.get("hgvs_c") or c.get("hgvs_p") or f"HGNC:{hgnc_id}:{c.get('variant_type') or 'unknown'}"
        tok = self.rt.cascade.issue(hgnc_id, variant)
        qr = "IDR-CST1." + base64.urlsafe_b64encode(
            json.dumps(tok, sort_keys=True, separators=(",", ":")).encode()).decode().rstrip("=")
        self.rt.audit.append("cascade.issue", "success", entity=[partner_id], agent="ConsentGuardian")
        return {"token": tok, "qr_payload": qr, "expires_at": tok["expiry"]}


# ======================================================================== counselor workbench
class Workbench:
    def __init__(self, rt: "Runtime"):
        self.rt = rt
        self.notes: dict[str, list[dict]] = {}

    def _case(self, case_id: str) -> dict:
        c = self.rt.cases.get(case_id)
        if c is None:
            raise KeyError("unknown case")
        return c

    def case_row(self, c: dict) -> dict:
        rt = self.rt
        cid = c["couple_id"]
        if rt.loop.has(cid):
            status = rt.loop.get(cid)["state"]
        elif cid not in rt.workspaces and rt.counselor_records.get(cid) is None:
            status = "consent_revoked_or_pending"  # couple data purged or not yet run; brief says which
        else:
            status = "no_active_loop"
        return {"case_id": c["case_id"], "couple_id": cid, "trigger": c["trigger"], "priority": PRIORITY.get(c["trigger"], "normal"),
                "opened_at": c["created_at"], "sla_due_at": c["sla_due_at"], "couple_status": status,
                "assigned_to": c.get("assigned_to"), "status": c["status"]}

    def cases(self, status: Optional[str] = None, trigger: Optional[str] = None) -> list[dict]:
        rows = [self.case_row(c) for c in self.rt.cases.values()]
        if status:
            rows = [r for r in rows if r["status"] == status]
        if trigger:
            rows = [r for r in rows if r["trigger"] == trigger]
        return sorted(rows, key=lambda r: (r["sla_due_at"], r["case_id"]))

    def scoped_variants(self, c: dict) -> list[dict]:
        """Consented scope: couple records, counselor_only records, and the case subjects' own records.
        Anything else becomes a placeholder that says nothing (docs/09 §4.2)."""
        rt = self.rt
        cid = c["couple_id"]
        records = rt.counselor_records.get(cid) or []
        role_pid = {p["role"]: p["partner_id"] for p in rt.couples[cid]["partners"]}
        allowed = set(c["subjects"]) | rt.disclosed_recipients(cid)
        out = []
        for r in records:
            if r["audience"] in ("couple", "counselor_only") or role_pid.get(r.get("carrier_role")) in allowed:
                out.append(dict(r))
            else:
                out.append({"outside_consent": True})
        return out

    def pedigree(self, couple: dict, records: list[dict]) -> dict:
        import fhirgen  # lazy: heavy import
        ped = fhirgen.to_dict(fhirgen.build_pedigree(couple))
        nodes, edges = [], []
        roles = {p["partner_id"]: p["role"] for p in couple["partners"]}
        for person in ped.get("persons", []):
            iid = person["individualId"]
            nodes.append({"id": iid, "sex": person.get("sex", "UNKNOWN_SEX"),
                          "affected": person.get("affectedStatus") == "AFFECTED",
                          "role": f"partner_{roles[iid]}" if iid in roles else "relative"})
            for parent in (person.get("paternalId"), person.get("maternalId")):
                if parent:
                    edges.append({"from": parent, "to": iid, "kind": "parent_of"})
        if len(roles) == 2:
            a, b = sorted(roles, key=roles.get)
            edges.append({"from": a, "to": b, "kind": "couple", "consanguineous": couple["relationship"]["type"] != "unrelated"})
        f_values = sorted({r["F"] for r in records if r.get("F") is not None})
        return {"nodes": nodes, "edges": edges, "F": f_values[0] if len(f_values) == 1 else None,
                "fusage": "genome_wide_context_only", "relationship": couple["relationship"]["type"]}

    def case_view(self, case_id: str, counselor_id: str, on_shift: bool) -> dict:
        rt = self.rt
        c = self._case(case_id)
        if c.get("assigned_to") is None:
            c["assigned_to"] = counselor_id
        cid = c["couple_id"]
        couple = rt.couples[cid]
        records = rt.counselor_records.get(cid)
        consent = records is not None and cid in rt.workspaces
        timeline = []
        if rt.loop.has(cid):
            timeline += [{"ts": h["ts"], "kind": "loop", "state": h["state"], "actor_role": h["actor_role"]}
                         for h in rt.loop.get(cid)["history"]]
        timeline += [{"ts": e["recorded"], "kind": "audit", "action": e["action"], "outcome": e["outcome"]}
                     for e in rt.audit.events() if case_id in (e.get("entity") or [])]
        return {"case": self.case_row(c), "brief": rt.brief(case_id),
                "pedigree": self.pedigree(couple, records or []) if consent else None,
                "variants": self.scoped_variants(c) if consent else [],
                "tasks": [self.public_task(t) for t in rt.tasks.values() if t["_couple"] == cid],
                "notes": [dict(n) for n in self.notes.get(case_id, [])],
                "timeline": sorted(timeline, key=lambda x: x["ts"]),
                "access_basis": {"couple_consent": consent, "on_shift": bool(on_shift)}, "simulated": True}

    @staticmethod
    def public_task(t: dict) -> dict:
        return {k: v for k, v in t.items() if not k.startswith("_")}

    def create_task(self, case_id: str, *, kind: str, partner_id: Optional[str], hgnc_id: Optional[int] = None) -> dict:
        rt = self.rt
        c = self._case(case_id)
        if kind not in TASK_KINDS:
            raise InvalidRequest("unknown task kind")
        cid = c["couple_id"]
        allowed = set(c["subjects"]) | rt.disclosed_recipients(cid)
        targets = [partner_id] if partner_id else sorted(allowed)
        if not targets or any(t not in allowed for t in targets):
            # e.g. a Task for a screen-negative partner without the carrier's disclosure consent (DECISIONS #16)
            raise PermissionError("task target outside the consented scope")
        made = [rt.new_task(cid, t, kind, case_id=case_id, hgnc_id=hgnc_id) for t in targets]
        return self.public_task(made[0]) if len(made) == 1 else {"tasks": [self.public_task(t) for t in made]}

    def update_task(self, case_id: str, task_id: str, status: str) -> dict:
        rt = self.rt
        c = self._case(case_id)
        t = rt.tasks.get(task_id)
        if t is None or t["_couple"] != c["couple_id"]:
            raise KeyError("unknown task")
        if status not in TASK_STATUSES:
            raise InvalidRequest("unknown task status")
        t["status"] = status
        t["lastModified"] = _iso(rt.clock())
        rt.audit.append("task.update", "success", entity=[case_id, task_id], agent="CounselorCopilot",
                        detail={"status": status})
        if status == "completed":
            target = {"confirmatory_test": "ConfirmatoryDone", "appointment": "CounselingDone",
                      "referral": "ReproReferralDone"}.get(t["_kind"])
            same = [x for x in rt.tasks.values() if x["_couple"] == t["_couple"] and x["_kind"] == t["_kind"]
                    and x["status"] != "cancelled"]
            if target and all(x["status"] == "completed" for x in same) and rt.loop.has(t["_couple"]):
                try:
                    rt.loop.advance(t["_couple"], target, actor_role="counselor")
                except LoopError:
                    pass  # already at or past this state
        return self.public_task(t)

    def add_note(self, case_id: str, counselor_id: str, text: str, kind: str = "note") -> dict:
        self._case(case_id)
        if not isinstance(text, str) or not text.strip() or len(text) > 5000:
            raise InvalidRequest("note text required (max 5000 chars)")
        n = {"id": "note-" + secrets.token_hex(6), "ts": _iso(self.rt.clock()), "author": counselor_id, "kind": kind,
             "text": text, "visible_to_patient": False}
        self.notes.setdefault(case_id, []).append(n)
        # audit carries ids only, never note text (P-12)
        self.rt.audit.append("note.create", "success", entity=[case_id, n["id"]], agent="CounselorCopilot")
        return n

    def closure(self, case_id: str, counselor_id: str, summary: str) -> dict:
        rt = self.rt
        c = self._case(case_id)
        cid = c["couple_id"]
        if not rt.loop.has(cid):
            raise Conflict("no active care loop for this couple")
        if rt.loop.get(cid)["state"] != "HumanClosure":
            rt.loop.advance(cid, "HumanClosure", actor_role="counselor")
        self.add_note(case_id, counselor_id, summary, kind="closure")
        for other in rt.cases.values():
            if other["couple_id"] == cid:
                other["status"] = "closed"
        rt.audit.append("case.closure", "success", entity=[case_id, cid], agent="CounselorCopilot")
        return {"case": self.case_row(c), "loop": rt.loop.get(cid)}
