"""Recording transport stubs: these tests do not call a real model or database."""

import copy
import hashlib
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from test_integrations import settings

from ps01_api import integrations, main
from ps01_api.evidence_audit import EVIDENCE_MARKER, EvidenceAudit, payload_manifest
from ps01_api.integrations import IntegrationFailure, generate_claims
from ps01_api.rag import prepare_generation_context


@pytest.fixture(autouse=True)
def isolated_circuits():
    integrations._GENERATION_CIRCUITS.clear()
    yield
    integrations._GENERATION_CIRCUITS.clear()


def evidence(content="Invoice INV-1001 totals USD 100.00", chunk="allowed"):
    return {
        "chunk_id": chunk,
        "source_type": "pdf",
        "page_number": 1,
        "source_id": "INV-1001",
        "content": content,
    }


async def test_recorded_fallback_payloads_have_exact_independent_manifests():
    writes, requests = [], []

    async def write(method, event_id, body):
        writes.append((method, event_id, copy.deepcopy(body)))

    audit = EvidenceAudit(
        "correlation", {"user_id": "actor", "organization_id": "org"}, "Finance Manager", write
    )
    audit.context_user_id = "finance-user"
    authorized_snapshots = [{"allowed"}, {"second"}]
    contexts = [[evidence()], [evidence("Invoice INV-1001 totals USD 200.00", "second")]]

    async def before():
        prompt, rows = prepare_generation_context("Invoice INV-1001 total", contexts[len(requests)])
        audit.canonical_ids = [row["evidence_id"] for row in rows]
        return prompt

    async def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": '{"claims":[{"evidence_ids":["second:0"]}]}'}]}}
                ]
            },
        )

    with patch.object(
        integrations, "generation_models", AsyncMock(return_value=["primary", "fallback"])
    ):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await generate_claims(client, settings(), "unused", before, audit.observe)
    await audit.validation("CITATION_VALIDATED")
    starts = [body for method, _, body in writes if method == "POST"]
    assert len(starts) == len(requests) == 2
    for index, (entry, request) in enumerate(zip(starts, requests, strict=True)):
        serialized = request["contents"][0]["parts"][0]["text"].rpartition(EVIDENCE_MARKER)[2]
        ids = [row["evidence_id"] for row in json.loads(serialized)]
        assert entry["details"]["evidence_ids"] == ids
        assert {value.split(":")[0] for value in ids} <= authorized_snapshots[index]
        assert entry["details"]["payload_sha256"] == hashlib.sha256(serialized.encode()).hexdigest()
        assert entry["details"]["request_id"] == "correlation"
        assert entry["details"]["context_user_id"] == "finance-user"
        assert "content" not in entry["details"] and "token" not in json.dumps(entry)
    assert starts[0]["details"]["payload_sha256"] != starts[1]["details"]["payload_sha256"]
    assert [entry["details"]["provider_outcome"] for entry in audit.entries.values()] == [
        "provider_unavailable",
        "success",
    ]
    assert [entry["details"]["validation_outcome"] for entry in audit.entries.values()] == [
        "not_run",
        "CITATION_VALIDATED",
    ]
    assert result["claims"]


@pytest.mark.parametrize("ids", [["fabricated:0"], [], ["allowed:0", "allowed:0"]])
def test_manifest_rejects_ids_not_in_server_selected_payload(ids):
    prompt, _ = prepare_generation_context("Invoice total", [evidence()])
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    with pytest.raises(IntegrationFailure, match="mismatch"):
        payload_manifest(payload, ids)


def test_hash_changes_for_changed_content_with_identical_evidence_ids():
    hashes = []
    for content in ("Invoice INV-1001 totals USD 100.00", "Invoice INV-1001 totals USD 101.00"):
        prompt, rows = prepare_generation_context("Invoice total", [evidence(content)])
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        manifest = payload_manifest(payload, [row["evidence_id"] for row in rows])
        assert manifest["evidence_ids"] == ["allowed:0"]
        hashes.append(manifest["payload_sha256"])
    assert hashes[0] != hashes[1]


async def test_unavailable_manifest_store_blocks_outbound_provider_request():
    audit = EvidenceAudit(
        "id",
        {"user_id": "actor", "organization_id": "org"},
        "CEO",
        AsyncMock(
            side_effect=IntegrationFailure("audit down", code="evidence_manifest_unavailable")
        ),
    )
    prompt, rows = prepare_generation_context("Invoice total", [evidence()])
    audit.canonical_ids = [row["evidence_id"] for row in rows]
    handler = AsyncMock()
    with patch.object(integrations, "generation_models", AsyncMock(return_value=["primary"])):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(IntegrationFailure, match="audit down") as failure:
                await generate_claims(client, settings(), prompt, attempt_observer=audit.observe)
    assert failure.value.model_attempts[0]["attempted"] is False
    handler.assert_not_called()
    assert not integrations._circuit(settings(), "primary").in_flight


def test_browser_cannot_supply_manifest_or_authorized_ids():
    response = TestClient(main.app).post(
        "/api/v1/chat/query",
        json={
            "query": "invoice total",
            "manifest": {"evidence_ids": ["fabricated:0"]},
        },
    )
    assert response.status_code == 422
