from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import runpy
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote, urlparse
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi import Path as ApiPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import get_settings
from .ingestion import (
    MAX_SOURCE_BYTES,
    IngestionError,
    extract_image_ocr,
    extract_pdf,
    structured_record_candidates,
)
from .integrations import (
    IntegrationFailure,
    create_document_embedding,
    create_embedding,
    generate_claims,
    retrieve_chunks,
    verify_supabase_session,
)
from .rag import (
    ambiguous_invoice,
    citation_from_row,
    insufficient_evidence,
    interpret_followup,
    normalize_question,
    prepare_generation_context,
    relevant_passage,
    small_talk,
    validate_generation,
    verified_evidence_response,
)
from .records import record_excerpt, validate_record

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
LOGGER = logging.getLogger("ps01_api")
DEMO_CREDENTIALS = REPOSITORY_ROOT / ".local-demo-credentials.json"
DEMO_ROLES = ("CEO", "Finance Manager", "HR Manager", "Sales Manager", "Engineer")
EVALUATION_RESULTS = REPOSITORY_ROOT / "data" / "local" / "evaluation.json"
EVALUATION_LOCK = asyncio.Lock()
PRIVATE_INGESTION = REPOSITORY_ROOT / "data" / "private" / "ingest"


@asynccontextmanager
async def lifespan(application):
    async with request_client() as client:
        application.state.http_client = client
        await drain_cleanup_jobs()
        yield
    application.state.http_client = None


@asynccontextmanager
async def request_client():
    client = getattr(app.state, "http_client", None)
    if client is not None:
        yield client
    else:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=5.0)) as temporary:
            yield temporary


app = FastAPI(
    lifespan=lifespan,
    title="Clearframe Knowledge API",
    version="0.2.0",
    description="Authenticated API for a multi-modal knowledge workspace.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Source-Name",
        "X-Access-Role",
        "X-Demo-Role",
    ],
)


@app.exception_handler(IntegrationFailure)
async def integration_failure_handler(_request: Request, exc: IntegrationFailure):
    LOGGER.warning("Integration failure [%s]: %s", exc.code, exc)
    messages = {
        "provider_unavailable": (
            "I couldn’t complete that answer just now. Your access permissions "
            "remain in place. Please try again shortly."
        ),
        "provider_rate_limited": (
            "I couldn’t complete that answer just now. Your access permissions "
            "remain in place. Please try again shortly."
        ),
        "provider_timeout": (
            "The answer took too long to complete. Your access permissions remain in "
            "place. Please try again shortly."
        ),
        "provider_invalid_response": (
            "The answer service returned an unusable response. Please retry."
        ),
        "retrieval_unavailable": "Authorized search is unavailable. No answer was generated.",
        "provider_authentication_failed": (
            "The answer service needs attention. Please contact your workspace administrator."
        ),
        "provider_invalid_model": (
            "The answer service needs attention. Please contact your workspace administrator."
        ),
        "provider_invalid_request": (
            "I couldn’t complete that answer. Please rephrase your question or "
            "contact your workspace administrator."
        ),
        "provider_safety_block": "The provider declined this request. No answer was released.",
        "session_expired": "Your session expired. Sign in again to continue.",
        "authorization_denied": "Your current access does not permit this action.",
        "migration_required": (
            "The workspace database schema is unavailable. "
            "Ask the administrator to apply local migrations."
        ),
        "database_unavailable": "The workspace database is temporarily unavailable. Please retry.",
        "evidence_changed": (
            "Source access or content changed during this request. "
            "Search again to use current evidence."
        ),
    }
    content: dict[str, object] = {
        "detail": messages.get(
            exc.code, "A workspace service is temporarily unavailable. Please retry."
        ),
        "code": exc.code,
    }
    if exc.stage == "embedding":
        content["stage"] = "embedding"
        content["detail"] = (
            "Embedding failed; the source was not published. "
            "Retry later or ask the administrator to check the provider configuration."
        )
    if exc.timing_ms is not None:
        content["timing_ms"] = exc.timing_ms
    if exc.retry_after is not None:
        content["retry_after_seconds"] = exc.retry_after
    if exc.provider_status:
        content["provider_status"] = exc.provider_status
    if exc.model_attempts:
        content["generation_attempts"] = exc.model_attempts
    LOGGER.warning(
        "Provider diagnostics code=%s status=%s retry_seconds=%s attempts=%s",
        exc.code,
        exc.provider_status,
        exc.retry_after,
        json.dumps(exc.model_attempts),
    )
    statuses = {
        "provider_rate_limited": 429,
        "session_expired": 401,
        "authorization_denied": 403,
        "provider_authentication_failed": 502,
        "provider_invalid_model": 502,
        "provider_invalid_request": 502,
        "provider_invalid_response": 502,
        "provider_safety_block": 422,
    }
    return JSONResponse(
        status_code=statuses.get(exc.code, 503),
        content=content,
        headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else {},
    )


@app.exception_handler(httpx.HTTPError)
async def upstream_http_error_handler(_request: Request, exc: httpx.HTTPError):
    LOGGER.warning("Upstream HTTP failure: %s", type(exc).__name__)
    return JSONResponse(
        status_code=503, content={"detail": "An upstream workspace service is unavailable"}
    )


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=2_000)
    conversation_id: UUID | None = None


class QueryResponse(BaseModel):
    request_id: str
    conversation_id: str | None = None
    message: str | None = None
    state: str
    claims: list[dict[str, object]]
    trace: dict[str, object]


class StructuredIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    table: str = Field(min_length=1, max_length=100)
    row_id: str = Field(min_length=1, max_length=200)
    source_name: str = Field(min_length=1, max_length=200)
    fields: dict[str, str | int | float | bool | None] = Field(min_length=1, max_length=100)
    access_role: str = Field(default="CEO", min_length=1, max_length=100)


def _local_demo_enabled() -> bool:
    settings = get_settings()
    hostname = urlparse(settings.supabase_url or "").hostname
    return hostname in {"localhost", "127.0.0.1", "::1"} and DEMO_CREDENTIALS.is_file()


def _rest_headers(settings, token: str) -> dict[str, str]:
    if not settings.supabase_publishable_key:
        raise IntegrationFailure("Supabase is not configured")
    return {
        "apikey": settings.supabase_publishable_key.get_secret_value(),
        "Authorization": f"Bearer {token}",
    }


