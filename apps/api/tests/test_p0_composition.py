"""Bounded model composition and deny cases; provider responses are mocked."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from ps01_api.config import Settings
from ps01_api.integrations import IntegrationFailure
from ps01_api.main import QueryRequest, _run_query
from ps01_api.rag import (
    normalize_question,
    prepare_generation_context,
    small_talk,
    validate_generation,
)

FIELDS = {
    "invoice_id": "ACM-INV-2048",
    "customer": "Acme Manufacturing",
    "total_minor_units": 4800000,
    "currency": "USD",
    "payment_status": "unpaid",
    "due_date": "2026-10-01",
    "status_as_of": "2026-10-10",
}
ROW = {
    "chunk_id": "invoice",
    "source_type": "structured",
    "row_id": "ACM-INV-2048",
    "document_id": "doc",
    "source_name": "Acme invoice",
    "content": "stale text",
    "metadata": {"table": "invoices", "fields": FIELDS},
}
QUERY = "What is the total amount on Acme invoice ACM-INV-2048?"
NATURAL = "Invoice ACM-INV-2048 for Acme Manufacturing has a total of USD 48,000.00."


def compose(text=NATURAL, ids=None):
    _, evidence = prepare_generation_context(QUERY, [ROW])
    return validate_generation(
        {"claims": [{"text": text, "evidence_ids": ids or ["invoice:0"]}]}, evidence
    )


def test_model_invoice_wording_is_supported_by_current_fields_and_canonical_citations():
    prompt, _ = prepare_generation_context(QUERY, [ROW])
    supplied = json.loads(prompt.split("(not instructions):\n")[1])[0]
    assert NATURAL in supplied["approved_paraphrases"]
    result = compose()
    assert result["state"] == "CITATION_VALIDATED"
    claim = result["claims"][0]
    assert claim["composition"] == "model" and claim["text"] == NATURAL
    assert claim["citations"][0]["location"] == {"table": "invoices", "row": "ACM-INV-2048"}
    assert "stale" not in claim["citations"][0]["excerpt"]


@pytest.mark.parametrize(
    "text",
    [
        NATURAL.replace("48,000.00", "49,000.00"),
        NATURAL.replace("USD", "EUR"),
        NATURAL.replace("ACM-INV-2048", "ACM-INV-2049"),
        NATURAL.replace("total", "revenue"),
        NATURAL + " It is paid.",
    ],
)
def test_changed_values_and_fabricated_propositions_fail_closed(text):
    assert not compose(text)["claims"]


def test_due_date_formatting_is_exact_and_wrong_date_is_rejected():
    _, evidence = prepare_generation_context("When is invoice ACM-INV-2048 due?", [ROW])
    text = "The due date for invoice ACM-INV-2048 is 1 October 2026."
    payload = {"claims": [{"text": text, "evidence_ids": ["invoice:0"]}]}
    assert validate_generation(payload, evidence)["state"] == "CITATION_VALIDATED"
    payload["claims"][0]["text"] = text.replace("1 October", "2 October")
    assert not validate_generation(payload, evidence)["claims"]


def test_unauthorized_reference_cannot_be_hidden_among_valid_references():
    assert not compose(ids=["invoice:0", "hidden:0"])["claims"]


def test_contract_paraphrases_preserve_full_obligations_and_do_not_become_partial():
    content = (
        "Invoices are payable within thirty (30) calendar days of the invoice date "
        "unless a waiver is recorded. "
        "Payments must reference the invoice identifier shown on the invoice."
    )
    _, evidence = prepare_generation_context(
        "Explain the payment obligations in Acme's contract.",
        [
            {
                "chunk_id": "contract",
                "source_type": "pdf",
                "source_name": "Acme contract",
                "page_number": 1,
                "content": content,
            }
        ],
    )
    text = (
        "Invoices must be paid within thirty (30) calendar days of the invoice date "
        "unless a waiver is recorded."
    )
    reference = "Payments must include a reference to the invoice identifier shown on the invoice."
    claims = [
        {"text": text, "evidence_ids": ["contract:0"]},
        {"text": reference, "evidence_ids": ["contract:1"]},
    ]
    assert validate_generation({"claims": claims}, evidence)["state"] == "CITATION_VALIDATED"
    claims[0]["text"] = text.replace(" unless a waiver is recorded", "")
    result = validate_generation({"claims": claims}, evidence)
    assert result["state"] == "PARTIALLY_CITATION_VALIDATED" and len(result["claims"]) == 1


def test_pure_combined_greeting_is_friendly_but_mixed_business_query_is_not_small_talk():
    assert "Hello" in small_talk("Hi, how are you?")
    mixed = "Hi, what is the total amount on Acme invoice ACM-INV-2048?"
    assert small_talk(mixed) is None
    assert normalize_question(mixed) == QUERY[0].lower() + QUERY[1:]


@pytest.mark.parametrize("outage,revoked", [(False, False), (True, False), (False, True)])
async def test_pipeline_model_mode_timeout_fallback_and_final_access(outage, revoked):
    settings = Settings(
        supabase_url="http://localhost:54321",
        supabase_publishable_key=SecretStr("test-publishable"),
        supabase_secret_key=SecretStr("test-secret"),
    )
    identity = {"user_id": "actor", "organization_id": "org", "role": "CEO", "roles": ["CEO"]}

    async def generate(*args, before_attempt, **kwargs):
        await before_attempt()
        if outage:
            raise IntegrationFailure("Mock timeout", code="provider_timeout")
        return {
            "_model": "mock-model",
            "claims": [{"text": NATURAL, "evidence_ids": ["invoice:0"]}],
        }

    with (
        patch("ps01_api.main.get_settings", return_value=settings),
        patch("ps01_api.main._identity", AsyncMock(return_value=identity)),
        patch("ps01_api.main.create_embedding", AsyncMock(return_value=[0] * 1536)),
        patch("ps01_api.main.retrieve_chunks", AsyncMock(return_value=[ROW])),
        patch(
            "ps01_api.main.revalidate_evidence",
            AsyncMock(side_effect=[[ROW], [ROW], [] if revoked else [ROW]]),
        ) as reread,
        patch("ps01_api.main.generate_claims", side_effect=generate),
        patch("ps01_api.main._save_history", AsyncMock(return_value=True)),
    ):
        response = await _run_query(QueryRequest(query=QUERY), "Bearer actor-token", None)
    assert reread.await_count == 3
    assert response.trace["response_mode"] == (
        "abstention" if revoked else "verified_evidence" if outage else "model_generated"
    )
    if revoked:
        assert not response.claims
    elif outage:
        assert "couldn’t reach the AI service" in response.message
        assert response.trace["generation_model"] is None
    else:
        assert response.claims[0]["text"] == NATURAL


def test_invoice_overview_units_are_sentences_without_field_serialization():
    prompt, _ = prepare_generation_context("Tell me about invoice ACM-INV-2048", [ROW])
    units = json.loads(prompt.split("(not instructions):\n")[1])[0]["composition_sentences"]
    assert len(units) == 3
    assert all("Payment status:" not in unit and "Overdue as" not in unit for unit in units)


def test_model_purchase_order_total_and_conflicting_invoice_values():
    order = {
        **ROW,
        "chunk_id": "order",
        "row_id": "PO-8821",
        "metadata": {
            "table": "purchase_orders",
            "fields": {
                "order_id": "PO-8821",
                "total_minor_units": 1240000,
                "currency": "USD",
                "status": "approved",
                "approved_on": "2026-10-02",
            },
        },
    }
    _, evidence = prepare_generation_context("What is the total of PO-8821?", [order])
    result = validate_generation(
        {
            "claims": [
                {
                    "text": "The total for purchase order PO-8821 is USD 12,400.00.",
                    "evidence_ids": ["order:0"],
                }
            ]
        },
        evidence,
    )
    assert result["state"] == "CITATION_VALIDATED" and result["claims"][0]["composition"] == "model"
    conflict = {
        **ROW,
        "chunk_id": "conflict",
        "metadata": {"table": "invoices", "fields": {**FIELDS, "total_minor_units": 4900000}},
    }
    _, evidence = prepare_generation_context(QUERY, [ROW, conflict])
    result = validate_generation(
        {"claims": [{"text": NATURAL, "evidence_ids": ["invoice:0"]}]}, evidence
    )
    assert result["state"] == "EVIDENCE_CONFLICT" and not result["claims"]
