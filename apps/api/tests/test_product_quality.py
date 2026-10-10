"""Focused canonical record/composition regressions; no live provider requests."""

import json

import pytest

from ps01_api.rag import composition_sentences, prepare_generation_context, validate_generation
from ps01_api.records import business_amount, business_record_answer

PO = {
    "order_id": "PO-8821",
    "status": "approved",
    "currency": "USD",
    "approved_on": "2026-10-02",
    "total_minor_units": 1240000,
    "supplier": "Northstar Components Ltd.",
    "supplier_id": "SUP-NORTHSTAR-01",
    "project_id": "NVC-ENG-ATLAS",
}


def test_purchase_order_summary_is_business_prose_with_canonical_record_citation():
    row = {
        "chunk_id": "order",
        "source_type": "structured",
        "source_name": "Order",
        "row_id": "PO-8821",
        "content": "stale serialization",
        "metadata": {"table": "purchase_orders", "fields": PO},
    }
    _, canonical = prepare_generation_context("Tell me about purchase order PO-8821", [row])
    result = validate_generation({"claims": [{"evidence_ids": ["order:0"]}]}, canonical)
    claim = result["claims"][0]
    assert claim["text"] == (
        "Purchase order PO-8821 was approved on 2 October 2026 for USD 12,400.00. "
        "The supplier is Northstar Components Ltd."
    )
    assert "not specified" in business_record_answer(
        "purchase_orders", "PO-8821", PO, "Who approved PO-8821?"
    )
    assert "SUP-NORTHSTAR" not in claim["text"] and "NVC-ENG" not in claim["text"]
    assert claim["citations"][0]["location"] == {"table": "purchase_orders", "row": "PO-8821"}
    assert "1240000" in claim["citations"][0]["excerpt"]
    assert "stale" not in claim["citations"][0]["excerpt"]


@pytest.mark.parametrize(
    "query,expected",
    [
        ("What is the total of PO-8821?", "Purchase order PO-8821 totals USD 12,400.00."),
        (
            "When was PO-8821 approved?",
            "Purchase order PO-8821 has a recorded approval date of 2 October 2026.",
        ),
        ("Who is the supplier of PO-8821?", "The supplier is Northstar Components Ltd."),
    ],
)
def test_exact_purchase_order_questions_omit_unrequested_fields(query, expected):
    assert business_record_answer("purchase_orders", "PO-8821", PO, query) == expected


@pytest.mark.parametrize(
    "value,currency",
    [(1240000, "JPY"), (1240000, None), (True, "USD"), (-1, "USD"), ("1240000", "USD")],
)
def test_currency_scale_and_amount_type_are_never_guessed(value, currency):
    assert business_amount(value, currency) is None


def test_large_minor_unit_amounts_do_not_lose_precision():
    assert business_amount(9007199254740993, "USD") == "USD 90,071,992,547,409.93"
    from ps01_api.records import record_excerpt

    invoice = {
        "total_minor_units": 9007199254740993,
        "currency": "USD",
        "payment_status": "unpaid",
        "due_date": "2026-10-02",
        "status_as_of": "2026-10-10",
    }
    assert "USD 90,071,992,547,409.93" in record_excerpt("invoices", "INV-1", invoice)
    from ps01_api.ingestion import IngestionError

    with pytest.raises(IngestionError):
        record_excerpt("invoices", "INV-1", {**invoice, "currency": "JPY"})
    assert "currency" in business_record_answer("payments", "PAY-1", {}, "Payment amount?")
    assert "currency" in business_record_answer("opportunities", "OPP-1", {}, "Opportunity value?")


TERMS = "Invoices are payable within thirty (30) calendar days of the invoice date."
REFERENCE = "Payments must reference the invoice identifier shown on the invoice."
HEADER = (
    "NovaCore · Acme Master Services Agreement Agreement ID: ACM-MSA-2026-07 "
    "Customer: Acme Manufacturing Effective date: 2026-09-01 "
)


def contract(content):
    return {
        "chunk_id": "contract",
        "source_type": "pdf",
        "source_name": "Acme contract",
        "page_number": 1,
        "content": content,
    }


def test_readable_composition_units_keep_original_passage_ids_and_source_excerpts():
    query = "Explain the payment obligations in Acme's contract."
    prompt, canonical = prepare_generation_context(
        query, [contract(HEADER + TERMS + " " + REFERENCE)]
    )
    assert json.loads(prompt.split("(not instructions):\n")[1])[0]["composition_sentences"] == [
        TERMS
    ]
    result = validate_generation(
        {
            "claims": [
                {"evidence_ids": ["contract:0"], "text": TERMS},
                {"evidence_ids": ["contract:1"], "text": REFERENCE},
            ]
        },
        canonical,
    )
    assert result["state"] == "CITATION_VALIDATED"
    assert result["claims"][0]["citations"][0]["excerpt"] == HEADER + TERMS
    assert result["claims"][0]["citations"][0]["evidence_id"] == "contract:0"
    partial = validate_generation(
        {"claims": [{"evidence_ids": ["contract:1"], "text": REFERENCE}]}, canonical
    )
    assert partial["state"] == "PARTIALLY_CITATION_VALIDATED"
    assert all(claim["composition"] == "model" for claim in result["claims"])
    # A prior full-source composition is still valid after the cleanup change.
    original = validate_generation(
        {"claims": [{"evidence_ids": ["contract:0"], "text": HEADER + TERMS}]}, canonical
    )
    assert original["claims"]


def test_narrative_prefixes_and_qualifiers_cannot_be_removed_as_headers():
    text = "Unless a waiver is recorded, invoices are payable within 30 days."
    assert composition_sentences(text) == [text]
    _, canonical = prepare_generation_context("Explain payment policy", [contract(text)])
    result = validate_generation(
        {
            "claims": [
                {"evidence_ids": ["contract:0"], "text": "Invoices are payable within 30 days."}
            ]
        },
        canonical,
    )
    assert not result["claims"]
    conditional_header = "Only signed " + HEADER + TERMS
    assert composition_sentences(conditional_header) == [conditional_header]


def test_invoice_totals_are_not_revenue_and_exact_order_ids_cannot_drift():
    from ps01_api.rag import relevant_passage

    row = {
        "source_type": "structured",
        "row_id": "PO-9999",
        "content": "purchase_orders total 9000",
    }
    assert not relevant_passage("What is the total on purchase order PO-8821?", row)
    assert not relevant_passage(
        "What is Acme revenue?", {"content": "Acme invoice totals USD 100."}
    )