async def _rest_rows(
    client: httpx.AsyncClient,
    settings,
    token: str,
    table: str,
    *,
    params: dict[str, str],
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    if not settings.supabase_url:
        raise IntegrationFailure("Supabase is not configured")
    response = await client.get(
        f"{settings.supabase_url.rstrip('/')}/rest/v1/{table}",
        params=params,
        headers=_rest_headers(settings, token) | (headers or {}),
    )
    if response.is_error:
        code = (
            "session_expired"
            if response.status_code == 401
            else "authorization_denied"
            if response.status_code == 403
            else "migration_required"
            if response.status_code == 404
            else "database_unavailable"
        )
        raise IntegrationFailure("Authorized workspace data is unavailable", code=code)
    return response


async def _identity(client: httpx.AsyncClient, settings, token: str) -> dict[str, object]:
    user = await verify_supabase_session(client, settings, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    user_id = str(user["id"])
    profile_response, role_response = await asyncio.gather(
        _rest_rows(
            client,
            settings,
            token,
            "profiles",
            params={
                "user_id": f"eq.{user_id}",
                "select": "user_id,organization_id,display_name",
                "limit": "1",
            },
        ),
        _rest_rows(
            client,
            settings,
            token,
            "user_roles",
            params={"user_id": f"eq.{user_id}", "select": "role_id,organization_id"},
        ),
    )
    profiles = profile_response.json()
    assignments = role_response.json()
    if not isinstance(profiles, list) or not profiles or not isinstance(assignments, list):
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable")
    role_ids = [
        str(item["role_id"])
        for item in assignments
        if isinstance(item, dict) and item.get("role_id")
    ]
    roles: list[str] = []
    if role_ids:
        role_response = await _rest_rows(
            client,
            settings,
            token,
            "roles",
            params={"id": f"in.({','.join(role_ids)})", "select": "id,name"},
        )
        rows = role_response.json()
        if isinstance(rows, list):
            roles = [
                str(row["name"])
                for row in rows
                if isinstance(row, dict) and isinstance(row.get("name"), str)
            ]
    if not roles:
        raise HTTPException(
            status_code=403, detail="No workspace role has been assigned to this account"
        )
    profile = profiles[0]
    return {
        "user_id": user_id,
        "email": str(user.get("email") or "Authenticated user"),
        "display_name": str(
            profile.get("display_name") or user.get("email") or "Authenticated user"
        ),
        "organization_id": str(profile["organization_id"]),
        "roles": roles,
        "role": roles[0] if roles else "Unassigned",
    }


def _append_activity(entry: dict[str, object]) -> None:
    activity = getattr(app.state, "activity", None)
    if activity is None:
        app.state.activity = []
        activity = app.state.activity
    activity.append(entry)
    del activity[:-100]


def _activity_for(user_id: str) -> list[dict[str, object]]:
    activity = getattr(app.state, "activity", [])
    return [entry for entry in reversed(activity) if entry.get("user_id") == user_id][:20]


async def _context_token(
    client: httpx.AsyncClient,
    settings,
    actor_token: str,
    identity: dict[str, object],
    requested_role: str | None,
) -> tuple[str, str]:
    """Resolve a server-authorized demo context to a role-scoped Supabase session."""
    role = requested_role or str(identity["role"])
    assigned_roles = identity.get("roles", [])
    if role == identity["role"]:
        return actor_token, role
    if role not in DEMO_ROLES or not isinstance(assigned_roles, list):
        raise HTTPException(
            status_code=403, detail="This demo role is not available to your identity"
        )
    if role not in assigned_roles and not (
        _local_demo_enabled() and identity["role"] == "CEO" and role in DEMO_ROLES
    ):
        raise HTTPException(
            status_code=403, detail="This demo role is not available to your identity"
        )
    if identity["role"] != "CEO" or not _local_demo_enabled():
        raise HTTPException(status_code=403, detail="Only the local demo CEO may switch contexts")

    # Demo infrastructure only. Bind every brokered session to this actor and
    # organization; verify the target's current membership on every reuse.
    try:
        credentials = json.loads(DEMO_CREDENTIALS.read_text())
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Demo context is unavailable") from exc
    target = credentials.get(role)
    actor = credentials.get(str(identity["role"]))
    if (
        not isinstance(target, dict)
        or not isinstance(actor, dict)
        or identity.get("email") != actor.get("email")
    ):
        raise HTTPException(status_code=403, detail="Demo context is unavailable")
    cache = getattr(app.state, "demo_role_sessions", {})
    cache_key = (str(identity["user_id"]), str(identity["organization_id"]), role)
    cached = cache.get(cache_key)
    if cached and cached["expires_at"] > time.monotonic() + 60:
        access_token = str(cached["access_token"])
    else:
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": settings.supabase_publishable_key.get_secret_value()},
            json={"email": target["email"], "password": target["password"]},
        )
        if response.is_error:
            raise HTTPException(status_code=503, detail="Local demo role session is unavailable")
        session = response.json()
        access_token = session.get("access_token")
        if not isinstance(access_token, str):
            raise HTTPException(status_code=503, detail="Local demo role session is invalid")
        cached = {
            "access_token": access_token,
            "expires_at": time.monotonic() + int(session.get("expires_in", 3600)),
        }
    target_identity = await _identity(client, settings, access_token)
    if (
        target_identity["organization_id"] != identity["organization_id"]
        or target_identity["role"] != role
        or target_identity.get("email") != target["email"]
    ):
        cache.pop(cache_key, None)
        raise HTTPException(status_code=403, detail="Demo context is unavailable")
    cache[cache_key] = cached
    app.state.demo_role_sessions = cache
    return access_token, role


def bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authentication required")
    return token.strip()


async def require_session(client: httpx.AsyncClient, authorization: str | None) -> str:
    token = bearer_token(authorization)
    settings = get_settings()
    try:
        user = await verify_supabase_session(client, settings, token)
    except (httpx.HTTPError, IntegrationFailure) as exc:
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return token


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/workspace", tags=["workspace"])
async def workspace_summary(
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    settings = get_settings()
    token = bearer_token(authorization)
    async with request_client() as client:
        identity = await _identity(client, settings, token)
        context_token, active_role = await _context_token(
            client, settings, token, identity, demo_role
        )
        organization_id = str(identity["organization_id"])
        docs_response, chunks_response, structured_response = await asyncio.gather(
            _rest_rows(
                client,
                settings,
                context_token,
                "documents",
                params={
                    "organization_id": f"eq.{organization_id}",
                    "select": "id,source_name,source_type,created_at,metadata",
                    "order": "created_at.desc",
                    "limit": "500",
                },
                headers={"Prefer": "count=exact", "Range": "0-499"},
            ),
            _rest_rows(
                client,
                settings,
                context_token,
                "knowledge_chunks",
                params={
                    "organization_id": f"eq.{organization_id}",
                    "select": "id,row_id",
                    "limit": "1",
                },
                headers={"Prefer": "count=exact", "Range": "0-0"},
            ),
            _rest_rows(
                client,
                settings,
                context_token,
                "knowledge_chunks",
                params={
                    "organization_id": f"eq.{organization_id}",
                    "source_type": "eq.structured",
                    "select": "row_id",
                    "limit": "5000",
                },
            ),
        )
        documents = docs_response.json()
        if not isinstance(documents, list):
            raise HTTPException(status_code=503, detail="Authorized source list is unavailable")
        content_range = chunks_response.headers.get("content-range", "*/0").rsplit("/", 1)[-1]
        chunk_count = int(content_range) if content_range.isdigit() else 0
    async with request_client() as client:
        history = await _history_rows(client, settings, token, identity, active_role)
        activity = await _rest_rows(
            client,
            settings,
            token,
            "security_events",
            params={
                "user_id": f"eq.{identity['user_id']}",
                "organization_id": f"eq.{identity['organization_id']}",
                "active_role": f"eq.{active_role}",
                "select": "kind,outcome,created_at",
                "order": "created_at.desc",
                "limit": "5",
            },
        )
    recent = [
        {
            "query": item["query"],
            "state": item["response"].get("state", "unknown"),
            "created_at": item["created_at"],
        }
        for item in reversed(history)
    ]
    latest_evaluation_status = "not run"
    if EVALUATION_RESULTS.is_file():
        try:
            saved_evaluation = json.loads(EVALUATION_RESULTS.read_text())
            latest_evaluation_status = (
                "recorded pass (not freshly run)"
                if evaluation_checks_passed(saved_evaluation)
                else "recorded review (not freshly run)"
            )
        except (OSError, ValueError, AttributeError):
            latest_evaluation_status = "unavailable"
    return {
        "identity": identity,
        "active_role": active_role,
        "document_count": int(docs_response.headers.get("content-range", "*/0").rsplit("/", 1)[-1])
        if docs_response.headers.get("content-range", "").rsplit("/", 1)[-1].isdigit()
        else len(documents),
        "chunk_count": chunk_count,
        "structured_record_count": len(
            {
                row.get("row_id")
                for row in structured_response.json()
                if isinstance(row, dict) and row.get("row_id")
            }
        ),
        "documents": documents,
        "security_activity": activity.json(),
        "recent_queries": [
            {
                "query": item.get("query"),
                "state": item.get("state"),
                "created_at": item.get("created_at"),
            }
            for item in recent
        ],
        "authorization": "active" if identity["role"] != "Unassigned" else "unassigned",
        "api": "connected",
        "supabase": "connected",
        "gemini": (
            getattr(app.state, "provider_status", {}).get("state")
            or (
                "configured; availability not checked"
                if settings.gemini_api_key
                else "not configured"
            )
        ),
        "provider_check": getattr(app.state, "provider_status", None),
        "ingestion": "ready"
        if _local_demo_enabled() and settings.supabase_secret_key
        else "local admin key unavailable",
        "evaluation": "available" if _local_demo_enabled() else "local demo unavailable",
        "latest_evaluation_status": latest_evaluation_status,
        "demo_switch_available": _local_demo_enabled() and identity["role"] == "CEO",
    }


@app.get("/api/v1/security", tags=["security"])
async def security_status(
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    settings = get_settings()
    token = bearer_token(authorization)
    async with request_client() as client:
        identity = await _identity(client, settings, token)
        _, active_role = await _context_token(client, settings, token, identity, demo_role)
    async with request_client() as client:
        events = await _rest_rows(
            client,
            settings,
            token,
            "security_events",
            params={
                "user_id": f"eq.{identity['user_id']}",
                "organization_id": f"eq.{identity['organization_id']}",
                "active_role": f"eq.{active_role}",
                "select": "id,kind,outcome,evidence_count,created_at,active_role",
                "order": "created_at.desc",
                "limit": "30",
            },
        )
    trace = [
        {
            "created_at": item["created_at"],
            "query_id": item["id"],
            "state": item["outcome"],
            "active_role": item["active_role"],
            "authorized_evidence_count": item.get("evidence_count"),
            "decision": f"{item['kind']}: {item['outcome']}",
        }
        for item in events.json()
    ]
    return {
        "identity": identity,
        "active_role": active_role,
        "effective_scope": f"{active_role} demo context: organization records granted to that role",
        "trace": trace,
        "security_tests": {
            "user_session_required": "enforced",
            "database_row_level_security": "configured; status not checked by this endpoint",
            "unauthorized_evidence_to_model": "not independently measured in this trace",
            "basis": (
                "Retrieval uses a server-authorized role session; the model receives only rows "
                "returned under that session's RLS policies."
            ),
        },
    }


@app.get("/api/v1/sources", tags=["sources"])
async def list_sources(
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    summary = await workspace_summary(authorization, demo_role)
    return {
        "identity": summary["identity"],
        "sources": summary["documents"],
        "count": summary["document_count"],
    }


@app.get("/api/v1/evaluation", tags=["evaluation"])
async def get_evaluation(
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    settings = get_settings()
    async with request_client() as client:
        token = await require_session(client, authorization)
        identity = await _identity(client, settings, token)
        _, role = await _context_token(client, settings, token, identity, demo_role)
    if role != "CEO" or not _local_demo_enabled():
        return {"state": "restricted", "result": None}
    if EVALUATION_RESULTS.is_file():
        try:
            result = json.loads(EVALUATION_RESULTS.read_text())
            if not isinstance(result, dict):
                return {"state": "unavailable", "result": None}
            if not isinstance(result.get("results"), list):
                return {"state": "unavailable", "result": None}
            return {
                "state": "completed",
                "result": recorded_evaluation(result) | {"history": evaluation_history()},
            }
        except (OSError, ValueError):
            return {"state": "unavailable", "result": None}
    return {"state": "not_run", "result": None}


def evaluation_checks_passed(result: dict[str, object]) -> bool:
    rows = result.get("results")
    return (
        result.get("authorization_violations") == 0
        and isinstance(rows, list)
        and bool(rows)
        and all(isinstance(row, dict) and row.get("hit") is True for row in rows)
    )


def recorded_evaluation(result: dict[str, object]) -> dict[str, object]:
    """Relabel legacy metrics without modifying or claiming to rerun saved data."""
    saved = dict(result)
    saved["run_kind"] = (
        "recorded_local" if saved.get("schema_version") == 2 else "historical_legacy"
    )
    if "retrieval_recall_at_k" in saved:
        saved["retrieval_hit_rate_at_k"] = saved.pop("retrieval_recall_at_k")
    checks = dict(saved.get("measured_checks") or {})
    for old, new in (
        ("citation_provenance_valid", "retrieved_citation_locations_present"),
        ("citation_provenance_checked", "retrieved_citation_locations_checked"),
    ):
        if old in checks:
            checks[new] = checks.pop(old)
    saved["measured_checks"] = checks
    return saved


def evaluation_history():
    history = []
    for path in sorted(EVALUATION_RESULTS.parent.glob("evaluation-history-*.json"), reverse=True)[
        :10
    ]:
        try:
            saved = json.loads(path.read_text())
            if not isinstance(saved, dict) or not isinstance(saved.get("results"), list):
                continue
            history.append(
                {
                    key: saved.get(key)
                    for key in (
                        "completed_at",
                        "dataset",
                        "query_count",
                        "execution_origin",
                        "run_id",
                    )
                }
            )
        except (OSError, ValueError):
            continue
    return history


def _atomic_evaluation_write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
            stream.flush()
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


class DemoSwitchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: str = Field(min_length=1, max_length=100)


async def require_local_ceo(
    client: httpx.AsyncClient, authorization: str | None, demo_role: str | None = None
) -> tuple[str, dict[str, object]]:
    settings = get_settings()
    if not _local_demo_enabled() or not settings.supabase_secret_key:
        raise HTTPException(status_code=404, detail="Local demo administration is unavailable")
    token = await require_session(client, authorization)
    identity = await _identity(client, settings, token)
    _, active_role = await _context_token(client, settings, token, identity, demo_role)
    if identity["role"] != "CEO" or active_role != "CEO":
        raise HTTPException(status_code=403, detail="CEO role required for this local demo action")
    return token, identity


@app.post("/api/v1/demo/switch", tags=["demo"])
async def switch_demo_user(
    request: DemoSwitchRequest,
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    if request.role not in DEMO_ROLES or not _local_demo_enabled():
        raise HTTPException(status_code=404, detail="Local demo user switching is unavailable")
    async with request_client() as client:
        actor_token = bearer_token(authorization)
        settings = get_settings()
        actor_identity = await _identity(client, settings, actor_token)
        await _context_token(client, settings, actor_token, actor_identity, request.role)
        if actor_identity["role"] != "CEO" and request.role != actor_identity["role"]:
            raise HTTPException(status_code=403, detail="Only a CEO identity can change demo roles")
    return {"active_role": request.role}


async def _store_ingested(
    client: httpx.AsyncClient,
    settings,
    identity: dict[str, object],
    source_id: str,
    source_name: str,
    source_type: str,
    content_hash: str,
    candidates,
    access_role: str,
    storage_path: str | None,
) -> dict[str, object]:
    if access_role not in DEMO_ROLES:
        raise HTTPException(status_code=422, detail="Choose one of the configured demo roles")
    key = settings.supabase_secret_key.get_secret_value()
    base = f"{settings.supabase_url.rstrip('/')}/rest/v1"
    admin_headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    organization_id = str(identity["organization_id"])
    role_response = await client.get(
        f"{base}/roles",
        params={
            "organization_id": f"eq.{organization_id}",
            "name": f"eq.{access_role}",
            "select": "id",
            "limit": "1",
        },
        headers=admin_headers,
    )
    if role_response.is_error or not role_response.json():
        raise HTTPException(status_code=503, detail="The selected access role is unavailable")
    role_id = str(role_response.json()[0]["id"])
    doc_headers = admin_headers | {
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    doc_payload = {
        "id": source_id,
        "organization_id": organization_id,
        "source_type": source_type,
        "source_name": source_name,
        "storage_path": storage_path,
        "content_hash": content_hash,
        "metadata": {
            "ingestion": "local-demo",
            "chunk_count": len(candidates),
            **({"table": candidates[0].metadata["table"]} if source_type == "structured" else {}),
        },
        "created_by": str(identity["user_id"]),
    }
    document_response = await client.post(
        f"{base}/documents", headers=doc_headers, json=[doc_payload]
    )
    if document_response.is_error:
        raise HTTPException(
            status_code=409 if document_response.status_code == 409 else 503,
            detail="Document could not be indexed",
        )
    if source_type == "structured":
        fields = candidates[0].metadata["fields"]
        table = candidates[0].metadata["table"]
        row_response = await client.post(
            f"{base}/{table}",
            headers=doc_headers,
            json=[
                {
                    **fields,
                    "organization_id": organization_id,
                    "document_id": source_id,
                }
            ],
        )
        if row_response.is_error:
            await client.delete(
                f"{base}/documents", params={"id": f"eq.{source_id}"}, headers=admin_headers
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    "Record violates the table contract. "
                    "Check required fields, references, and business key."
                ),
            )
        persisted = row_response.json()[0]
        fields = {
            key: value
            for key, value in persisted.items()
            if key not in {"organization_id", "document_id"}
        }
        candidates = [
            type(candidate)(
                **{
                    **candidate.__dict__,
                    "content": record_excerpt(table, candidate.row_id, fields),
                    "metadata": {"table": table, "fields": fields},
                }
            )
            for candidate in candidates
        ]
    semaphore = asyncio.Semaphore(3)

    async def embed(candidate):
        async with semaphore:
            return await create_document_embedding(client, settings, source_name, candidate.content)

    try:
        embeddings = await asyncio.gather(*(embed(candidate) for candidate in candidates))
    except (IntegrationFailure, httpx.HTTPError) as exc:
        await client.delete(
            f"{base}/documents", params={"id": f"eq.{source_id}"}, headers=admin_headers
        )
        if isinstance(exc, IntegrationFailure):
            exc.stage = "embedding"
            raise
        failure = IntegrationFailure(
            "Embedding transport failed",
            code="provider_timeout"
            if isinstance(exc, httpx.TimeoutException)
            else "provider_unavailable",
        )
        failure.stage = "embedding"
        raise failure from exc
    chunk_payload = []
    for candidate, embedding in zip(candidates, embeddings, strict=True):
        chunk_payload.append(
            {
                "organization_id": organization_id,
                "document_id": source_id,
                "source_type": candidate.source_type,
                "source_name": source_name,
                "source_id": candidate.source_id,
                "page_number": candidate.page_number,
                "row_id": candidate.row_id,
                "image_id": candidate.image_id,
                "ocr_region": candidate.ocr_region,
                "chunk_index": candidate.chunk_index,
                "content": candidate.content,
                "metadata": candidate.metadata or {},
                "embedding": f"[{','.join(str(value) for value in embedding)}]",
            }
        )
    chunks_response = await client.post(
        f"{base}/knowledge_chunks", headers=doc_headers, json=chunk_payload
    )
    if chunks_response.is_error:
        await client.delete(
            f"{base}/documents", params={"id": f"eq.{source_id}"}, headers=admin_headers
        )
        raise HTTPException(status_code=503, detail="Document chunks could not be indexed")
    chunk_rows = chunks_response.json()
    grants = [
        {
            "organization_id": organization_id,
            "document_id": source_id,
            "principal_type": "role",
            "principal_id": role_id,
            "can_read": True,
        }
    ]
    if access_role != "CEO":
        ceo = await client.get(
            f"{base}/roles",
            headers=admin_headers,
            params={
                "organization_id": f"eq.{organization_id}",
                "name": "eq.CEO",
                "select": "id",
                "limit": "1",
            },
        )
        if ceo.is_error or not ceo.json():
            await client.delete(
                f"{base}/documents", params={"id": f"eq.{source_id}"}, headers=admin_headers
            )
            raise HTTPException(status_code=503, detail="CEO access policy is unavailable")
        grants.append({**grants[0], "principal_id": ceo.json()[0]["id"]})
    grant_response = await client.post(f"{base}/access_grants", headers=doc_headers, json=grants)
    if grant_response.is_error:
        await client.delete(
            f"{base}/documents", params={"id": f"eq.{source_id}"}, headers=admin_headers
        )
        raise HTTPException(status_code=503, detail="Document access policy could not be saved")
    return {
        "document_id": source_id,
        "source_name": source_name,
        "source_type": source_type,
        "chunks_indexed": len(chunk_rows),
        "access_role": access_role,
    }


@app.post("/api/v1/ingest/file", tags=["ingestion"])
async def ingest_file(
    request: Request,
    authorization: str | None = Header(default=None),
    source_name: str = Header(alias="X-Source-Name"),
    access_role: str = Header(default="CEO", alias="X-Access-Role"),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    settings = get_settings()
    if not _local_demo_enabled() or not settings.supabase_secret_key:
        raise HTTPException(status_code=404, detail="Local ingestion is unavailable")
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0)) as auth_client:
        _, identity = await require_local_ceo(auth_client, authorization, demo_role)
    raw_name = unquote(source_name)
    safe_name = Path(raw_name.replace("\\", "/")).name
    if (
        not safe_name
        or safe_name != raw_name.replace("\\", "/").split("/")[-1]
        or len(safe_name) > 200
    ):
        raise HTTPException(status_code=422, detail="Source filename is invalid")
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=415, detail="Upload a PDF, PNG, or JPEG source")
    data = bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data) > MAX_SOURCE_BYTES:
            raise HTTPException(status_code=413, detail="Source exceeds the 25 MB limit")
    if not data:
        raise HTTPException(status_code=422, detail="Source file is empty")
    source_id = str(uuid4())
    PRIVATE_INGESTION.mkdir(parents=True, exist_ok=True, mode=0o700)
    PRIVATE_INGESTION.chmod(0o700)
    stored_path = PRIVATE_INGESTION / f"{source_id}{suffix}"
    stored_path.write_bytes(data)
    stored_path.chmod(0o600)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0)) as client:
            try:
                candidates = await asyncio.to_thread(
                    extract_pdf if suffix == ".pdf" else extract_image_ocr,
                    stored_path,
                    source_id,
                )
            except IngestionError as exc:
                stored_path.unlink(missing_ok=True)
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            if not candidates:
                stored_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=422, detail="No searchable text was found in this source"
                )
            result = await _store_ingested(
                client,
                settings,
                identity,
                source_id,
                safe_name,
                candidates[0].source_type,
                hashlib.sha256(data).hexdigest(),
                candidates,
                access_role,
                str(stored_path.relative_to(REPOSITORY_ROOT)),
            )
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise
    except IntegrationFailure:
        stored_path.unlink(missing_ok=True)
        raise
    except httpx.HTTPError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="Ingestion service is unavailable") from exc
    return {"state": "indexed", **result}


