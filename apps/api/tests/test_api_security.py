from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from ps01_api.integrations import IntegrationFailure
from ps01_api.main import app


class TestApiSecurity:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_health_is_liveness_only(self) -> None:
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_query_rejects_client_supplied_identity_and_evidence(self) -> None:
        response = self.client.post(
            "/api/v1/chat/query",
            json={
                "query": "Show the finance invoice.",
                "user_id": "11111111-1111-4111-8111-111111111111",
                "organization_id": "22222222-2222-4222-8222-222222222222",
                "role": "CEO",
                "acl": ["finance"],
                "evidence": [{"content": "forged evidence"}],
            },
        )
        assert response.status_code == 422

    def test_query_requires_a_bearer_session(self) -> None:
        response = self.client.post(
            "/api/v1/chat/query", json={"query": "What is the invoice amount?"}
        )
        assert response.status_code == 401

    def test_model_context_is_exactly_the_rpc_returned_evidence(self) -> None:
        authorized = {
            "chunk_id": "11111111-1111-4111-8111-111111111111",
            "source_type": "structured",
            "source_name": "Invoice INV-2048",
            "source_id": "invoices",
            "row_id": "INV-2048",
            "content": "Acme | USD 48,000 | unpaid",
        }
        captured: list[str] = []

        async def generate(_client, _settings, prompt, before_attempt=None):
            if before_attempt:
                prompt = await before_attempt()
            captured.append(prompt)
            return {
                "claims": [
                    {
                        "evidence_ids": [f"{authorized['chunk_id']}:0"],
                    }
                ]
            }

        with (
            patch("ps01_api.main.verify_supabase_session", new_callable=AsyncMock) as auth,
            patch("ps01_api.main._identity", new_callable=AsyncMock) as identity,
            patch("ps01_api.main.revalidate_evidence", AsyncMock(side_effect=lambda c, s, t, e: e)),
            patch("ps01_api.main.create_embedding", new_callable=AsyncMock) as embed,
            patch("ps01_api.main.retrieve_chunks", new_callable=AsyncMock) as retrieve,
            patch("ps01_api.main.generate_claims", new_callable=AsyncMock) as generate_mock,
            patch("ps01_api.main._save_history", new_callable=AsyncMock, return_value=True),
        ):
            auth.return_value = {"id": "trusted-session-user"}
            identity.return_value = {
                "user_id": "trusted-session-user",
                "organization_id": "trusted-org",
                "role": "CEO",
                "roles": ["CEO"],
            }
            embed.return_value = [0.0] * 1536
            retrieve.return_value = [authorized]
            generate_mock.side_effect = generate

            response = self.client.post(
                "/api/v1/chat/query",
                headers={"Authorization": "Bearer trusted-session-token"},
                json={"query": "What amount is on the invoice?"},
            )

        assert response.status_code == 200
        assert response.json()["state"] == "CITATION_VALIDATED"
        assert response.json()["trace"]["evidence_items_sent_to_model"] == 1
        assert "unauthorized_evidence_sent_to_model" not in response.json()["trace"]
        assert len(captured) == 1
        assert "USD 48,000" in captured[0]
        assert "trusted-session-token" not in captured[0]
        assert retrieve.await_args.args[2] == "trusted-session-token"
        assert generate_mock.await_count == 1

    def test_empty_authorized_retrieval_never_calls_the_generator(self) -> None:
        with (
            patch("ps01_api.main.verify_supabase_session", new_callable=AsyncMock) as auth,
            patch("ps01_api.main._identity", new_callable=AsyncMock) as identity,
            patch("ps01_api.main.revalidate_evidence", AsyncMock(side_effect=lambda c, s, t, e: e)),
            patch("ps01_api.main.create_embedding", new_callable=AsyncMock) as embed,
            patch("ps01_api.main.retrieve_chunks", new_callable=AsyncMock) as retrieve,
            patch("ps01_api.main.generate_claims", new_callable=AsyncMock) as generate,
            patch("ps01_api.main._save_history", new_callable=AsyncMock, return_value=True),
        ):
            auth.return_value = {"id": "trusted-session-user"}
            identity.return_value = {
                "user_id": "trusted-session-user",
                "organization_id": "trusted-org",
                "role": "CEO",
                "roles": ["CEO"],
            }
            embed.return_value = [0.0] * 1536
            retrieve.return_value = []

            response = self.client.post(
                "/api/v1/chat/query",
                headers={"Authorization": "Bearer trusted-session-token"},
                json={"query": "What is the HR salary?"},
            )

        assert response.status_code == 200
        assert response.json()["state"] == "INSUFFICIENT_EVIDENCE"
        assert response.json()["trace"]["evidence_items_sent_to_model"] == 0
        assert "unauthorized_evidence_sent_to_model" not in response.json()["trace"]
        generate.assert_not_awaited()

    def test_source_lookup_requires_a_bearer_session(self) -> None:
        response = self.client.get("/api/v1/sources/11111111-1111-4111-8111-111111111111")
        assert response.status_code == 401

    def test_source_preview_requires_a_bearer_session(self) -> None:
        response = self.client.get("/api/v1/sources/11111111-1111-4111-8111-111111111111/preview")
        assert response.status_code == 401

    def test_provider_timeout_has_safe_distinct_error_contract(self) -> None:
        with (
            patch("ps01_api.main.verify_supabase_session", new_callable=AsyncMock) as auth,
            patch("ps01_api.main._identity", new_callable=AsyncMock) as identity,
            patch("ps01_api.main.revalidate_evidence", AsyncMock(side_effect=lambda c, s, t, e: e)),
            patch("ps01_api.main.create_embedding", new_callable=AsyncMock) as embed,
            patch("ps01_api.main.retrieve_chunks", new_callable=AsyncMock) as retrieve,
            patch("ps01_api.main.generate_claims", new_callable=AsyncMock) as generate,
            patch("ps01_api.main._save_history", new_callable=AsyncMock, return_value=True),
        ):
            auth.return_value = {"id": "trusted-session-user"}
            identity.return_value = {
                "user_id": "trusted-session-user",
                "organization_id": "trusted-org",
                "role": "CEO",
                "roles": ["CEO"],
            }
            embed.return_value = [0.0] * 1536
            retrieve.return_value = [
                {
                    "chunk_id": "authorized",
                    "content": "evidence",
                    "source_type": "pdf",
                    "page_number": 1,
                }
            ]
            generate.side_effect = IntegrationFailure(
                "Gemini generation timed out", code="provider_timeout"
            )
            response = self.client.post(
                "/api/v1/chat/query",
                headers={"Authorization": "Bearer trusted-session-token"},
                json={"query": "Summarize the available evidence."},
            )

        assert response.status_code == 503
        body = response.json()
        assert body["detail"] == "The answer service took too long to respond. Please try again."
        assert body["code"] == "provider_timeout"
        assert body["timing_ms"]["gemini_ms"] >= 0
        assert body["timing_ms"]["total_ms"] >= body["timing_ms"]["gemini_ms"]

    def test_provider_rate_limit_has_distinct_safe_error_contract(self) -> None:
        with (
            patch("ps01_api.main.verify_supabase_session", new_callable=AsyncMock) as auth,
            patch("ps01_api.main._identity", new_callable=AsyncMock) as identity,
            patch("ps01_api.main.revalidate_evidence", AsyncMock(side_effect=lambda c, s, t, e: e)),
            patch("ps01_api.main.create_embedding", new_callable=AsyncMock) as embed,
            patch("ps01_api.main.retrieve_chunks", new_callable=AsyncMock) as retrieve,
            patch("ps01_api.main.generate_claims", new_callable=AsyncMock) as generate,
            patch("ps01_api.main._save_history", new_callable=AsyncMock, return_value=True),
        ):
            auth.return_value = {"id": "trusted-session-user"}
            identity.return_value = {
                "user_id": "trusted-session-user",
                "organization_id": "trusted-org",
                "role": "CEO",
                "roles": ["CEO"],
            }
            embed.return_value = [0.0] * 1536
            retrieve.return_value = [
                {
                    "chunk_id": "authorized",
                    "content": "evidence",
                    "source_type": "pdf",
                    "page_number": 1,
                }
            ]
            generate.side_effect = IntegrationFailure(
                "Gemini rate limited", code="provider_rate_limited"
            )
            response = self.client.post(
                "/api/v1/chat/query",
                headers={"Authorization": "Bearer trusted-session-token"},
                json={"query": "Summarize the available evidence."},
            )

        assert response.status_code == 429
        assert response.json()["code"] == "provider_rate_limited"
        assert "rate-limited" in response.json()["detail"]

    def test_non_ceo_cannot_forge_a_ceo_context_header(self) -> None:
        with (
            patch("ps01_api.main._identity", new_callable=AsyncMock) as identity,
            patch("ps01_api.main._local_demo_enabled", return_value=True),
            patch("ps01_api.main.revalidate_evidence", AsyncMock(side_effect=lambda c, s, t, e: e)),
            patch("ps01_api.main.create_embedding", new_callable=AsyncMock) as embed,
        ):
            identity.return_value = {
                "user_id": "finance-user",
                "organization_id": "trusted-org",
                "role": "Finance Manager",
                "roles": ["Finance Manager"],
            }
            response = self.client.post(
                "/api/v1/chat/query",
                headers={
                    "Authorization": "Bearer trusted-finance-session",
                    "X-Demo-Role": "CEO",
                },
                json={"query": "Show all employee information."},
            )

        assert response.status_code == 403
        embed.assert_not_awaited()

    def test_ingestion_rejects_unsupported_file_type(self) -> None:
        with (
            patch("ps01_api.main._local_demo_enabled", return_value=True),
            patch(
                "ps01_api.main.require_local_ceo",
                new_callable=AsyncMock,
                return_value=("token", {}),
            ),
        ):
            response = self.client.post(
                "/api/v1/ingest/file",
                headers={"X-Source-Name": "notes.txt"},
                content=b"not an accepted source format",
            )

        assert response.status_code == 415


