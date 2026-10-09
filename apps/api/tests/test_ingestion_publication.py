"""Recording database transport; no real provider or database calls."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import SecretStr

from ps01_api.config import Settings
from ps01_api.ingestion import ChunkCandidate
from ps01_api.integrations import IntegrationFailure
from ps01_api.main import _store_ingested


@pytest.mark.parametrize("kind", ["pdf", "image_ocr", "structured"])
@pytest.mark.parametrize("visible", [True, False])
async def test_ingestion_success_requires_persisted_source_and_chunks_visible_to_actor(
    kind, visible
):
    config = Settings(
        supabase_url="http://database.test",
        supabase_secret_key=SecretStr("admin"),
        supabase_publishable_key=SecretStr("public"),
    )
    fields = {
        "customer_id": "customer-1",
        "name": "Customer",
        "status": "active",
        "contract_id": None,
        "payment_terms": "Net 30",
    }
    candidate = ChunkCandidate(
        kind,
        "Test source",
        "doc",
        "Test source text",
        0,
        page_number=1 if kind == "pdf" else None,
        image_id="scan" if kind == "image_ocr" else None,
        row_id="customer-1" if kind == "structured" else None,
        metadata={"table": "customers", "fields": fields} if kind == "structured" else {},
    )
    writes, reads, deletes = {}, [], []

    def handler(request):
        table = request.url.path.split("/")[-1]
        if request.method == "DELETE":
            deletes.append(table)
            return httpx.Response(204)
        if request.method == "POST":
            writes[table] = json.loads(request.content)
            return httpx.Response(201, json=writes[table])
        if table == "roles":
            return httpx.Response(200, json=[{"id": "ceo-role"}])
        assert request.headers["authorization"] == "Bearer actor-token"
        reads.append(table)
        if not visible:
            return httpx.Response(200, json=[])
        if table == "documents":
            return httpx.Response(200, json=[{"id": "doc", "content_hash": "hash"}])
        if table == "knowledge_chunks":
            return httpx.Response(200, json=[{"id": "chunk"}])
        return httpx.Response(200, json=[{"row_id": "customer-1", "fields": fields}])

    with patch("ps01_api.main.create_document_embedding", AsyncMock(return_value=[0.25] * 1536)):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            args = (
                client,
                config,
                {"organization_id": "org", "user_id": "actor"},
                "doc",
                "Test source",
                kind,
                "hash",
                [candidate],
                "CEO",
                None,
                "actor-token",
            )
            if visible:
                result = await _store_ingested(*args)
                assert result["chunks_indexed"] == 1
                assert set(reads) == {"documents", "knowledge_chunks"} | (
                    {"structured_records"} if kind == "structured" else set()
                )
                assert writes["access_grants"][0]["principal_id"] == "ceo-role"
                assert not deletes
            else:
                with pytest.raises(IntegrationFailure, match="readback"):
                    await _store_ingested(*args)
                assert deletes == ["documents"]