@app.post("/api/v1/ingest/structured", tags=["ingestion"])
async def ingest_structured(
    request: StructuredIngestRequest,
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    settings = get_settings()
    if not _local_demo_enabled() or not settings.supabase_secret_key:
        raise HTTPException(status_code=404, detail="Local ingestion is unavailable")
    source_id = str(uuid4())
    try:
        validate_record(request.table, request.row_id, request.fields)
        candidates = structured_record_candidates(
            table_name=request.table,
            row_id=request.row_id,
            source_name=request.source_name,
            fields=request.fields,
            source_id=source_id,
        )
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0)) as client:
        _, identity = await require_local_ceo(client, authorization, demo_role)
        result = await _store_ingested(
            client,
            settings,
            identity,
            source_id,
            request.source_name,
            "structured",
            hashlib.sha256(json.dumps(request.fields, sort_keys=True).encode()).hexdigest(),
            candidates,
            request.access_role,
            None,
        )
    return {"state": "indexed", **result}


@app.post("/api/v1/evaluation/run", tags=["evaluation"])
async def run_evaluation(
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    if not _local_demo_enabled():
        raise HTTPException(status_code=404, detail="Local evaluation is unavailable")
    async with request_client() as client:
        token, identity = await require_local_ceo(client, authorization, demo_role)
    if EVALUATION_LOCK.locked():
        raise HTTPException(
            status_code=409, detail="An evaluation is already running. Refresh shortly."
        )
    try:
        async with EVALUATION_LOCK:
            started = time.perf_counter()
            async with request_client() as client:
                counts = {}
                for table in ("documents", "knowledge_chunks", "structured_records"):
                    response = await _rest_rows(
                        client,
                        get_settings(),
                        token,
                        table,
                        params={
                            "select": "row_id" if table == "structured_records" else "id",
                            "limit": "1",
                            "organization_id": f"eq.{identity['organization_id']}",
                        },
                        headers={"Prefer": "count=exact"},
                    )
                    counts[table] = int(response.headers["content-range"].rsplit("/", 1)[-1])
            module = runpy.run_path(
                str(REPOSITORY_ROOT / "apps" / "api" / "scripts" / "evaluate_local_retrieval.py")
            )
            async with asyncio.timeout(120):
                result = await module["run"]()
            result.update(
                {
                    "completed_at": datetime.now(UTC).isoformat(),
                    "execution_origin": "app",
                    "run_id": str(uuid4()),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "corpus": counts,
                }
            )
            if EVALUATION_RESULTS.is_file():
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
                archive = EVALUATION_RESULTS.with_name(f"evaluation-history-{stamp}.json")
                _atomic_evaluation_write(archive, EVALUATION_RESULTS.read_bytes())
            _atomic_evaluation_write(
                EVALUATION_RESULTS, (json.dumps(result, indent=2) + "\n").encode()
            )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Evaluation failed; no result was saved"
        ) from exc
    return {
        "state": "completed",
        "result": result | {"run_kind": "fresh_local", "history": evaluation_history()},
    }


