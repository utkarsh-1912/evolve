"""FastAPI app implementing contracts/api.md v1.2.x (R-AGT-1..4, R-PRIV-2/3/4 wiring, R-UX-2/3 backend).

SMART-style hardening (R-PRIV-3), all SIMULATED (no real IdP):
- tokens expire after <= 1 h on the injectable clock; expired or unknown tokens -> 401
- every endpoint declares the one scope it needs; a token without it -> 403 insufficient_scope
- PKCE (RFC 7636, S256 only): POST /api/auth/authorize {partner_id|role, code_challenge, code_challenge_method, state}
  -> {code, state}; POST /api/auth/token {code, code_verifier} -> token. Codes are single-use, 60 s.
  POST /api/session remains as the SIMULATED one-step demo sign-in.
Every request is scoped to the token's partner; naming another partner (path, query or header) -> 403. Every request
writes an AuditEvent (P-10). Errors use {"error": {"code", "message"}} with no PHI or genes.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from typing import Any, Optional

from . import bootstrap  # noqa: F401  (sys.path for our packages)

from fastapi import Depends, FastAPI, HTTPException, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from loopbus import ForbiddenTransition, LoopError  # noqa: E402
from runtime.agents import ConsentRequired  # noqa: E402
from runtime.enterprise import DISCLOSE_PURPOSE, Conflict, InvalidRequest  # noqa: E402
from runtime.orchestrator import Forbidden, NotFound, Runtime  # noqa: E402

DEFAULT_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001",
                   "http://localhost:3002", "http://127.0.0.1:3002"]
ENVIRONMENTS = ("local", "vm", "vercel-render")


def cors_origins() -> list[str]:
    """CORS_ORIGINS (comma-separated) from env for deployed targets; the localhost defaults are always kept."""
    extra = [o.strip().rstrip("/") for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
    return list(dict.fromkeys(DEFAULT_ORIGINS + extra))

PARTNER_SCOPES = ["patient/Observation.rs", "patient/DiagnosticReport.r", "patient/Consent.cru"]
COUNSELOR_SCOPES = ["user/DiagnosticReport.rs", "user/Task.cru"]
TOKEN_TTL = timedelta(seconds=3600)      # P-10: <= 1 h
CODE_TTL = timedelta(seconds=60)
OBS, REPORT, CONSENT = PARTNER_SCOPES
C_READ, C_TASK = COUNSELOR_SCOPES


# ------------------------------------------------------------------------------------------ bodies
class SessionIn(BaseModel):
    partner_id: Optional[str] = None
    role: Optional[str] = None
    lang: Optional[str] = None
    scopes: Optional[list[str]] = None      # optional down-scoping (least privilege)
    counselor_id: Optional[str] = None


class AuthorizeIn(SessionIn):
    code_challenge: str
    code_challenge_method: str = "S256"
    state: str


class TokenIn(BaseModel):
    code: str
    code_verifier: str


class ConsentIn(BaseModel):
    counterpart: Optional[str] = None
    purpose: Optional[str] = None
    hgnc_id: Optional[int] = None


class AnswersIn(BaseModel):
    answers: Any


class AdvanceIn(BaseModel):
    to: str


class CoupleIn(BaseModel):
    couple_id: str


class ProbeIn(BaseModel):
    recipient_partner_id: str
    draft: str
    lang: str = "en"
    kind: str = "result"


class FamilyTokenIn(BaseModel):
    hgnc_id: int


class ShiftIn(BaseModel):
    on: bool


class TaskIn(BaseModel):
    kind: str
    partner_id: Optional[str] = None
    hgnc_id: Optional[int] = None


class TaskPatch(BaseModel):
    status: str


class NoteIn(BaseModel):
    text: str


class ClosureIn(BaseModel):
    summary: str


def _err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode().rstrip("=")


def create_app(runtime: Optional[Runtime] = None) -> FastAPI:
    rt = runtime or Runtime()
    app = FastAPI(title="evolve API (SIMULATED, synthetic data only)", version="1.3.0")
    # The counselor AI draft (DECISIONS #62) is PAUSED (deployment first): runtime/llm_sarvam.py and
    # runtime/counselor_draft.py exist but are not imported here; no LLM is reachable from this app.
    app.state.runtime = rt
    app.state.sessions = {}
    app.state.codes = {}
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["*"], allow_headers=["*"])

    # ------------------------------------------------------------------ errors
    @app.exception_handler(StarletteHTTPException)
    async def _http(_req, exc: StarletteHTTPException):
        code = exc.detail if isinstance(exc.detail, str) else "error"
        return _err(exc.status_code, code, code.replace("_", " "))

    @app.exception_handler(RequestValidationError)
    async def _validation(_req, _exc):
        return _err(422, "invalid_request", "request body or parameters are invalid")

    # ------------------------------------------------------------------ auth + audit middleware
    def _resolve(request: Request) -> Optional[dict]:
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return None
        sess = app.state.sessions.get(auth[7:].strip())
        if sess is None or rt.clock() >= sess["expires_at"]:
            return {"invalid": True}
        return sess

    @app.middleware("http")
    async def scope_and_audit(request: Request, call_next):
        principal = _resolve(request)
        request.state.principal = principal if principal and not principal.get("invalid") else None
        actor = (principal or {}).get("partner_id") or (principal or {}).get("role") or "anonymous"
        action = "api.read" if request.method == "GET" else "api.write"
        entity = [actor, f"{request.method} {request.url.path}"]
        if principal and principal.get("invalid"):
            rt.audit.append(action, "denied", entity=entity, agent="evolve-api", detail={"reason": "invalid_token"})
            return _err(401, "invalid_token", "token invalid or expired")
        me = (principal or {}).get("partner_id")
        named = [request.query_params.get("partner_id"), request.headers.get("x-partner-id")]
        if me and any(n and n != me for n in named):
            rt.audit.append(action, "denied", entity=entity, agent="evolve-api", detail={"reason": "cross_partner"})
            return _err(403, "forbidden", "access is limited to your own data")
        response = await call_next(request)
        rt.audit.append(action, "success" if response.status_code < 400 else "denied", entity=entity,
                        agent="evolve-api", detail={"status": str(response.status_code)})
        return response

    def principal(request: Request) -> dict:
        p = request.state.principal
        if p is None:
            raise HTTPException(401, "unauthenticated")
        return p

    def need(role: str, scope: str):
        """Dependency: the caller has this role AND this scope (per-endpoint scope enforcement, P-10)."""
        def dep(p: dict = Depends(principal)) -> dict:
            if p["role"] != role:
                raise HTTPException(403, "forbidden")
            if scope not in p["scopes"]:
                raise HTTPException(403, "insufficient_scope")
            return p
        return dep

    def any_reader(p: dict = Depends(principal)) -> dict:
        if (p["role"] == "partner" and REPORT in p["scopes"]) or (p["role"] == "counselor" and C_READ in p["scopes"]):
            return p
        raise HTTPException(403, "insufficient_scope")

    def on_shift(p: dict = Depends(need("counselor", C_READ))) -> dict:
        if not p.get("on_shift"):
            raise HTTPException(403, "off_shift")
        return p

    def on_shift_writer(p: dict = Depends(need("counselor", C_TASK))) -> dict:
        if not p.get("on_shift"):
            raise HTTPException(403, "off_shift")
        return p

    def own_couple(p: dict, couple_id: str) -> None:
        if couple_id not in rt.couples:
            raise HTTPException(404, "not_found")
        if p["role"] == "partner" and rt.couple_of(p["partner_id"]) != couple_id:
            raise HTTPException(403, "forbidden")

    # ------------------------------------------------------------------ sessions (SIMULATED sign-in)
    def _principal_for(body: SessionIn) -> dict:
        if body.role == "counselor":
            sess = {"role": "counselor", "partner_id": None, "scopes": list(COUNSELOR_SCOPES),
                    "counselor_id": body.counselor_id or "counselor-1", "on_shift": False}
        elif body.partner_id:
            if body.partner_id not in rt.partners:
                raise HTTPException(404, "not_found")
            sess = {"role": "partner", "partner_id": body.partner_id, "scopes": list(PARTNER_SCOPES)}
        else:
            raise HTTPException(422, "invalid_request")
        if body.scopes is not None:
            if not body.scopes or any(s not in sess["scopes"] for s in body.scopes):
                raise HTTPException(400, "invalid_scope")
            sess["scopes"] = [s for s in sess["scopes"] if s in body.scopes]
        return sess

    def _issue(sess: dict, lang: Optional[str]) -> dict:
        if lang and sess["partner_id"]:
            rt.set_lang(sess["partner_id"], lang)
        token = secrets.token_urlsafe(32)
        app.state.sessions[token] = {**sess, "expires_at": rt.clock() + TOKEN_TTL}
        return {"token": token, "token_type": "Bearer", "partner_id": sess["partner_id"], "role": sess["role"],
                "scopes": sess["scopes"], "expires_in": int(TOKEN_TTL.total_seconds()), "simulated": True,
                "label": "SIMULATED sign-in"}

    @app.post("/api/session")
    def session(body: SessionIn):
        return _issue(_principal_for(body), body.lang)

    @app.post("/api/auth/authorize")
    def authorize(body: AuthorizeIn):
        """SIMULATED authorization endpoint: no login UI; issues a one-time code bound to the PKCE challenge."""
        if body.code_challenge_method != "S256":
            raise HTTPException(400, "unsupported_challenge_method")
        if len(body.state) < 22:  # >= 128 bits of base64url entropy (docs/02 §7 asks >= 122)
            raise HTTPException(400, "invalid_state")
        if not 43 <= len(body.code_challenge) <= 128:
            raise HTTPException(400, "invalid_challenge")
        sess = _principal_for(body)
        code = secrets.token_urlsafe(24)
        app.state.codes[code] = {"sess": sess, "challenge": body.code_challenge, "lang": body.lang,
                                 "expires_at": rt.clock() + CODE_TTL}
        return {"code": code, "state": body.state, "simulated": True}

    @app.post("/api/auth/token")
    def token(body: TokenIn):
        entry = app.state.codes.pop(body.code, None)  # single use
        if entry is None or rt.clock() >= entry["expires_at"]:
            raise HTTPException(400, "invalid_grant")
        if not 43 <= len(body.code_verifier) <= 128 or not hmac.compare_digest(_s256(body.code_verifier), entry["challenge"]):
            raise HTTPException(400, "invalid_grant")
        return _issue(entry["sess"], entry["lang"])

    # ------------------------------------------------------------------ demo
    @app.post("/api/demo/reset")
    def demo_reset():
        return rt.reset()

    @app.get("/api/demo/vignettes")
    def demo_vignettes():
        return rt.vignettes()

    @app.post("/api/demo/simulate-partner-consent")
    def simulate_partner_consent(body: CoupleIn):
        try:
            made = rt.simulate_partner_consent(body.couple_id)
        except NotFound:
            raise HTTPException(404, "not_found")
        return {"couple_id": body.couple_id, "created": len(made), "simulated": True, "label": "SIMULATED"}

    @app.post("/api/demo/gate-probe")
    def gate_probe(body: ProbeIn):
        try:
            return rt.gate_probe(body.recipient_partner_id, body.draft, body.lang, body.kind)
        except NotFound:
            raise HTTPException(404, "not_found")

    @app.get("/api/guardrail/events")
    def guardrail_events():
        return list(rt.guardrail_events)

    # ------------------------------------------------------------------ partner: results, consent, check
    @app.get("/api/me/vault")
    def vault(p: dict = Depends(need("partner", OBS))):
        return rt.vault(p["partner_id"])

    @app.get("/api/me/messages")
    def messages(p: dict = Depends(need("partner", OBS))):
        return rt.messages(p["partner_id"])

    @app.get("/api/consents")
    def list_consents(p: dict = Depends(need("partner", CONSENT))):
        return rt.list_consents(p["partner_id"])

    @app.post("/api/consents")
    def consents(body: ConsentIn, p: dict = Depends(need("partner", CONSENT))):
        try:
            if body.purpose == DISCLOSE_PURPOSE:
                if body.hgnc_id is None:
                    raise HTTPException(422, "invalid_request")
                return rt.disclose_gene(p["partner_id"], body.hgnc_id)
            if body.purpose not in (None, "apsi-couple-compatibility") or not body.counterpart:
                raise HTTPException(422, "invalid_request")
            return rt.request_consent(p["partner_id"], body.counterpart)
        except Forbidden:
            raise HTTPException(403, "forbidden")
        except InvalidRequest:
            raise HTTPException(422, "not_allowed")

    @app.delete("/api/consents/{consent_id}")
    def revoke(consent_id: str, p: dict = Depends(need("partner", CONSENT))):
        try:
            return rt.revoke_consent(p["partner_id"], consent_id)
        except NotFound:
            raise HTTPException(404, "not_found")
        except Forbidden:
            raise HTTPException(403, "forbidden")

    @app.post("/api/couples/{couple_id}/compatibility")
    def compatibility(couple_id: str, p: dict = Depends(need("partner", CONSENT))):
        own_couple(p, couple_id)
        try:
            res = rt.run_compatibility(couple_id)
        except ConsentRequired:
            raise HTTPException(409, "consent_required")
        me = p["partner_id"]
        mine = [m for m in res["messages"].get(me, []) if m["kind"] in ("result", "escalation")]
        return {"apsi": res["apsi"], "records": res["records"], "messages": mine,
                "review_required": res["review_required"].get(me, False)}

    # ------------------------------------------------------------------ partner: portal (v1.2.0)
    @app.get("/api/me/home")
    def home(p: dict = Depends(need("partner", REPORT))):
        return rt.portal.home(p["partner_id"])

    @app.get("/api/me/activity")
    def activity(limit: int = 50, p: dict = Depends(need("partner", REPORT))):
        return rt.portal.activity(p["partner_id"], limit)

    @app.get("/api/me/notifications")
    def notifications(p: dict = Depends(need("partner", REPORT))):
        return rt.portal.notifications(p["partner_id"])

    @app.post("/api/me/notifications/{notification_id}/read")
    def notification_read(notification_id: str, p: dict = Depends(need("partner", REPORT))):
        try:
            return rt.portal.mark_read(p["partner_id"], notification_id)
        except KeyError:
            raise HTTPException(404, "not_found")

    @app.get("/api/me/care-plan")
    def care_plan(p: dict = Depends(need("partner", REPORT))):
        return rt.portal.care_plan(p["partner_id"])

    @app.post("/api/me/teachback/start")
    def teachback_start(p: dict = Depends(need("partner", REPORT))):
        ctx = rt.contexts[p["partner_id"]]
        return {"questions": rt.communicator.teachback_items(ctx.lang), "answer_format": "list of booleans in order, or {id: bool}"}

    @app.post("/api/teachback")
    def teachback(body: AnswersIn, p: dict = Depends(need("partner", REPORT))):
        return rt.teachback(p["partner_id"], body.answers)

    @app.post("/api/sure")
    def sure(body: AnswersIn, p: dict = Depends(need("partner", REPORT))):
        try:
            return rt.sure(p["partner_id"], body.answers)
        except ValueError:
            raise HTTPException(422, "invalid_request")

    @app.post("/api/family/tokens")
    def family_token(body: FamilyTokenIn, p: dict = Depends(need("partner", OBS))):
        try:
            return rt.portal.family_token(p["partner_id"], body.hgnc_id)
        except InvalidRequest:
            raise HTTPException(403, "forbidden")

    # ------------------------------------------------------------------ counselor (v1.0 + v1.2.0)
    @app.get("/api/counselor/queue")
    def queue(_p: dict = Depends(on_shift)):  # DECISIONS #40: legacy endpoints are shift-gated too
        return rt.queue()

    @app.get("/api/counselor/briefs/{case_id}")
    def brief(case_id: str, _p: dict = Depends(on_shift)):
        try:
            return rt.brief(case_id)
        except NotFound:
            raise HTTPException(404, "not_found")

    @app.post("/api/counselor/shift")
    def shift(body: ShiftIn, request: Request, p: dict = Depends(need("counselor", C_TASK))):
        p["on_shift"] = bool(body.on)  # the session dict itself (online_access flag)
        rt.audit.append("counselor.shift", "success", entity=[p["counselor_id"]], agent="evolve-api",
                        detail={"status": "on" if body.on else "off"})
        return {"counselor_id": p["counselor_id"], "on_shift": p["on_shift"]}

    @app.get("/api/counselor/cases")
    def cases(status: Optional[str] = None, trigger: Optional[str] = None, _p: dict = Depends(on_shift)):
        return rt.workbench.cases(status, trigger)

    @app.get("/api/counselor/cases/{case_id}")
    def case_view(case_id: str, p: dict = Depends(on_shift)):
        try:
            return rt.workbench.case_view(case_id, p["counselor_id"], p["on_shift"])
        except (KeyError, NotFound):
            raise HTTPException(404, "not_found")

    @app.post("/api/counselor/cases/{case_id}/tasks")
    def create_task(case_id: str, body: TaskIn, _p: dict = Depends(on_shift_writer)):
        try:
            return rt.workbench.create_task(case_id, kind=body.kind, partner_id=body.partner_id, hgnc_id=body.hgnc_id)
        except KeyError:
            raise HTTPException(404, "not_found")
        except PermissionError:
            raise HTTPException(403, "outside_consent")
        except InvalidRequest:
            raise HTTPException(422, "invalid_request")

    @app.patch("/api/counselor/cases/{case_id}/tasks/{task_id}")
    def update_task(case_id: str, task_id: str, body: TaskPatch, _p: dict = Depends(on_shift_writer)):
        try:
            return rt.workbench.update_task(case_id, task_id, body.status)
        except KeyError:
            raise HTTPException(404, "not_found")
        except InvalidRequest:
            raise HTTPException(422, "invalid_request")

    @app.post("/api/counselor/cases/{case_id}/notes")
    def add_note(case_id: str, body: NoteIn, p: dict = Depends(on_shift_writer)):
        try:
            return rt.workbench.add_note(case_id, p["counselor_id"], body.text)
        except KeyError:
            raise HTTPException(404, "not_found")
        except InvalidRequest:
            raise HTTPException(422, "invalid_request")

    @app.get("/api/config")
    def config():
        env = os.environ.get("DEPLOY_TARGET", "local")
        # AI draft paused until after deployment (coordinator priority change); provider null while disabled
        return {"ai_draft_enabled": False, "provider": None, "environment": env if env in ENVIRONMENTS else "local"}

    @app.post("/api/counselor/cases/{case_id}/closure")
    def closure(case_id: str, body: ClosureIn, p: dict = Depends(on_shift_writer)):
        try:
            return rt.workbench.closure(case_id, p["counselor_id"], body.summary)
        except KeyError:
            raise HTTPException(404, "not_found")
        except Conflict:
            raise HTTPException(409, "no_active_loop")
        except InvalidRequest:
            raise HTTPException(422, "invalid_request")

    # ------------------------------------------------------------------ loop
    @app.get("/api/loop/{couple_id}")
    def loop_get(couple_id: str, p: dict = Depends(any_reader)):
        own_couple(p, couple_id)
        if p["role"] == "partner":
            view = rt.portal.visible_loop(p["partner_id"])  # no escalation-specific states for uninvolved partners
            if view is None:
                raise HTTPException(404, "not_found")
            return view
        try:
            return rt.loop.get(couple_id)
        except LoopError:
            raise HTTPException(404, "not_found")

    @app.post("/api/loop/{couple_id}/advance")
    def loop_advance(couple_id: str, body: AdvanceIn, p: dict = Depends(on_shift_writer)):  # DECISIONS #50
        own_couple(p, couple_id)
        try:
            return rt.loop.advance(couple_id, body.to, actor_role="counselor")
        except ForbiddenTransition:
            raise HTTPException(403, "forbidden")
        except LoopError:
            raise HTTPException(409, "invalid_transition")

    return app


app = create_app()
