from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
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


def business_date(value: Any) -> str | None:
    try:
        parsed = date.fromisoformat(value)
        return f"{parsed.day} {parsed:%B %Y}"
    except (ValueError, TypeError):
        return None


def business_amount(value: Any, currency: Any) -> str | None:
    # These are the two-decimal currencies supported by the existing corpus.
    # Unknown currencies and absent currency information never inherit a scale.
    if currency not in {"USD", "INR", "EUR", "GBP"} or type(value) is not int or value < 0:
        return None
    return f"{currency} {Decimal(value) / 100:,.2f}"


def business_record_answer(table: str, row_id: str, fields: dict, query: str) -> str:
    """Question-scoped prose from one authorized record; no inferred joins."""
    q = query.casefold()
    amount_only = bool(re.search(r"\b(?:amount|total|how much|value|salary)\b", q))
    date_only = bool(re.search(r"\b(?:when|date|approved on)\b", q))
    status_only = bool(re.search(r"\b(?:status|stage|approved|employment)\b", q)) and not date_only
    supplier_only = bool(re.search(r"\b(?:supplier|issued to)\b", q))
    broad = not any((amount_only, date_only, status_only, supplier_only))
    parts = []
    if table == "purchase_orders":
        if re.search(r"\b(?:who approved|approved by|approver)\b", q):
            return "The approver is not specified in this purchase order record."
        subject = f"Purchase order {row_id}"
        amount = business_amount(fields.get("total_minor_units"), fields.get("currency"))
        approved = business_date(fields.get("approved_on"))
        if broad:
            if fields.get("status") == "approved" and approved:
                subject += f" was approved on {approved}"
            elif fields.get("status"):
                subject += f" is {fields['status']}"
            if amount:
                subject += f" for {amount}"
            parts.append(subject + ".")
        else:
            if status_only and fields.get("status"):
                parts.append(f"{subject} is {fields['status']}.")
            if date_only and approved:
                parts.append(f"{subject} has a recorded approval date of {approved}.")
            if amount_only and amount:
                parts.append(f"{subject} totals {amount}.")
        if (broad or supplier_only) and fields.get("supplier"):
            supplier = str(fields["supplier"])
            parts.append(f"The supplier is {supplier}" + ("" if supplier.endswith(".") else "."))
        if "project" in q and fields.get("project_id"):
            parts.append(f"It relates to project {fields['project_id']}.")
        if "supplier id" in q and fields.get("supplier_id"):
            parts.append(f"The supplier ID is {fields['supplier_id']}.")
    elif table == "projects":
        subject = fields.get("name") or f"Project {row_id}"
        if fields.get("status"):
            parts.append(f"{subject} is in {fields['status']}.")
        if broad and fields.get("owner_team"):
            parts.append(f"The owning team is {fields['owner_team']}.")
        if (broad or "release" in q) and fields.get("release"):
            parts.append(f"The recorded release is {fields['release']}.")
        if "project id" in q:
            parts.append(f"The project ID is {row_id}.")
    elif table == "customers":
        subject = fields.get("name") or f"Customer {row_id}"
        parts.append(f"{subject} is a customer in the accessible records.")
        for field, label in (
            ("industry", "Industry"),
            ("account_status", "Account status"),
            ("payment_terms", "Payment terms"),
        ):
            if fields.get(field) and (broad or field.replace("_", " ") in q):
                parts.append(f"{label}: {fields[field]}.")
    elif table == "employees":
        subject = f"Employee {row_id}"
        if amount_only:
            amount = business_amount(
                fields.get("annual_salary_minor_units"), fields.get("currency")
            )
            if amount:
                parts.append(f"{subject} has a recorded annual salary of {amount}.")
        else:
            if fields.get("role"):
                parts.append(f"{subject}'s role is {fields['role']}.")
            if fields.get("employment_status"):
                parts.append(f"Their employment status is {fields['employment_status']}.")
    elif table == "payments":
        subject = f"Payment {row_id}"
        if amount_only:
            # The current payments schema has no currency field. A payment
            # attempt/settlement is never an invoice total or revenue figure.
            parts.append(
                "The payment record does not specify a currency, "
                "so I can’t give a reliable formatted amount."
            )
        else:
            if fields.get("status"):
                parts.append(f"{subject} is {fields['status']}.")
            attempted = business_date(fields.get("attempted_on"))
            if (broad or date_only) and attempted:
                parts.append(f"The attempt was recorded on {attempted}.")
            if fields.get("invoice_id"):
                parts.append(f"It refers to invoice {fields['invoice_id']}.")
    elif table == "opportunities":
        subject = f"The sales opportunity {row_id}"
        if fields.get("customer"):
            subject += f" for {fields['customer']}"
        if amount_only:
            parts.append(
                "The opportunity record does not specify a currency, "
                "so I can’t give a reliable formatted value."
            )
        elif fields.get("stage"):
            parts.append(f"{subject} is at the {fields['stage']} stage.")
    return " ".join(parts) or (
        "That detail is not specified in this record. "
        "Open its citation to inspect the available fields."
    )


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
            amount = business_amount(fields["total_minor_units"], fields["currency"])
            if amount is None:
                raise ValueError("Unsupported invoice amount or currency")
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
            f"{amount}. Payment status: {fields['payment_status']}. "
            f"Due date: {due}; status as of: {as_of}. "
            f"Overdue as of that date: {'yes' if overdue else 'no'}."
            f"{invoice_date}"
        )
    return f"{table} / {row_id}. " + "; ".join(
        f"{key.replace('_', ' ')}: {value}" for key, value in fields.items()
    )
