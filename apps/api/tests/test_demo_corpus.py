from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "data" / "demo"


def test_manifest_sources_are_real_unique_and_role_scoped() -> None:
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    roles = set(manifest["roles"])
    sources = manifest["sources"]

    assert len({source["source_id"] for source in sources}) == len(sources)
    assert {source["source_type"] for source in sources} == {"pdf", "image_ocr", "structured"}
    for source in sources:
        assert (CORPUS / source["path"]).is_file()
        assert set(source["allowed_roles"]) <= roles


def test_corpus_covers_required_pdf_image_and_record_domains() -> None:
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    sources = manifest["sources"]
    paths = {source["path"] for source in sources}
    tables = {
        json.loads((CORPUS / source["path"]).read_text())["table"]
        for source in sources
        if source["source_type"] == "structured"
    }

    assert {
        "documents/contracts/acme-contract-ACM-MSA-2026-07.pdf",
        "documents/finance/finance-policy-2026.pdf",
        "documents/hr/employee-handbook-2026.pdf",
        "documents/security/security-policy-2026.pdf",
        "documents/product/atlas-gateway-specification.pdf",
        "documents/procurement/northstar-supplier-agreement.pdf",
    } <= paths
    assert {
        "documents/finance/acme-invoice-ACM-INV-2048.png",
        "documents/procurement/purchase-order-PO-8821.png",
        "documents/finance/receipt-RCP-2048.png",
        "documents/hr/employee-acknowledgement-EMP-020.png",
    } <= paths
    assert {"customers", "invoices", "payments", "employees", "projects", "orders"} <= tables


def test_acme_invoice_payment_and_contract_relationships_are_consistent() -> None:
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    structured = {
        json.loads((CORPUS / source["path"]).read_text())["table"]: json.loads(
            (CORPUS / source["path"]).read_text()
        )["records"]
        for source in manifest["sources"]
        if source["source_type"] == "structured"
    }

    customer = structured["customers"][0]
    invoice = structured["invoices"][0]
    payment = structured["payments"][0]
    assert customer["customer_id"] == invoice["customer_id"] == payment["customer_id"]
    assert customer["contract_id"] == invoice["contract_id"] == "ACM-MSA-2026-07"
    assert payment["invoice_id"] == invoice["invoice_id"] == "ACM-INV-2048"
    assert invoice["due_date"] < "2026-10-08" and invoice["payment_status"] == "unpaid"
    assert payment["status"] == "declined" and payment["settled_minor_units"] == 0
