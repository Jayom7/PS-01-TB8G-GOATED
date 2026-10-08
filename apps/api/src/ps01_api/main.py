from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import runpy
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote, urlparse
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi import Path as ApiPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from .rag import insufficient_evidence, prepare_generation_context, validate_generation

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
LOGGER = logging.getLogger("ps01_api")
DEMO_CREDENTIALS = REPOSITORY_ROOT / ".local-demo-credentials.json"
DEMO_ROLES = ("CEO", "Finance Manager", "HR Manager", "Sales Manager", "Engineer")
EVALUATION_RESULTS = REPOSITORY_ROOT / "data" / "local" / "evaluation.json"
PRIVATE_INGESTION = REPOSITORY_ROOT / "data" / "private" / "ingest"

app = FastAPI(
    title="Clearframe Knowledge API",
    version="0.2.0",
    description="Authenticated API for a multi-modal knowledge workspace.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
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
        "provider_unavailable": "Answer generation is temporarily unavailable. Try again shortly.",
        "provider_rate_limited": (
            "Answer generation is rate-limited. Your retrieved evidence remains protected; "
            "retry later."
        ),
        "provider_timeout": "The answer service took too long to respond. Please try again.",
        "provider_invalid_response": (
            "The answer service returned an unusable response. Please retry."
        ),
        "retrieval_unavailable": "Authorized search is unavailable. No answer was generated.",
    }
    content: dict[str, object] = {
        "detail": messages.get(
            exc.code, "A workspace service is temporarily unavailable. Please retry."
        ),
        "code": exc.code,
    }
    if exc.timing_ms is not None:
        content["timing_ms"] = exc.timing_ms
    return JSONResponse(status_code=503, content=content)


@app.exception_handler(httpx.HTTPError)
async def upstream_http_error_handler(_request: Request, exc: httpx.HTTPError):
    LOGGER.warning("Upstream HTTP failure: %s", type(exc).__name__)
    return JSONResponse(
        status_code=503, content={"detail": "An upstream workspace service is unavailable"}
    )


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=2_000)