@pytest.mark.asyncio
async def test_non_ceo_cannot_request_ceo_demo_context() -> None:
    from ps01_api.config import get_settings
    from ps01_api.main import _context_token

    identity = {"role": "Finance Manager", "roles": ["Finance Manager"]}
    client = AsyncMock()
    with patch("ps01_api.main._local_demo_enabled", return_value=True):
        with pytest.raises(HTTPException) as error:
            await _context_token(client, get_settings(), "finance-user-token", identity, "CEO")

    assert error.value.status_code == 403
    client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_ceo_context_uses_server_side_role_session_without_returning_it(tmp_path) -> None:
    import json

    from ps01_api.config import get_settings
    from ps01_api.main import _context_token

    credentials_path = tmp_path / "demo-credentials.json"
    credentials_path.write_text(
        json.dumps(
            {
                "Finance Manager": {"email": "finance@novacore.demo", "password": "demo"},
                "CEO": {"email": "ceo@novacore.demo", "password": "demo"},
            }
        )
    )
    client = AsyncMock()
    client.post.return_value = SimpleNamespace(
        is_error=False,
        json=lambda: {"access_token": "server-only-role-token", "expires_in": 3600},
    )
    identity = {
        "role": "CEO",
        "roles": ["CEO"],
        "user_id": "ceo",
        "organization_id": "org",
        "email": "ceo@novacore.demo",
    }

    with (
        patch("ps01_api.main._local_demo_enabled", return_value=True),
        patch("ps01_api.main.DEMO_CREDENTIALS", credentials_path),
        patch(
            "ps01_api.main._identity",
            AsyncMock(
                return_value={
                    "organization_id": "org",
                    "role": "Finance Manager",
                    "email": "finance@novacore.demo",
                }
            ),
        ),
    ):
        token, role = await _context_token(
            client, get_settings(), "original-ceo-session", identity, "Finance Manager"
        )

    assert token == "server-only-role-token"
    assert role == "Finance Manager"
    assert client.post.await_args.kwargs["json"]["email"] == "finance@novacore.demo"
