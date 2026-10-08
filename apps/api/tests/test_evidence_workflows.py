from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from ps01_api.ingestion import IngestionError
from ps01_api.main import app, original_path
from ps01_api.records import record_excerpt, validate_record

IDENTITY = {"user_id": "actor", "organization_id": "org", "role": "CEO", "roles": ["CEO"]}
ID = "11111111-1111-4111-8111-111111111111"
HEADERS = {"Authorization": "Bearer actor-token"}


def test_stream_requires_identity_before_opening():
    response = TestClient(app).post("/api/v1/chat/stream", json={"query": "Invoice?"})
    assert response.status_code == 401


def test_stream_stage_order_and_only_validated_final_text():
    row = {
        "chunk_id": ID,
        "source_type": "pdf",
        "page_number": 1,
        "content": "Acme terms are net 30 days.",
        "source_name": "Agreement",
    }
    with (
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch("ps01_api.main.create_embedding", AsyncMock(return_value=[0] * 1536)),
        patch("ps01_api.main.retrieve_chunks", AsyncMock(return_value=[row])),
        patch(
            "ps01_api.main.generate_claims",
            AsyncMock(return_value={"claims": [{"evidence_ids": [f"{ID}:0"]}]}),
        ),
        patch("ps01_api.main._save_history", AsyncMock(return_value=True)),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/stream", headers=HEADERS, json={"query": "Terms?"}
        )
    assert response.status_code == 200
    text = response.text
    assert text.index('"stage": "searching_knowledge"') < text.index(
        '"stage": "generating_response"'
    )
    assert text.index('"stage": "validating_citations"') < text.index("event: result")
    assert "Acme terms" not in text[: text.index("event: result")]
    assert '"history_saved":true' in text


def test_stream_forged_role_denied_before_embedding():
    with (
        patch(
            "ps01_api.main._identity",
            AsyncMock(return_value={**IDENTITY, "role": "HR Manager", "roles": ["HR Manager"]}),
        ),
        patch("ps01_api.main.create_embedding", AsyncMock()) as embedding,
    ):
        response = TestClient(app).post(
            "/api/v1/chat/stream",
            headers={**HEADERS, "X-Demo-Role": "CEO"},
            json={"query": "Finance"},
        )
    assert response.status_code == 403
    embedding.assert_not_awaited()


def test_original_preview_traversal_is_never_resolved():
    assert (
        original_path({"metadata": {"synthetic": True, "local_demo_path": "../../README.md"}})
        is None
    )
    assert original_path({"storage_path": "README.md"}) is None
    assert (
        original_path(
            {"metadata": {"synthetic": True, "local_demo_path": "structured/finance.json"}}
        )
        is None
    )


def test_original_preview_requires_document_grant_and_denies_without_metadata():
    with (
        patch("ps01_api.main._local_demo_enabled", return_value=True),
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch(
            "ps01_api.main._rest_rows", AsyncMock(return_value=httpx.Response(200, json=[]))
        ) as rows,
    ):
        response = TestClient(app).get(f"/api/v1/sources/{ID}/original", headers=HEADERS)
    assert response.status_code == 404
    assert response.json() == {"detail": "Source not found"}
    assert rows.await_args.args[3] == "documents"
    assert rows.await_args.args[2] == "actor-token"


def test_structured_record_key_and_scope_are_server_owned():
    with pytest.raises(IngestionError):
        validate_record("arbitrary_sql", "id", {"id": "id"})
    with pytest.raises(IngestionError):
        validate_record("invoices", "INV-2048", {"invoice_id": "different"})
    with pytest.raises(IngestionError):
        validate_record(
            "invoices", "INV-2048", {"invoice_id": "INV-2048", "organization_id": "forged"}
        )


def test_overdue_is_computed_from_record_snapshot_not_wall_clock():
    excerpt = record_excerpt(
        "invoices",
        "INV-2048",
        {
            "total_minor_units": 4800000,
            "currency": "USD",
            "payment_status": "unpaid",
            "due_date": "2026-10-01",
            "status_as_of": "2026-10-08",
            "customer": "Acme",
        },
    )
    assert "USD 48,000.00" in excerpt
    assert "Overdue as of that date: yes" in excerpt
    assert "2026-10-08" in excerpt


