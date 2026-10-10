"""Mock provider/identity transports: no live credentials, model, or database."""

import json
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from ps01_api.config import Settings
from ps01_api.ingestion import ChunkCandidate
from ps01_api.integrations import _GENERATION_CIRCUITS
from ps01_api.main import QueryRequest, _run_query, _store_ingested

ACTOR = {"user_id": "actor", "organization_id": "org", "role": "CEO", "roles": ["CEO"]}


async def test_failed_ingestion_cancels_pending_embeddings_before_document_cleanup():
    import asyncio

    from ps01_api.integrations import IntegrationFailure

    pending_started = asyncio.Event()
    events = []

    async def embedding(client, settings, title, text, before_attempt=None):
        if text == "failure":
            await pending_started.wait()
            raise IntegrationFailure("Invalid vector", code="provider_invalid_response")
        pending_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            events.append("cancelled")

    def handler(request):
        if request.method == "DELETE":
            events.append("cleanup")
            return httpx.Response(204)
        if request.method == "GET":
            return httpx.Response(200, json=[{"id": "role"}])
        return httpx.Response(201, json=json.loads(request.content))

    candidates = [
        ChunkCandidate("pdf", "source.pdf", "source", text, index, page_number=1)
        for index, text in enumerate(["failure", "pending", "pending", "queued", "queued"])
    ]
    with patch("ps01_api.main.create_document_embedding", embedding):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(IntegrationFailure) as failure:
                await _store_ingested(
                    client,
                    config(),
                    ACTOR,
                    "source",
                    "source.pdf",
                    "pdf",
                    "hash",
                    candidates,
                    "CEO",
                    None,
                    "actor-token",
                )
    assert failure.value.code == "provider_invalid_response"
    assert events and events[-1] == "cleanup" and "cancelled" in events[:-1]


def config():
    return Settings(
        _env_file=None,
        gemini_api_key=SecretStr("fake-primary"),
        gemini_secondary_api_key=SecretStr("fake-secondary"),
        gemini_project_id="primary-project",
        gemini_secondary_project_id="secondary-project",
        supabase_url="http://database.test",
        supabase_secret_key=SecretStr("fake-admin"),
        supabase_publishable_key=SecretStr("fake-public"),
    )


@pytest.fixture(autouse=True)
def clear_circuits():
    _GENERATION_CIRCUITS.clear()
    yield
    _GENERATION_CIRCUITS.clear()


@pytest.mark.parametrize("changed", ["user_id", "organization_id", "role"])
async def test_query_revocation_before_secondary_prevents_retrieval_and_generation(changed):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429)

    @asynccontextmanager
    async def client_context():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    second_identity = ACTOR | {changed: "changed"} if changed != "role" else ACTOR
    contexts = [
        ("fresh-token", "Finance Manager"),
        ("new-token", "HR Manager" if changed == "role" else "Finance Manager"),
    ]
    with (
        patch("ps01_api.main.get_settings", return_value=config()),
        patch("ps01_api.main.request_client", client_context),
        patch(
            "ps01_api.main._identity", AsyncMock(side_effect=[ACTOR, second_identity])
        ) as identity,
        patch("ps01_api.main._context_token", AsyncMock(side_effect=contexts)) as context,
        patch("ps01_api.main.retrieve_chunks", AsyncMock()) as retrieval,
        patch("ps01_api.main.generate_claims", AsyncMock()) as generation,
    ):
        with pytest.raises(HTTPException) as denied:
            await _run_query(
                QueryRequest(query="What is invoice INV-1001's total?"),
                "Bearer actor-token",
                "Finance Manager",
                verified=(ACTOR, "original-token", "Finance Manager", time.perf_counter()),
            )
    assert denied.value.status_code == 403
    assert identity.await_count == context.await_count == 2
    assert len(calls) == 1
    retrieval.assert_not_awaited()
    generation.assert_not_awaited()


async def test_ingestion_role_revocation_before_secondary_compensates_unpublished_source():
    embeddings, deletes, writes = [], [], []

    def handler(request):
        if request.url.host == "generativelanguage.googleapis.com":
            embeddings.append(request)
            return httpx.Response(429)
        table = request.url.path.split("/")[-1]
        if request.method == "DELETE":
            deletes.append(table)
            return httpx.Response(204)
        if request.method == "GET":
            return httpx.Response(200, json=[{"id": "role"}])
        writes.append(table)
        return httpx.Response(201, json=json.loads(request.content))

    candidate = ChunkCandidate("pdf", "source.pdf", "source", "private passage", 0, page_number=1)
    with (
        patch(
            "ps01_api.main._identity",
            AsyncMock(side_effect=[ACTOR, ACTOR | {"role": "HR Manager"}]),
        ) as identity,
        patch("ps01_api.main._context_token", AsyncMock(return_value=("actor-token", "CEO"))),
    ):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(HTTPException) as denied:
                await _store_ingested(
                    client,
                    config(),
                    ACTOR,
                    "source",
                    "source.pdf",
                    "pdf",
                    "hash",
                    [candidate],
                    "CEO",
                    None,
                    "actor-token",
                )
    assert denied.value.status_code == 403
    assert identity.await_count == 2
    assert len(embeddings) == 1 and deletes == ["documents"]
    assert writes == ["documents"]


async def test_query_fallback_retrieves_with_latest_authorized_role_token():
    calls = []

    def handler(request):
        calls.append(request)
        return (
            httpx.Response(429)
            if len(calls) == 1
            else httpx.Response(200, json={"embedding": {"values": [0.25] * 1536}})
        )

    @asynccontextmanager
    async def client_context():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    with (
        patch("ps01_api.main.get_settings", return_value=config()),
        patch("ps01_api.main.request_client", client_context),
        patch("ps01_api.main._identity", AsyncMock(return_value=ACTOR)),
        patch(
            "ps01_api.main._context_token",
            AsyncMock(
                side_effect=[
                    ("fresh-primary-token", "Finance Manager"),
                    ("fresh-secondary-token", "Finance Manager"),
                ]
            ),
        ),
        patch("ps01_api.main.retrieve_chunks", AsyncMock(return_value=[])) as retrieval,
        patch("ps01_api.main.revalidate_evidence", AsyncMock(return_value=[])),
        patch("ps01_api.main.generate_claims", AsyncMock()) as generation,
        patch("ps01_api.main._save_history", AsyncMock(return_value=True)),
    ):
        response = await _run_query(
            QueryRequest(query="What is invoice INV-1001's total?"),
            "Bearer actor-token",
            "Finance Manager",
            verified=(ACTOR, "original-token", "Finance Manager", time.perf_counter()),
        )
    assert len(calls) == 2
    assert retrieval.await_args.args[2] == "fresh-secondary-token"
    assert response.state == "INSUFFICIENT_EVIDENCE"
    generation.assert_not_awaited()
