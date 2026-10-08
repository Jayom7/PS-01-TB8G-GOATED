from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .config import get_settings
from .integrations import (
    IntegrationFailure,
    create_embedding,
    generate_claims,
    retrieve_chunks,
    verify_supabase_session,
)
from .rag import insufficient_evidence, prepare_generation_context, validate_generation

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
    allow_headers=["Authorization", "Content-Type"],
)


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=2_000)


class QueryResponse(BaseModel):
    request_id: str
    state: str
    claims: list[dict[str, object]]
    trace: dict[str, object]


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


@app.post("/api/v1/chat/query", response_model=QueryResponse, tags=["chat"])
async def query_knowledge(
    request: QueryRequest,
    authorization: str | None = Header(default=None),
) -> QueryResponse:
    request_id = str(uuid4())
    settings = get_settings()
    timeout = httpx.Timeout(25.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        access_token = await require_session(client, authorization)
        try:
            embedding = await create_embedding(client, settings, request.query)
            evidence = await retrieve_chunks(
                client, settings, access_token, request.query, embedding
            )
            if not evidence:
                result = insufficient_evidence()
                model_context: list[dict[str, object]] = []
            else:
                prompt, model_context = prepare_generation_context(request.query, evidence)
                model_output = await generate_claims(client, settings, prompt)
                result = validate_generation(model_output, model_context)
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=503, detail="Knowledge service timed out") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Knowledge service unavailable") from exc
        except IntegrationFailure as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return QueryResponse(
        request_id=request_id,
        state=result["state"],
        claims=result["claims"],
        trace={
            "session_verified": True,
            "database_request_used_user_session": True,
            "evidence_items_sent_to_model": len(model_context),
        },
    )


@app.get("/api/v1/sources/{source_id}", tags=["sources"])
async def get_source(
    source_id: Annotated[UUID, Path()],
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Source service unavailable")

    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        access_token = await require_session(client, authorization)
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
