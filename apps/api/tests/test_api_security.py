from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

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

        async def generate(_client, _settings, prompt):
            captured.append(prompt)
            return {
                "claims": [
                    {
                        "text": "Invoice INV-2048 is USD 48,000.",
                        "citation_ids": [authorized["chunk_id"]],
                    }
                ]
            }

        with (
            patch("ps01_api.main.verify_supabase_session", new_callable=AsyncMock) as auth,
            patch("ps01_api.main.create_embedding", new_callable=AsyncMock) as embed,
            patch("ps01_api.main.retrieve_chunks", new_callable=AsyncMock) as retrieve,
            patch("ps01_api.main.generate_claims", new_callable=AsyncMock) as generate_mock,
        ):
            auth.return_value = {"id": "trusted-session-user"}
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
        assert response.json()["trace"]["unauthorized_evidence_sent_to_model"] == 0
        assert len(captured) == 1
        assert "USD 48,000" in captured[0]
        assert "trusted-session-token" not in captured[0]
        assert retrieve.await_args.args[2] == "trusted-session-token"
        assert generate_mock.await_count == 1

    def test_empty_authorized_retrieval_never_calls_the_generator(self) -> None:
        with (
            patch("ps01_api.main.verify_supabase_session", new_callable=AsyncMock) as auth,
            patch("ps01_api.main.create_embedding", new_callable=AsyncMock) as embed,
            patch("ps01_api.main.retrieve_chunks", new_callable=AsyncMock) as retrieve,
            patch("ps01_api.main.generate_claims", new_callable=AsyncMock) as generate,
        ):
            auth.return_value = {"id": "trusted-session-user"}
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
        assert response.json()["trace"]["unauthorized_evidence_sent_to_model"] == 0
        generate.assert_not_awaited()

    def test_source_lookup_requires_a_bearer_session(self) -> None:
        response = self.client.get("/api/v1/sources/11111111-1111-4111-8111-111111111111")
        assert response.status_code == 401
