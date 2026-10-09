import json
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException

from ps01_api.config import Settings
from ps01_api.main import _context_token, app, revalidate_evidence

ACTOR = {
    "user_id": "actor",
    "organization_id": "org",
    "role": "CEO",
    "roles": ["CEO"],
    "email": "ceo@demo",
}
TARGET = {"organization_id": "org", "role": "Finance Manager", "email": "finance@demo"}


@pytest.mark.asyncio
async def test_cached_context_rechecks_tenant_and_role_each_time(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text(
        json.dumps({"CEO": {"email": "ceo@demo"}, "Finance Manager": {"email": "finance@demo"}})
    )
    key = ("actor", "org", "Finance Manager")
    app.state.demo_role_sessions = {
        key: {"access_token": "scoped", "expires_at": time.monotonic() + 500}
    }
    client = AsyncMock()
    with (
        patch("ps01_api.main.DEMO_CREDENTIALS", path),
        patch("ps01_api.main._local_demo_enabled", return_value=True),
        patch("ps01_api.main._identity", AsyncMock(return_value=TARGET)) as identity,
    ):
        assert await _context_token(
            client, Settings(), "actor-token", ACTOR, "Finance Manager"
        ) == ("scoped", "Finance Manager")
        identity.return_value = TARGET | {"organization_id": "foreign"}
        with pytest.raises(HTTPException) as error:
            await _context_token(client, Settings(), "actor-token", ACTOR, "Finance Manager")
        assert error.value.status_code == 403
        assert key not in app.state.demo_role_sessions
        client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_other_actor_cannot_reuse_role_cache(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text(
        json.dumps({"CEO": {"email": "ceo@demo"}, "Finance Manager": {"email": "finance@demo"}})
    )
    app.state.demo_role_sessions = {
        "Finance Manager": {"access_token": "foreign", "expires_at": time.monotonic() + 500}
    }
    with (
        patch("ps01_api.main.DEMO_CREDENTIALS", path),
        patch("ps01_api.main._local_demo_enabled", return_value=True),
    ):
        with pytest.raises(HTTPException) as error:
            await _context_token(
                AsyncMock(),
                Settings(),
                "token",
                ACTOR | {"email": "foreign@demo"},
                "Finance Manager",
            )
        assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_revoked_deleted_or_changed_evidence_is_removed():
    ids = ["11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"]
    rows = [
        {"chunk_id": x, "content": "Original", "source_type": "pdf", "page_number": 1} for x in ids
    ]

    async def handler(request):
        assert request.headers["authorization"] == "Bearer scoped"
        assert "id=in." in str(request.url)
        return httpx.Response(
            200, json=[{"id": ids[0], "content": "Changed", "source_type": "pdf", "page_number": 1}]
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        from pydantic import SecretStr

        settings = Settings(
            supabase_url="http://localhost:54321", supabase_publishable_key=SecretStr("public")
        )
        assert await revalidate_evidence(client, settings, "scoped", rows) == []


def test_unauthorized_delete_rejects_before_source_lookup():
    from fastapi.testclient import TestClient

    for detail in ("known", "missing"):
        with patch(
            "ps01_api.main.require_local_ceo",
            AsyncMock(side_effect=HTTPException(403, "CEO role required")),
        ) as guard:
            response = TestClient(app).delete(
                "/api/v1/sources/11111111-1111-4111-8111-111111111111",
                headers={"Authorization": "Bearer hr"},
            )
            assert response.status_code == 403
            assert detail not in response.text
            guard.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_cannot_delete_outside_private_uploads(tmp_path):
    from pydantic import SecretStr

    from ps01_api.main import cleanup_source_original

    outside = tmp_path / "keep.pdf"
    outside.write_bytes(b"keep")
    client = AsyncMock()
    client.patch.return_value.is_error = False
    settings = Settings(
        supabase_url="http://localhost:54321", supabase_secret_key=SecretStr("admin")
    )
    assert await cleanup_source_original(client, settings, "test-id", str(outside))
    assert outside.exists()


@pytest.mark.asyncio
async def test_denied_context_audit_uses_verified_actor_role():
    from fastapi import Request, Response

    from ps01_api.main import audit_workspace_actions

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/sources/example",
            "headers": [(b"authorization", b"Bearer actor"), (b"x-demo-role", b"CEO")],
        }
    )
    actor = ACTOR | {"role": "HR Manager"}
    with (
        patch("ps01_api.main._identity", AsyncMock(return_value=actor)),
        patch("ps01_api.main._context_token", AsyncMock(side_effect=HTTPException(403, "Denied"))),
        patch("ps01_api.main.record_security_event", AsyncMock()) as audit,
    ):
        await audit_workspace_actions(request, AsyncMock(return_value=Response(status_code=403)))
    audit.assert_awaited_once_with(actor, "HR Manager", "source_read", "denied_or_failed")


@pytest.mark.asyncio
async def test_ingestion_embedding_quota_preserves_cause_and_compensates():
    from types import SimpleNamespace

    from pydantic import SecretStr

    from ps01_api.integrations import IntegrationFailure
    from ps01_api.main import _store_ingested, integration_failure_handler

    config = Settings(supabase_url="http://localhost:54321", supabase_secret_key=SecretStr("test"))
    client = AsyncMock()
    client.get.return_value = httpx.Response(200, json=[{"id": "role"}])
    client.post.return_value = httpx.Response(201, json=[])
    failure = IntegrationFailure("Quota", code="provider_rate_limited")
    failure.retry_after = 120
    candidate = SimpleNamespace(content="Synthetic invoice", metadata={})
    with patch("ps01_api.main.create_document_embedding", AsyncMock(side_effect=failure)):
        with pytest.raises(IntegrationFailure) as error:
            await _store_ingested(
                client, config, ACTOR, "source", "test.pdf", "pdf", "hash", [candidate], "CEO", None
            )
    client.delete.assert_awaited_once()
    response = await integration_failure_handler(None, error.value)
    body = json.loads(response.body)
    assert response.status_code == 429
    assert body["stage"] == "embedding"
    assert body["code"] == "provider_rate_limited"
    assert body["retry_after_seconds"] == 120