def test_conversation_list_is_actor_org_and_role_scoped():
    with (
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch(
            "ps01_api.main._rest_rows", AsyncMock(return_value=httpx.Response(200, json=[]))
        ) as rows,
    ):
        response = TestClient(app).get("/api/v1/conversations", headers=HEADERS)
    assert response.status_code == 200
    args = rows.await_args.kwargs["params"]
    assert args["user_id"] == "eq.actor" and args["organization_id"] == "eq.org"
    assert args["active_role"] == "eq.CEO" and args["deleted_at"] == "is.null"


def test_reopen_revoked_citation_removes_saved_answer_and_source_title():
    stored = [
        {
            "query": "Terms?",
            "response": {
                "claims": [
                    {
                        "text": "secret",
                        "citations": [
                            {"citation_id": ID, "title": "Restricted title", "excerpt": "secret"}
                        ],
                    }
                ]
            },
        }
    ]
    with (
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch("ps01_api.main._history_rows", AsyncMock(return_value=stored)),
        patch("ps01_api.main._rest_rows", AsyncMock(return_value=httpx.Response(200, json=[]))),
    ):
        response = TestClient(app).get(f"/api/v1/conversations/{ID}", headers=HEADERS)
    assert response.status_code == 200
    assert "Restricted title" not in response.text
    assert response.json()["turns"][0]["response"]["state"] == "INSUFFICIENT_EVIDENCE"


def test_hide_conversation_uses_actor_session_and_all_scope_predicates():
    captured = []

    async def handle(request):
        captured.append(request)
        return httpx.Response(204)

    @asynccontextmanager
    async def client():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as instance:
            yield instance

    with (
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch("ps01_api.main.request_client", client),
    ):
        response = TestClient(app).delete(f"/api/v1/conversations/{ID}", headers=HEADERS)
    assert response.status_code == 200
    request = captured[0]
    assert request.method == "PATCH"
    assert request.headers["Authorization"] == "Bearer actor-token"
    assert request.url.params["user_id"] == "eq.actor"
    assert request.url.params["organization_id"] == "eq.org"
    assert request.url.params["active_role"] == "eq.CEO"


def test_history_requires_authentication():
    assert TestClient(app).get("/api/v1/conversations").status_code == 401
    assert TestClient(app).delete(f"/api/v1/conversations/{ID}").status_code == 401


def test_additive_migration_keeps_invoker_and_no_user_admin_writes():
    root = Path(__file__).resolve().parents[3]
    schema = (
        root / "supabase/migrations/20261009000100_relational_evidence_history.sql"
    ).read_text()
    assert "security_invoker = true" in schema
    assert "as restrictive" in schema
    assert "r.fields = knowledge_chunks.metadata->'fields'" in schema
    assert "grant update(deleted_at)" in schema
    assert "grant all on public.invoices to service_role" in schema


@pytest.mark.parametrize(
    "citations", [[], [{"citation_id": "invalid", "evidence_id": "invalid:0"}]]
)
def test_reopen_client_written_answer_cannot_bypass_canonical_rebuild(citations):
    stored = [
        {
            "query": "Terms?",
            "response": {
                "answer": "fabricated",
                "claims": [{"text": "fabricated", "citations": citations}],
            },
        }
    ]
    with (
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch("ps01_api.main._history_rows", AsyncMock(return_value=stored)),
        patch("ps01_api.main._rest_rows", AsyncMock()) as rows,
    ):
        response = TestClient(app).get(f"/api/v1/conversations/{ID}", headers=HEADERS)
    assert response.status_code == 200
    assert "fabricated" not in response.text
    assert response.json()["turns"][0]["response"]["claims"] == []
    rows.assert_not_awaited()


@pytest.mark.parametrize(
    "saved",
    [
        None,
        {"claims": [None]},
        {"claims": "invalid", "trace": None},
        {
            "claims": [{"citations": [{"citation_id": {}, "evidence_id": "invalid"}]}],
            "trace": {"generation_model": "fabricated", "timing_ms": {"total_ms": 1}},
        },
    ],
)
def test_malformed_history_content_fails_closed_without_crashing(saved):
    with (
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch(
            "ps01_api.main._history_rows",
            AsyncMock(return_value=[{"query": "Terms?", "response": saved}]),
        ),
    ):
        response = TestClient(app).get(f"/api/v1/conversations/{ID}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["turns"][0]["response"]["claims"] == []
    trace = response.json()["turns"][0]["response"]["trace"]
    assert trace["history_replay"] is True
    assert trace["generation_model"] is None
    assert trace["timing_ms"] == {}
