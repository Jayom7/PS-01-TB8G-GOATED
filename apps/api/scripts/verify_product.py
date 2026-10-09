"""Read-only live product checks for fresh synthetic browser uploads.

No generation fixtures, hosted access, reseed or destructive cleanup. Run after
browser uploads and before removing the disposable sources through Sources.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from seed_local_demo import local_supabase_environment

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-assets", action="store_true")
    parser.add_argument("--verify-deletion", action="store_true")
    args = parser.parse_args()
    if args.prepare_assets:
        import fitz

        directory = ROOT / "data/local/acceptance-assets"
        directory.mkdir(parents=True, exist_ok=True)
        with fitz.open() as pdf:
            page = pdf.new_page()
            page.insert_text(
                (72, 72),
                "SYNTHETIC Clearframe acceptance CF-FRESH-1009\nAcme CF-INV-1009\n"
                "Invoice total USD 1,234.00. Payment terms Net 15.",
            )
            pdf.save(directory / "fresh-acceptance.pdf")
            page.get_pixmap(matrix=fitz.Matrix(2, 2)).save(directory / "fresh-acceptance.png")
        print("Prepared disposable PDF and image under data/local/acceptance-assets")
        return 0
    local = local_supabase_environment()
    credentials = json.loads((ROOT / ".local-demo-credentials.json").read_text())
    checks = []

    def check(name, passed):
        checks.append({"name": name, "status": "PASS" if passed else "FAIL"})
        print(f"{'PASS' if passed else 'FAIL'}: {name}")

    with httpx.Client(timeout=40) as client:
        tokens = {}
        for role in ("CEO", "HR Manager"):
            login = client.post(
                local["API_URL"] + "/auth/v1/token?grant_type=password",
                headers={"apikey": local["PUBLISHABLE_KEY"]},
                json=credentials[role],
            )
            login.raise_for_status()
            tokens[role] = login.json()["access_token"]
        ceo = {"Authorization": "Bearer " + tokens["CEO"]}
        hr = {"Authorization": "Bearer " + tokens["HR Manager"]}
        rest = ceo | {"apikey": local["PUBLISHABLE_KEY"]}
        api = "http://127.0.0.1:8000/api/v1"
        sources = client.get(api + "/sources", headers=ceo).json()["sources"]
        if args.verify_deletion:
            output = ROOT / "data/local/product-verification.json"
            report = json.loads(output.read_text())
            ids = report["fresh_source_ids"]
            if len(ids) != 3:
                raise RuntimeError("Expected three previously verified disposable source IDs")
            vector = client.get(
                local["API_URL"] + "/rest/v1/knowledge_chunks",
                headers=rest,
                params={"select": "embedding", "limit": "1"},
            ).json()[0]["embedding"]
            vector = json.loads(vector) if isinstance(vector, str) else vector
            found = client.post(
                local["API_URL"] + "/rest/v1/rpc/match_knowledge_chunks",
                headers=rest,
                json={"query_embedding": vector, "query_text": "CF-INV-1009", "match_count": 12},
            ).json()
            for source_id in ids:
                for table, column in (
                    ("documents", "id"),
                    ("knowledge_chunks", "document_id"),
                    ("access_grants", "document_id"),
                ):
                    rows = client.get(
                        local["API_URL"] + "/rest/v1/" + table,
                        headers=rest,
                        params={column: "eq." + source_id},
                    ).json()
                    check(table + ": deleted source absent", rows == [])
                check(
                    "Deleted source absent from live retrieval",
                    all(r["document_id"] != source_id for r in found),
                )
                for suffix in ("preview", "original"):
                    check(
                        "Deleted " + suffix + " denied",
                        client.get(
                            api + "/sources/" + source_id + "/" + suffix, headers=ceo
                        ).status_code
                        == 404,
                    )
                job = client.get(
                    local["API_URL"] + "/rest/v1/source_cleanup_jobs",
                    headers={
                        "apikey": local["SERVICE_ROLE_KEY"],
                        "Authorization": "Bearer " + local["SERVICE_ROLE_KEY"],
                    },
                    params={"source_id": "eq." + source_id},
                ).json()
                check(
                    "Durable original cleanup complete",
                    len(job) == 1
                    and job[0]["state"] == "complete"
                    and (
                        not job[0].get("storage_path")
                        or not (ROOT / job[0]["storage_path"]).exists()
                    ),
                )
            rows = client.get(
                local["API_URL"] + "/rest/v1/invoices",
                headers=rest,
                params={"invoice_id": "eq.CF-INV-1009"},
            ).json()
            check("Disposable typed invoice removed", rows == [])
            report["deletion_checks"] = checks
            report["deletion_checked_at"] = datetime.now(UTC).isoformat()
            output.write_text(json.dumps(report, indent=2) + "\n")
            return 0 if all(c["status"] == "PASS" for c in checks) else 1
        fresh = [
            s
            for s in sources
            if s["source_name"]
            in {"fresh-acceptance.pdf", "fresh-acceptance.png", "Disposable invoice CF-INV-1009"}
        ]
        check("Three fresh browser-ingested sources visible", len(fresh) == 3)
        for source in fresh:
            rows = client.get(
                local["API_URL"] + "/rest/v1/knowledge_chunks",
                headers=rest,
                params={"document_id": "eq." + source["id"], "select": "*"},
            ).json()
            check(
                source["source_type"] + ": persisted nonempty vectors",
                bool(rows) and all(r.get("embedding") for r in rows),
            )
            row = rows[0]
            vector = (
                json.loads(row["embedding"])
                if isinstance(row["embedding"], str)
                else row["embedding"]
            )
            found = client.post(
                local["API_URL"] + "/rest/v1/rpc/match_knowledge_chunks",
                headers=rest,
                json={"query_embedding": vector, "query_text": "CF-INV-1009", "match_count": 12},
            ).json()
            check(
                source["source_type"] + ": real authorized RPC retrieval",
                any(r["document_id"] == source["id"] for r in found),
            )
            preview = client.get(api + f"/sources/{row['id']}", headers=ceo)
            check(
                source["source_type"] + ": exact canonical preview",
                preview.status_code == 200 and preview.json()["excerpt"] == row["content"],
            )
            if source["source_type"] == "image_ocr":
                check("Fresh real OCR coordinates present", all(r.get("ocr_region") for r in rows))
            if source["source_type"] == "pdf":
                original = client.get(api + f"/sources/{source['id']}/original?page=1", headers=ceo)
                check(
                    "Fresh PDF exact page image",
                    original.status_code == 200 and original.content.startswith(b"\x89PNG"),
                )
            for suffix in (row["id"], source["id"] + "/preview", source["id"] + "/original"):
                denied = client.get(api + "/sources/" + suffix, headers=hr)
                check(
                    source["source_type"] + ": HR protected lookup denied",
                    denied.status_code == 404 and "CF-INV" not in denied.text,
                )
            denied = client.delete(api + "/sources/" + source["id"], headers=hr)
            check(
                source["source_type"] + ": unauthorized deletion denied", denied.status_code == 403
            )
        records = client.get(
            local["API_URL"] + "/rest/v1/invoices",
            headers=rest,
            params={
                "invoice_id": "eq.CF-INV-1009",
                "select": "invoice_id,total_minor_units,payment_status",
            },
        ).json()
        check(
            "Fresh typed PostgreSQL invoice values",
            len(records) == 1 and records[0]["total_minor_units"] == 123400,
        )
        refused = client.post(
            api + "/chat/query",
            headers=hr,
            json={"query": "What amount is shown on Acme's scanned invoice?"},
        )
        body = refused.json()
        check(
            "HR same finance question safely refused without generation",
            refused.status_code == 200
            and body["state"] == "INSUFFICIENT_EVIDENCE"
            and body["trace"]["generation_model"] is None
            and body["trace"]["evidence_items_sent_to_model"] == 0,
        )
        history = client.get(api + "/conversations", headers=ceo).json()["conversations"]
        check(
            "Real saved conversation exists after restart",
            any(t["title"] == "hello" for t in history),
        )
        if history:
            foreign = client.get(api + "/conversations/" + history[0]["id"], headers=hr)
            check("Guessed other-user conversation denied", foreign.status_code == 404)
        security = client.get(api + "/security", headers=ceo).json()
        check("Durable security events available", bool(security["trace"]))
    report = {
        "completed_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "fresh_source_ids": [s["id"] for s in fresh],
        "generation": (
            "NOT RUN by this script; provider-dependent acceptance is reported separately"
        ),
    }
    output = ROOT / "data/local/product-verification.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if all(c["status"] == "PASS" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
