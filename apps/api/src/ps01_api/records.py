from __future__ import annotations

from datetime import date
from typing import Any

from .ingestion import IngestionError

# Whitelisted tables and business keys; supplied fields never control SQL names.
RECORD_KEYS = {
    "customers": "customer_id",
    "projects": "project_id",
    "employees": "employee_id",
    "invoices": "invoice_id",
    "payments": "payment_id",
    "purchase_orders": "order_id",
    "opportunities": "opportunity_id",
}


def validate_record(table: str, row_id: str, fields: dict[str, Any]) -> None:
    key = RECORD_KEYS.get(table)
    if not key or fields.get(key) != row_id:
        raise IngestionError("Choose a supported table and match its business key to the row ID")
    if {"organization_id", "document_id"} & fields.keys():
        raise IngestionError("Organization and source identity are assigned by the server")


def record_excerpt(table: str, row_id: str, fields: dict[str, Any]) -> str:
    """Canonical business rendering of actual database fields, no model inference."""
    if table == "invoices" and all(
        key in fields
        for key in (
            "total_minor_units",
            "currency",
            "payment_status",
            "due_date",
            "status_as_of",
        )
    ):
        try:
            amount = int(fields["total_minor_units"]) / 100
            due, as_of = (
                date.fromisoformat(fields["due_date"]),
                date.fromisoformat(fields["status_as_of"]),
            )
        except (ValueError, TypeError):
            raise IngestionError("Invoice amount and dates must be valid") from None
        overdue = fields["payment_status"] == "unpaid" and due < as_of
        invoice_date = ""
        if fields.get("invoice_date"):
            try:
                invoice_date = f" Invoice date: {date.fromisoformat(fields['invoice_date'])}."
            except (ValueError, TypeError):
                raise IngestionError("Invoice date must be valid") from None
        return (
            f"Invoice {row_id} for {fields.get('customer', 'the customer')} totals "
            f"{fields['currency']} {amount:,.2f}. Payment status: {fields['payment_status']}. "
            f"Due date: {due}; status as of: {as_of}. "
            f"Overdue as of that date: {'yes' if overdue else 'no'}."
            f"{invoice_date}"
        )
    return f"{table} / {row_id}. " + "; ".join(
        f"{key.replace('_', ' ')}: {value}" for key, value in fields.items()
    )