@app.post("/api/v1/chat/query", response_model=QueryResponse, tags=["chat"])
async def query_knowledge(
    request: QueryRequest,
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> QueryResponse:
    return await _run_query(request, authorization, demo_role)


async def revalidate_evidence(client, settings, token, evidence):
    if not evidence:
        return []
    ids = [str(UUID(str(row["chunk_id"]))) for row in evidence]
    response = await _rest_rows(
        client,
        settings,
        token,
        "knowledge_chunks",
        params={
            "id": f"in.({','.join(ids)})",
            "select": "id,content,source_name,source_type,source_id,document_id,metadata,"
            "page_number,row_id,image_id,ocr_region",
            "limit": "100",
        },
    )
    current = {row["id"]: row for row in response.json()}
    # Drop changed rows as well as revoked/deleted rows. No stale snapshot is sent.
    return [
        row
        for row in evidence
        if row["chunk_id"] in current
        and all(
            row.get(key) == current[row["chunk_id"]].get(key)
            for key in (
                "content",
                "source_name",
                "source_type",
                "source_id",
                "document_id",
                "page_number",
                "row_id",
                "image_id",
                "ocr_region",
                "metadata",
            )
        )
    ]


async def _run_query(request, authorization, demo_role, emit=None, verified=None):
    async def progress(stage):
        if emit:
            await emit({"stage": stage})

    request_id = str(uuid4())
    settings = get_settings()
    fallback_used = False
    model_output = {}
    provider_failure = None
    sent_evidence_count = 0
    final_access_checked = False
    effective_query = normalize_question(request.query)
    clarification = None
    request_started = verified[3] if verified else time.perf_counter()
    preliminary_auth_ms = (time.perf_counter() - request_started) * 1000 if verified else 0
    timings: dict[str, float | None] = {
        "auth_session_ms": 0.0,
        "embedding_ms": None,
        "retrieval_and_ranking_ms": None,
        "ranking_only_ms": None,
        "gemini_ms": None,
        "citation_validation_ms": None,
    }

    async with request_client() as client:
        try:
            auth_started = time.perf_counter()
            try:
                await progress("checking_access")
                actor_token = bearer_token(authorization)
                if verified:
                    identity, access_token, active_role = verified[:3]
                else:
                    identity = await _identity(client, settings, actor_token)
                    access_token, active_role = await _context_token(
                        client, settings, actor_token, identity, demo_role
                    )
                rows = []
                if request.conversation_id:
                    rows = await _history_rows(
                        client,
                        settings,
                        actor_token,
                        identity,
                        active_role,
                        conversation_id=str(request.conversation_id),
                    )
                    if not rows:
                        raise HTTPException(status_code=404, detail="Conversation not found")
                await progress("access_checked")
            finally:
                timings["auth_session_ms"] = round(
                    preliminary_auth_ms + (time.perf_counter() - auth_started) * 1000, 1
                )
            greeting = small_talk(request.query)
            if greeting:
                response = QueryResponse(
                    request_id=request_id,
                    conversation_id=str(request.conversation_id or uuid4()),
                    state="SMALL_TALK",
                    message=greeting,
                    claims=[],
                    trace={
                        "active_role": active_role,
                        "session_verified": True,
                        "database_request_used_user_session": False,
                        "evidence_items_sent_to_model": 0,
                        "generation_model": None,
                        "fallback_used": False,
                        "timing_ms": timings,
                        "ranking_timing_note": (
                            "No company data or model was used for this greeting."
                        ),
                    },
                )
                response.trace["history_saved"] = await _save_history(
                    actor_token, identity, active_role, request.query, response
                )
                response.trace["timing_ms"]["total_ms"] = round(
                    (time.perf_counter() - request_started) * 1000, 1
                )
                return response
            effective_query, clarification = interpret_followup(request.query, [])
            if clarification and rows:
                recent = await _recent_referents(client, settings, access_token, rows)
                effective_query, clarification = interpret_followup(request.query, recent)
            if clarification:
                response = QueryResponse(
                    request_id=request_id,
                    conversation_id=str(request.conversation_id or uuid4()),
                    state="CLARIFICATION_NEEDED",
                    message=clarification,
                    claims=[],
                    trace={
                        "active_role": active_role,
                        "session_verified": True,
                        "database_request_used_user_session": True,
                        "evidence_items_sent_to_model": 0,
                        "generation_model": None,
                        "fallback_used": False,
                        "timing_ms": timings,
                    },
                )
                response.trace["history_saved"] = await _save_history(
                    actor_token, identity, active_role, request.query, response
                )
                return response
            await progress("searching_knowledge")
            embedding_started = time.perf_counter()
            try:
                embedding = await create_embedding(client, settings, effective_query)
            finally:
                timings["embedding_ms"] = round((time.perf_counter() - embedding_started) * 1000, 1)
            retrieval_started = time.perf_counter()
            try:
                evidence = await retrieve_chunks(
                    client, settings, access_token, effective_query, embedding
                )
            finally:
                timings["retrieval_and_ranking_ms"] = round(
                    (time.perf_counter() - retrieval_started) * 1000, 1
                )
            await progress("retrieval_complete")
            await progress("checking_references")
            recheck_started = time.perf_counter()
            evidence = await revalidate_evidence(client, settings, access_token, evidence)
            timings["evidence_revalidation_ms"] = round(
                (time.perf_counter() - recheck_started) * 1000, 1
            )
            prompt, model_context = prepare_generation_context(effective_query, evidence)
            if ambiguous_invoice(effective_query, evidence):
                clarification = "Which invoice do you mean? Please include its invoice ID."
                result = {"state": "CLARIFICATION_NEEDED", "message": clarification, "claims": []}
                model_context = []
                generation_model = None
            elif not model_context or not any(
                relevant_passage(effective_query, row) for row in model_context
            ):
                result = insufficient_evidence()
                model_context: list[dict[str, object]] = []
                generation_model = None
            else:
                await progress("evidence_selected")
                await progress("generating_response")
                generation_started = time.perf_counter()
                try:

                    async def current_evidence():
                        current_identity = await _identity(client, settings, actor_token)
                        scoped, current_role = await _context_token(
                            client, settings, actor_token, current_identity, demo_role
                        )
                        if (
                            current_identity["user_id"] != identity["user_id"]
                            or current_identity["organization_id"] != identity["organization_id"]
                            or current_role != active_role
                        ):
                            raise HTTPException(status_code=403, detail="Access context changed")
                        return await revalidate_evidence(client, settings, scoped, evidence)

                    async def before_attempt():
                        nonlocal model_context, sent_evidence_count
                        fresh = await current_evidence()
                        new_prompt, model_context = prepare_generation_context(
                            effective_query, fresh
                        )
                        if not any(relevant_passage(effective_query, row) for row in model_context):
                            raise IntegrationFailure(
                                "Evidence changed before generation", code="evidence_changed"
                            )
                        sent_evidence_count = len(model_context)
                        return new_prompt

                    try:
                        model_output = await generate_claims(
                            client, settings, prompt, before_attempt=before_attempt
                        )
                    except IntegrationFailure as exc:
                        if exc.code not in {
                            "provider_unavailable",
                            "provider_timeout",
                            "provider_rate_limited",
                        }:
                            raise
                        provider_failure = exc
                finally:
                    timings["gemini_ms"] = round(
                        (time.perf_counter() - generation_started) * 1000, 1
                    )
                generation_model = model_output.get("_model")
                app.state.provider_status = {
                    "state": provider_failure.code if provider_failure else "available",
                    "model": generation_model,
                    "checked_at": datetime.now(UTC).isoformat(),
                }
                fallback_used = model_output.get("_fallback_used") is True
                await progress("checking_final_access")
                final_started = time.perf_counter()
                fresh = await current_evidence()
                _, model_context = prepare_generation_context(effective_query, fresh)
                final_access_checked = True
                timings["final_evidence_revalidation_ms"] = round(
                    (time.perf_counter() - final_started) * 1000, 1
                )
                if provider_failure:
                    await progress("composing_verified_evidence")
                await progress("validating_citations")
                validation_started = time.perf_counter()
                try:
                    if provider_failure:
                        result = verified_evidence_response(effective_query, model_context)
                        if not result["claims"]:
                            # Keep the precise provider error when safe extraction
                            # cannot support a complete answer.
                            raise provider_failure
                    else:
                        result = validate_generation(model_output, model_context)
                finally:
                    timings["citation_validation_ms"] = round(
                        (time.perf_counter() - validation_started) * 1000, 1
                    )
        except httpx.TimeoutException as exc:
            LOGGER.warning("Knowledge request timed out [%s]", request_id)
            raise HTTPException(status_code=503, detail="Knowledge service timed out") from exc
        except httpx.HTTPError as exc:
            LOGGER.warning("Knowledge upstream failed [%s]: %s", request_id, type(exc).__name__)
            raise HTTPException(status_code=503, detail="Knowledge service unavailable") from exc
        except IntegrationFailure as exc:
            if exc.code.startswith("provider_"):
                app.state.provider_status = {
                    "state": exc.code,
                    "checked_at": datetime.now(UTC).isoformat(),
                }
            if "identity" in locals() and "active_role" in locals():
                await record_security_event(
                    identity, active_role, "query", exc.code, len(locals().get("model_context", []))
                )
            # Only the post-provider recheck may supply error source links. A
            # failed check must not release stale titles/excerpts from the prompt.
            exc.evidence = (
                [citation_from_row(row) for row in model_context] if final_access_checked else []
            )
            exc.timing_ms = timings | {
                "total_ms": round((time.perf_counter() - request_started) * 1000, 1)
            }
            LOGGER.warning(
                "Ask failed [%s] code=%s timing_ms=%s",
                request_id,
                exc.code,
                json.dumps(exc.timing_ms, sort_keys=True),
            )
            raise

    await record_security_event(identity, active_role, "query", result["state"], len(model_context))
    created_at = datetime.now(UTC).isoformat()
    _append_activity(
        {
            "user_id": str(identity["user_id"]),
            "request_id": request_id,
            "query": request.query,
            "state": result["state"],
            "created_at": created_at,
            "evidence_count": len(model_context),
            "active_role": active_role,
            "timing_ms": timings,
        }
    )

    conversation_id = str(request.conversation_id or uuid4())
    await progress("validation_complete")
    response = QueryResponse(
        request_id=request_id,
        conversation_id=conversation_id,
        state=result["state"],
        message=(
            (
                "Verified evidence response: composed from your sources without a "
                "language model. Open citations to inspect the evidence."
            )
            if provider_failure
            else clarification
        ),
        claims=result["claims"],
        trace={
            "session_verified": True,
            "database_request_used_user_session": True,
            "evidence_items_sent_to_model": sent_evidence_count,
            "generation_model": generation_model,
            "fallback_used": fallback_used,
            "generation_attempts": (
                provider_failure.model_attempts
                if provider_failure
                else model_output.get("_attempts", [])
            ),
            "response_mode": (
                "verified_evidence"
                if provider_failure
                else "model_generated"
                if result["claims"]
                else "abstention"
            ),
            "provider_failure": (
                {
                    "code": provider_failure.code,
                    "provider_status": provider_failure.provider_status,
                    "retry_after_seconds": provider_failure.retry_after,
                }
                if provider_failure
                else None
            ),
            "active_role": active_role,
            "timing_ms": timings
            | {"total_ms": round((time.perf_counter() - request_started) * 1000, 1)},
            "ranking_timing_note": (
                "Ranking runs inside the database retrieval RPC; no separate server timing "
                "is exposed."
            ),
        },
    )
    history_started = time.perf_counter()
    saved = await _save_history(actor_token, identity, active_role, request.query, response)
    response.trace["history_saved"] = saved
    response.trace["timing_ms"]["history_persistence_ms"] = round(
        (time.perf_counter() - history_started) * 1000, 1
    )
    response.trace["timing_ms"]["total_ms"] = round(
        (time.perf_counter() - request_started) * 1000, 1
    )
    return response


async def record_security_event(identity, role, kind, outcome, evidence_count=None):
    settings = get_settings()
    if not settings.supabase_secret_key:
        return False
    key = settings.supabase_secret_key.get_secret_value()
    try:
        async with request_client() as client:
            response = await client.post(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/security_events",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                json={
                    "user_id": identity["user_id"],
                    "organization_id": identity["organization_id"],
                    "active_role": role,
                    "kind": kind,
                    "outcome": outcome,
                    "evidence_count": evidence_count,
                },
            )
        return not response.is_error
    except (httpx.HTTPError, IntegrationFailure):
        LOGGER.warning("Security event persistence unavailable")
        return False


