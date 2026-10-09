from __future__ import annotations

import json
import runpy
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "data" / "demo"
SEED_SCRIPT = ROOT / "apps" / "api" / "scripts" / "seed_local_demo.py"


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
    counts = {
        kind: sum(source["source_type"] == kind for source in sources)
        for kind in ("pdf", "image_ocr", "structured")
    }
    tables = {
        json.loads((CORPUS / source["path"]).read_text())["table"]
        for source in sources
        if source["source_type"] == "structured"
    }

    assert counts == {"pdf": 8, "image_ocr": 4, "structured": 7}
    assert {
        "documents/contracts/acme-contract-ACM-MSA-2026-07.pdf",
        "documents/security/prompt-injection-test-01.pdf",
    } <= paths
    assert {
        "documents/finance/acme-invoice-ACM-INV-2048.png",
        "documents/hr/employee-acknowledgement-EMP-020.png",
    } <= paths
    assert {
        "invoices",
        "projects",
        "employees",
        "payments",
        "customers",
        "purchase_orders",
        "opportunities",
    } == tables
    assert all(
        any(role in source["allowed_roles"] for source in sources) for role in manifest["roles"]
    )


def test_acme_invoice_status_and_contract_relationships_are_consistent() -> None:
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    structured = {
        json.loads((CORPUS / source["path"]).read_text())["table"]: json.loads(
            (CORPUS / source["path"]).read_text()
        )["records"]
        for source in manifest["sources"]
        if source["source_type"] == "structured"
    }

    invoice = structured["invoices"][0]
    assert invoice["contract_id"] == "ACM-MSA-2026-07"
    assert invoice["due_date"] < "2026-10-08" and invoice["payment_status"] == "unpaid"


def test_seed_prunes_only_removed_documents_with_local_demo_markers() -> None:
    prune = runpy.run_path(str(SEED_SCRIPT))["prune_removed_demo_sources"]
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[{"id": "retained"}, {"id": "stale-demo"}])
        return httpx.Response(204)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        removed = prune(client, "http://local.test", "local-key", "org-id", {"retained"})

    assert removed == 1
    assert requests[0].url.params.get("organization_id") == "eq.org-id"
    assert requests[0].url.params.get("metadata->>synthetic") == "eq.true"
    assert requests[0].url.params.get("metadata->>local_demo_path") == "not.is.null"
    assert len(requests) == 2
    assert requests[1].url.params.get("id") == "eq.stale-demo"


def test_database_json_field_order_does_not_change_business_row_identity(tmp_path, monkeypatch):
    collect = runpy.run_path(str(SEED_SCRIPT))["collect_candidates"]
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    sources = [source for source in manifest["sources"] if source["source_type"] == "structured"]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"sources": sources}))
    monkeypatch.setitem(collect.__globals__, "MANIFEST", manifest_path)
    database_records, expected = {}, {}
    for source in sources:
        fixture = json.loads((CORPUS / source["path"]).read_text())
        key = collect.__globals__["RECORD_KEYS"][fixture["table"]]
        # PostgreSQL jsonb readback does not preserve fixture insertion order.
        fixture["records"] = [dict(reversed(list(row.items()))) for row in fixture["records"]]
        database_records[source["source_id"]] = fixture
        expected[source["source_id"]] = fixture["records"][0][key]
    candidates = collect(database_records)
    assert len(candidates) == 7
    assert all(
        candidate.row_id == expected[source["source_id"]] for source, candidate in candidates
    )