class QueryResponse(BaseModel):
    request_id: str
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
        raise IntegrationFailure("Authorized workspace data is unavailable")
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
    if not _local_demo_enabled():
        raise HTTPException(status_code=403, detail="Demo role contexts are available only locally")

    cache = getattr(app.state, "demo_role_sessions", {})
    cached = cache.get(role)
    if cached and cached["expires_at"] > time.monotonic() + 60:
        return str(cached["access_token"]), role
    try:
        credentials = json.loads(DEMO_CREDENTIALS.read_text())
        target = credentials.get(role)
    except (OSError, ValueError):
        target = None
    if not isinstance(target, dict) or not target.get("email") or not target.get("password"):
        raise HTTPException(status_code=503, detail="Local demo role credentials are unavailable")
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
    cache[role] = {
        "access_token": access_token,
        "expires_at": time.monotonic() + int(session.get("expires_in", 3600)),
    }
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
    timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
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
    recent = _activity_for(str(identity["user_id"]))
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
        "document_count": len(documents),
        "chunk_count": chunk_count,
        "structured_record_count": len(
            {
                row.get("row_id")
                for row in structured_response.json()
                if isinstance(row, dict) and row.get("row_id")
            }
        ),
        "documents": documents,
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
        "gemini": "configured; availability not checked"
        if settings.gemini_api_key
        else "not configured",
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
        identity = await _identity(client, settings, token)
        _, active_role = await _context_token(client, settings, token, identity, demo_role)
    trace = [
        {
            "created_at": item.get("created_at"),
            "query_id": item.get("request_id"),
            "state": item.get("state"),
            "active_role": item.get("active_role", "unknown"),
            "authorized_evidence_count": item.get("evidence_count", 0),
            "decision": "authorized retrieval"
            if item.get("evidence_count", 0)
            else "no authorized evidence",
        }
        for item in _activity_for(str(identity["user_id"]))
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        token = await require_session(client, authorization)
        identity = await _identity(client, settings, token)
        await _context_token(client, settings, token, identity, demo_role)
    if EVALUATION_RESULTS.is_file():
        try:
            result = json.loads(EVALUATION_RESULTS.read_text())
            if not isinstance(result, dict):
                return {"state": "unavailable", "result": None}
            return {"state": "completed", "result": recorded_evaluation(result)}
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
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
    semaphore = asyncio.Semaphore(3)

    async def embed(candidate):
        async with semaphore:
            return await create_document_embedding(client, settings, source_name, candidate.content)

    try:
        embeddings = await asyncio.gather(*(embed(candidate) for candidate in candidates))
    except IntegrationFailure as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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
        "metadata": {"ingestion": "local-demo", "chunk_count": len(candidates)},
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
    chunk_payload = []
    for candidate, embedding in zip(candidates, embeddings, strict=True):
        chunk_payload.append(
            {
                "organization_id": organization_id,
                "document_id": source_id,
                "source_type": candidate.source_type,
                "source_name": candidate.source_name,
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
            _, identity = await require_local_ceo(client, authorization, demo_role)
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
    except (httpx.HTTPError, IntegrationFailure) as exc:
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
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
        await require_local_ceo(client, authorization, demo_role)
    try:
        module = runpy.run_path(
            str(REPOSITORY_ROOT / "apps" / "api" / "scripts" / "evaluate_local_retrieval.py")
        )
        result = await module["run"]()
        result["completed_at"] = datetime.now(UTC).isoformat()
        EVALUATION_RESULTS.parent.mkdir(parents=True, exist_ok=True)
        if EVALUATION_RESULTS.is_file():
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            archive = EVALUATION_RESULTS.with_name(f"evaluation-history-{stamp}.json")
            archive.write_bytes(EVALUATION_RESULTS.read_bytes())
            archive.chmod(0o600)
        EVALUATION_RESULTS.write_text(json.dumps(result, indent=2) + "\n")
        EVALUATION_RESULTS.chmod(0o600)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Evaluation failed; no result was saved"
        ) from exc
    return {"state": "completed", "result": result | {"run_kind": "fresh_local"}}


@app.post("/api/v1/chat/query", response_model=QueryResponse, tags=["chat"])
async def query_knowledge(
    request: QueryRequest,
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> QueryResponse:
    request_id = str(uuid4())
    settings = get_settings()
    timeout = httpx.Timeout(25.0, connect=5.0)
    fallback_used = False
    request_started = time.perf_counter()
    timings: dict[str, float | None] = {
        "auth_session_ms": 0.0,
        "embedding_ms": 0.0,
        "retrieval_and_ranking_ms": 0.0,
        "ranking_only_ms": None,
        "gemini_ms": 0.0,
        "citation_validation_ms": 0.0,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            auth_started = time.perf_counter()
            try:
                actor_token = bearer_token(authorization)
                identity = await _identity(client, settings, actor_token)
                access_token, active_role = await _context_token(
                    client, settings, actor_token, identity, demo_role
                )
            finally:
                timings["auth_session_ms"] = round((time.perf_counter() - auth_started) * 1000, 1)
            embedding_started = time.perf_counter()
            try:
                embedding = await create_embedding(client, settings, request.query)
            finally:
                timings["embedding_ms"] = round((time.perf_counter() - embedding_started) * 1000, 1)
            retrieval_started = time.perf_counter()
            try:
                evidence = await retrieve_chunks(
                    client, settings, access_token, request.query, embedding
                )
            finally:
                timings["retrieval_and_ranking_ms"] = round(
                    (time.perf_counter() - retrieval_started) * 1000, 1
                )
            if not evidence:
                result = insufficient_evidence()
                model_context: list[dict[str, object]] = []
                generation_model = None
            else:
                prompt, model_context = prepare_generation_context(request.query, evidence)
                generation_started = time.perf_counter()
                try:
                    model_output = await generate_claims(client, settings, prompt)
                finally:
                    timings["gemini_ms"] = round(
                        (time.perf_counter() - generation_started) * 1000, 1
                    )
                generation_model = model_output.get("_model")
                fallback_used = model_output.get("_fallback_used") is True
                validation_started = time.perf_counter()
                result = validate_generation(model_output, model_context)
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

    return QueryResponse(
        request_id=request_id,
        state=result["state"],
        claims=result["claims"],
        trace={
            "session_verified": True,
            "database_request_used_user_session": True,
            "evidence_items_sent_to_model": len(model_context),
            "generation_model": generation_model,
            "fallback_used": fallback_used,
            "active_role": active_role,
            "timing_ms": timings
            | {"total_ms": round((time.perf_counter() - request_started) * 1000, 1)},
            "ranking_timing_note": (
                "Ranking runs inside the database retrieval RPC; no separate server timing "
                "is exposed."
            ),
        },
    )


@app.get("/api/v1/sources/{source_id}", tags=["sources"])
async def get_source(
    source_id: Annotated[UUID, ApiPath()],
    authorization: str | None = Header(default=None),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
) -> dict[str, object]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Source service unavailable")

    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
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
                        "ocr_region,content"
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
    row = rows[0]
    return {
        "citation_id": str(row["id"]),
        "source_type": row.get("source_type"),
        "title": row.get("source_name"),
        "source_id": row.get("source_id"),
        "location": {
            "page": row.get("page_number"),
            "row": row.get("row_id"),
            "image_id": row.get("image_id"),
            "region": row.get("ocr_region"),
        },
        "excerpt": row.get("content", ""),
    }


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

    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
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
                        "ocr_region,content"
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
    row = rows[0]
    return {
        "citation_id": str(row["id"]),
        "source_type": row.get("source_type"),
        "title": row.get("source_name"),
        "source_id": str(source_id),
        "location": {
            "page": row.get("page_number"),
            "row": row.get("row_id"),
            "image_id": row.get("image_id"),
            "region": row.get("ocr_region"),
        },
        "excerpt": row.get("content", ""),
    }