@app.middleware("http")
async def audit_workspace_actions(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    kind = (
        "source_read"
        if path.startswith("/api/v1/sources/")
        else "ingestion"
        if path.startswith("/api/v1/ingest/")
        else "context_switch"
        if path == "/api/v1/demo/switch"
        else None
    )
    if kind and request.headers.get("authorization"):
        try:
            async with request_client() as client:
                token = bearer_token(request.headers.get("authorization"))
                identity = await _identity(client, get_settings(), token)
                requested = request.headers.get("x-demo-role")
                try:
                    _, role = await _context_token(
                        client, get_settings(), token, identity, requested
                    )
                except HTTPException as exc:
                    if exc.status_code != 403:
                        raise
                    # Attribute a denied context request to the verified actor's
                    # real role, never the forged requested context.
                    role = str(identity["role"])
            await record_security_event(
                identity,
                role,
                kind,
                "allowed" if response.status_code < 400 else "denied_or_failed",
            )
        except (HTTPException, IntegrationFailure, httpx.HTTPError):
            pass  # Never attribute an unverified identity or supplied role to an event.
    return response


async def cleanup_source_original(client, settings, source_id, storage_path):
    if storage_path:
        path = (REPOSITORY_ROOT / storage_path).resolve()
        # Immutable synthetic seed fixtures are retained; uploads are private and disposable.
        if path.is_relative_to(PRIVATE_INGESTION.resolve()):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                return False
    key = settings.supabase_secret_key.get_secret_value()
    response = await client.patch(
        f"{settings.supabase_url.rstrip('/')}/rest/v1/source_cleanup_jobs",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        params={"source_id": f"eq.{source_id}"},
        json={"state": "complete"},
    )
    return not response.is_error


async def drain_cleanup_jobs():
    settings = get_settings()
    if not _local_demo_enabled() or not settings.supabase_secret_key:
        return
    key = settings.supabase_secret_key.get_secret_value()
    try:
        async with request_client() as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/source_cleanup_jobs",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                params={"state": "eq.pending", "select": "source_id,storage_path", "limit": "100"},
            )
            if not response.is_error:
                for job in response.json():
                    await cleanup_source_original(
                        client, settings, job["source_id"], job["storage_path"]
                    )
    except (httpx.HTTPError, IntegrationFailure):
        LOGGER.warning("Private original cleanup deferred")


@app.delete("/api/v1/sources/{source_id}", tags=["sources"])
async def delete_source(
    source_id: Annotated[UUID, ApiPath()],
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
):
    settings = get_settings()
    async with request_client() as client:
        _, identity = await require_local_ceo(client, authorization, demo_role)
        key = settings.supabase_secret_key.get_secret_value()
        response = await client.post(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/delete_local_source",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            json={
                "target_source": str(source_id),
                "target_org": identity["organization_id"],
                "actor": identity["user_id"],
            },
        )
        if response.is_error:
            if response.status_code == 409:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "This source has dependent business records. Remove those sources first."
                    ),
                )
            raise IntegrationFailure("Source deletion is unavailable", code="database_unavailable")
        deleted = response.json()
        if deleted is None:
            raise HTTPException(status_code=404, detail="Source not found")
        cleaned = await cleanup_source_original(
            client, settings, str(source_id), deleted.get("storage_path")
        )
    return {"state": "deleted", "original_cleanup": "complete" if cleaned else "pending"}


@app.get("/api/v1/sources/{source_id}", tags=["sources"])
async def get_source(
    source_id: Annotated[UUID, ApiPath()],
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Source service unavailable")

    async with request_client() as client:
        actor_token = await require_session(client, authorization)
        identity = await _identity(client, settings, actor_token)
        access_token, _ = await _context_token(client, settings, actor_token, identity, demo_role)
        try:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/knowledge_chunks",
                params={
                    "id": f"eq.{source_id}",
                    "select": (
                        "id,source_type,source_name,source_id,page_number,row_id,image_id,"
                        "ocr_region,content,document_id,metadata"
                    ),
                    "limit": "1",
                },
                headers={
                    "apikey": settings.supabase_publishable_key.get_secret_value(),
                    "Authorization": f"Bearer {access_token}",
                },
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=503, detail="Source service timed out") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Source service unavailable") from exc

    if response.is_error:
        raise HTTPException(status_code=503, detail="Source service unavailable")
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Source not found")
    return await _source_payload(rows[0], authorization, demo_role)


@app.get("/api/v1/sources/{source_id}/preview", tags=["sources"])
async def get_source_preview(
    source_id: Annotated[UUID, ApiPath()],
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    """Open the first RLS-visible chunk belonging to an authorized source."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Source service unavailable")

    async with request_client() as client:
        actor_token = await require_session(client, authorization)
        identity = await _identity(client, settings, actor_token)
        access_token, _ = await _context_token(client, settings, actor_token, identity, demo_role)
        try:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/knowledge_chunks",
                params={
                    "document_id": f"eq.{source_id}",
                    "select": (
                        "id,source_type,source_name,source_id,page_number,row_id,image_id,"
                        "ocr_region,content,document_id,metadata"
                    ),
                    "order": "chunk_index.asc",
                    "limit": "1",
                },
                headers={
                    "apikey": settings.supabase_publishable_key.get_secret_value(),
                    "Authorization": f"Bearer {access_token}",
                },
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=503, detail="Source service timed out") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Source service unavailable") from exc

    if response.is_error:
        raise HTTPException(status_code=503, detail="Source service unavailable")
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Source not found")
    return await _source_payload(rows[0], authorization, demo_role)


async def _source_payload(row, authorization, demo_role):
    citation = citation_from_row({**row, "chunk_id": row["id"]})
    return {
        **citation,
        "source_id": row.get("source_id"),
        "excerpt": row.get("content", ""),
        "record_fields": (row.get("metadata") or {}).get("fields"),
        "preview_path": f"/api/v1/sources/{row['document_id']}/original"
        if row.get("source_type") in {"pdf", "image_ocr"}
        else None,
        "access": "Available within your current authorization scope",
    }


@app.get("/api/v1/sources/{source_id}/original", tags=["sources"])
async def source_original(
    source_id: Annotated[UUID, ApiPath()],
    page: Annotated[int | None, Query(ge=1, le=100)] = None,
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
):
    # A whole file requires a document-level grant. A chunk-only grant cannot
    # expose siblings, and structured fixtures are never returned as originals.
    settings = get_settings()
    if not _local_demo_enabled():
        raise HTTPException(status_code=404, detail="Source not found")
    async with request_client() as client:
        actor_token = bearer_token(authorization)
        identity = await _identity(client, settings, actor_token)
        token, _ = await _context_token(client, settings, actor_token, identity, demo_role)
        response = await _rest_rows(
            client,
            settings,
            token,
            "documents",
            params={
                "id": f"eq.{source_id}",
                "select": "id,source_type,storage_path,metadata",
                "limit": "1",
            },
        )
    rows = response.json()
    if not rows or rows[0]["source_type"] not in {"pdf", "image_ocr"}:
        raise HTTPException(status_code=404, detail="Source not found")
    doc = rows[0]
    path = original_path(doc)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Source not found")
    if page is not None:
        if doc["source_type"] != "pdf":
            raise HTTPException(status_code=404, detail="Page not found")
        png = await asyncio.to_thread(render_pdf_page, path, page)
        return Response(
            png,
            media_type="image/png",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    media = (
        "application/pdf"
        if doc["source_type"] == "pdf"
        else "image/png"
        if path.suffix.lower() == ".png"
        else "image/jpeg"
    )
    return FileResponse(
        path,
        media_type=media,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


def render_pdf_page(path: Path, page: int) -> bytes:
    import pymupdf

    with pymupdf.open(path) as document:
        if page > len(document):
            raise HTTPException(status_code=404, detail="Page not found")
        source = document[page - 1]
        # Bound raster dimensions even when an uploaded PDF has an unusually large page.
        scale = min(1.5, 1600 / max(source.rect.width, source.rect.height, 1))
        return source.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")


def original_path(doc):
    metadata = doc.get("metadata") or {}
    if metadata.get("synthetic") is True and metadata.get("local_demo_path"):
        base = (REPOSITORY_ROOT / "data/demo").resolve()
        path = (base / metadata["local_demo_path"]).resolve()
    elif doc.get("storage_path"):
        base = PRIVATE_INGESTION.resolve()
        path = (REPOSITORY_ROOT / doc["storage_path"]).resolve()
    else:
        return None
    return (
        path
        if path.is_relative_to(base) and path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}
        else None
    )


@app.post("/api/v1/chat/stream", tags=["chat"])
async def stream_query(
    request: QueryRequest,
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
):
    request_started = time.perf_counter()
    # Authenticate and validate role before opening the stream. No raw generation
    # deltas are exposed: factual text is released only after citation validation.
    settings = get_settings()
    async with request_client() as client:
        token = bearer_token(authorization)
        identity = await _identity(client, settings, token)
        scoped_token, active_role = await _context_token(
            client, settings, token, identity, demo_role
        )

    async def events():
        queue = asyncio.Queue()
        task = asyncio.create_task(
            _run_query(
                request,
                authorization,
                demo_role,
                queue.put,
                (identity, scoped_token, active_role, request_started),
            )
        )
        try:
            while not task.done() or not queue.empty():
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield f"event: progress\ndata: {json.dumps(update)}\n\n"
                except TimeoutError:
                    continue
            result = await task
            yield f"event: result\ndata: {result.model_dump_json()}\n\n"
        except (IntegrationFailure, HTTPException) as exc:
            if isinstance(exc, IntegrationFailure):
                safe = await integration_failure_handler(None, exc)
                error = json.loads(safe.body)
                error["evidence"] = exc.evidence
            else:
                error = {
                    "code": "session_expired" if exc.status_code == 401 else "request_failed",
                    "detail": str(exc.detail),
                    "status": exc.status_code,
                }
            yield f"event: error\ndata: {json.dumps(error)}\n\n"
        except httpx.HTTPError:
            yield (
                'event: error\ndata: {"code":"upstream_unavailable",'
                '"detail":"Workspace service unavailable."}\n\n'
            )
        finally:
            if not task.done():
                task.cancel()
            try:
                await task
            except (asyncio.CancelledError, IntegrationFailure, HTTPException, httpx.HTTPError):
                pass

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )


async def _history_rows(client, settings, token, identity, role, conversation_id=None):
    params = {
        "user_id": f"eq.{identity['user_id']}",
        "organization_id": f"eq.{identity['organization_id']}",
        "active_role": f"eq.{role}",
        "deleted_at": "is.null",
        "select": "id,conversation_id,query,response,created_at",
        "order": "created_at.desc",
        "limit": "200",
    }
    if conversation_id:
        params["conversation_id"] = f"eq.{conversation_id}"
    response = await _rest_rows(client, settings, token, "query_history", params=params)
    return list(reversed(response.json()))


async def _recent_referents(client, settings, token, turns):
    # Prior prose/trace is never factual context. Only a recent cited source
    # pointer is used, then read again under the current actor's RLS session.
    for turn in reversed(turns[-5:]):
        saved = turn.get("response") or {}
        ids = []
        claims = saved.get("claims", []) if isinstance(saved, dict) else []
        for claim in claims if isinstance(claims, list) else []:
            if not isinstance(claim, dict):
                continue
            citations = claim.get("citations", [])
            for citation in citations if isinstance(citations, list) else []:
                try:
                    ids.append(str(UUID(citation["citation_id"])))
                except (ValueError, TypeError, KeyError):
                    continue
        ids = list(dict.fromkeys(ids))[:24]
        if not ids:
            continue
        visible = await _rest_rows(
            client,
            settings,
            token,
            "knowledge_chunks",
            params={
                "id": f"in.({','.join(ids)})",
                "select": "id,content,row_id,document_id",
                "limit": "24",
            },
        )
        current = visible.json()
        document_ids = list(
            dict.fromkeys(
                row["document_id"]
                for row in current
                if row.get("document_id") and not row.get("row_id")
            )
        )
        if document_ids:
            siblings = await _rest_rows(
                client,
                settings,
                token,
                "knowledge_chunks",
                params={
                    "document_id": f"in.({','.join(document_ids)})",
                    "select": "id,content,row_id,document_id",
                    "limit": "100",
                },
            )
            current += [row for row in siblings.json() if row["id"] not in ids]
        return current
    return []


async def _save_history(token, identity, role, query, response):
    settings = get_settings()
    try:
        async with request_client() as client:
            saved = await client.post(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/query_history",
                headers=_rest_headers(settings, token),
                json={
                    "id": response.request_id,
                    "conversation_id": response.conversation_id,
                    "user_id": identity["user_id"],
                    "organization_id": identity["organization_id"],
                    "active_role": role,
                    "query": query,
                    "response": response.model_dump(),
                },
            )
        if saved.is_error:
            LOGGER.warning("History persistence unavailable: HTTP %s", saved.status_code)
        return not saved.is_error
    except (httpx.HTTPError, IntegrationFailure, AttributeError):
        LOGGER.warning("History persistence unavailable")
        return False


@app.get("/api/v1/conversations", tags=["chat"])
async def conversations(
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
):
    settings = get_settings()
    async with request_client() as client:
        token = bearer_token(authorization)
        identity = await _identity(client, settings, token)
        _, role = await _context_token(client, settings, token, identity, demo_role)
        rows = await _history_rows(client, settings, token, identity, role)
    grouped = {}
    for row in rows:
        entry = grouped.setdefault(
            row["conversation_id"],
            {
                "id": row["conversation_id"],
                "title": row["query"][:90],
                "created_at": row["created_at"],
            },
        )
        entry["updated_at"] = row["created_at"]
    return {"conversations": list(reversed(list(grouped.values())))}


@app.get("/api/v1/conversations/{conversation_id}", tags=["chat"])
async def conversation(
    conversation_id: Annotated[UUID, ApiPath()],
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
):
    settings = get_settings()
    async with request_client() as client:
        token = bearer_token(authorization)
        identity = await _identity(client, settings, token)
        scoped_token, role = await _context_token(client, settings, token, identity, demo_role)
        rows = await _history_rows(client, settings, token, identity, role, str(conversation_id))
        if not rows:
            raise HTTPException(status_code=404, detail="Conversation not found")
        for turn_index, row in enumerate(rows):
            replay_query, clarification = interpret_followup(row["query"], [])
            if clarification and turn_index:
                recent = await _recent_referents(client, settings, scoped_token, rows[:turn_index])
                replay_query, clarification = interpret_followup(row["query"], recent)
            saved = row.get("response")
            saved = saved if isinstance(saved, dict) else {}
            claims = saved.get("claims")
            claims = claims if isinstance(claims, list) else []
            references = [
                {
                    "evidence_ids": [
                        c.get("evidence_id")
                        for c in claim.get("citations", [])
                        if isinstance(c, dict)
                    ]
                }
                for claim in claims
                if isinstance(claim, dict) and isinstance(claim.get("citations"), list)
            ]
            citations = [
                c
                for claim in claims
                if isinstance(claim, dict) and isinstance(claim.get("citations"), list)
                for c in claim["citations"]
                if isinstance(c, dict)
            ]
            ids = list(
                dict.fromkeys(
                    c["citation_id"] for c in citations if isinstance(c.get("citation_id"), str)
                )
            )
            try:
                ids = [str(UUID(value)) for value in ids if isinstance(value, str)][:100]
            except ValueError:
                ids = []
            current = []
            if ids:
                # Reauthorize every saved reference under the current grants.
                visible = await _rest_rows(
                    client,
                    settings,
                    scoped_token,
                    "knowledge_chunks",
                    params={
                        "id": f"in.({','.join(ids)})",
                        "select": (
                            "id,content,source_name,source_type,source_id,document_id,metadata,"
                            "page_number,row_id,image_id,ocr_region"
                        ),
                        "limit": "100",
                    },
                )
                current = visible.json()
                document_ids = list(dict.fromkeys(item["document_id"] for item in current))
                if document_ids:
                    # Rebuild same-document invoice identity from current,
                    # independently RLS-visible siblings, never saved metadata.
                    siblings = await _rest_rows(
                        client,
                        settings,
                        scoped_token,
                        "knowledge_chunks",
                        params={
                            "document_id": f"in.({','.join(document_ids)})",
                            "select": (
                                "id,content,source_name,source_type,source_id,document_id,metadata,"
                                "page_number,row_id,image_id,ocr_region"
                            ),
                            "limit": "100",
                        },
                    )
                    current += [item for item in siblings.json() if item["id"] not in ids]
            _, canonical = prepare_generation_context(
                replay_query, [{**item, "chunk_id": item["id"]} for item in current]
            )
            rebuilt = validate_generation({"claims": references}, canonical)
            if saved.get("state") == "VERIFIED_EVIDENCE":
                # The saved mode/text is not proof of a provider failure. Re-run
                # the deterministic extractor on currently visible references.
                rebuilt = verified_evidence_response(replay_query, canonical)
                rebuilt["message"] = (
                    "Verified evidence response: reconstructed without a language model. "
                    "History replay did not rerun provider availability."
                )
            greeting = small_talk(row["query"])
            if greeting:
                rebuilt = {"state": "SMALL_TALK", "claims": [], "message": greeting}
            elif clarification or saved.get("state") == "CLARIFICATION_NEEDED":
                rebuilt = {
                    "state": "CLARIFICATION_NEEDED",
                    "claims": [],
                    "message": clarification
                    or "Which invoice do you mean? Please include its invoice ID.",
                }
            row["response"] = {
                "request_id": row.get("id", str(uuid4())),
                "conversation_id": str(conversation_id),
                "trace": {
                    "session_verified": True,
                    "database_request_used_user_session": True,
                    "active_role": role,
                    "history_replay": True,
                    "canonical_evidence_count": len(canonical),
                    "evidence_items_sent_to_model": 0,
                    "generation_model": None,
                    "fallback_used": False,
                    "history_saved": True,
                    "timing_ms": {},
                    "ranking_timing_note": (
                        "History replay rechecks current source access; generation and "
                        "original timings were not rerun."
                    ),
                },
                **rebuilt,
            }
    return {"turns": rows}


@app.delete("/api/v1/conversations/{conversation_id}", tags=["chat"])
async def hide_conversation(
    conversation_id: Annotated[UUID, ApiPath()],
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
):
    settings = get_settings()
    async with request_client() as client:
        token = bearer_token(authorization)
        identity = await _identity(client, settings, token)
        _, role = await _context_token(client, settings, token, identity, demo_role)
        response = await client.patch(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/query_history",
            headers=_rest_headers(settings, token),
            params={
                "conversation_id": f"eq.{conversation_id}",
                "user_id": f"eq.{identity['user_id']}",
                "organization_id": f"eq.{identity['organization_id']}",
                "active_role": f"eq.{role}",
            },
            json={"deleted_at": datetime.now(UTC).isoformat()},
        )
    if response.is_error:
        raise IntegrationFailure("Conversation could not be removed")
    return {"state": "removed"}
