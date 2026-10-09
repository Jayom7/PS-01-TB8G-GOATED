from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from seed_local_demo import local_supabase_environment

ROOT = Path(__file__).resolve().parents[3]
ROLES = ("CEO", "Finance Manager", "HR Manager", "Sales Manager", "Engineer")
TARGETS = (
    "ACM-INV-2048-SCAN",
    "ACM-INV-2048-SCAN",
    "EMP-020-SIGNED",
    "ACM-MSA-2026-07",
    "nova-engineering-records",
)
REPORT = ROOT / "data/local/security-verification.json"


def synthetic_corpus_is_bound(documents, fixture_hashes):
    # Deletion may leave a strict subset. Verify every remaining document;
    # never restore deleted data or allow unknown/duplicate uploads.
    paths = [(doc.get("metadata") or {}).get("local_demo_path") for doc in documents]
    return (
        bool(documents)
        and len(paths) == len(set(paths))
        and all(
            (doc.get("metadata") or {}).get("synthetic") is True
            and path in fixture_hashes
            and doc.get("content_hash") == fixture_hashes[path]
            for doc, path in zip(documents, paths, strict=True)
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the running local checkout without reseeding."
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--skip-generation", action="store_true")
    args = parser.parse_args()
    if urlparse(args.api_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("This suite refuses hosted API URLs.")
    checks, inspected = [], []

    def record(name, passed, detail=""):
        status = "passed" if passed else "failed"
        checks.append({"name": name, "status": status, "detail": detail})
        print(f"{status.upper()}: {name}", flush=True)

    def blocked(name, detail):
        checks.append({"name": name, "status": "blocked", "detail": detail})
        print(f"BLOCKED: {name} ({detail})", flush=True)

    try:
        local = local_supabase_environment()
        credentials = json.loads((ROOT / ".local-demo-credentials.json").read_text())
        manifest = json.loads((ROOT / "data/demo/manifest.json").read_text())
        base, api = local["API_URL"].rstrip("/"), args.api_url.rstrip("/")
        with httpx.Client(timeout=70.0) as client:
            tokens, identities, rows_by_role = {}, {}, {}
            for role in ROLES:
                login = client.post(
                    f"{base}/auth/v1/token",
                    params={"grant_type": "password"},
                    headers={"apikey": local["PUBLISHABLE_KEY"]},
                    json=credentials[role],
                )
                login.raise_for_status()
                tokens[role] = login.json()["access_token"]
                identities[role] = login.json()["user"]["id"]

            def headers(role, context=None):
                result = {"Authorization": f"Bearer {tokens[role]}"}
                if context:
                    result["X-Demo-Role"] = context
                return result

            def get(path, role, context=None):
                response = client.get(f"{api}{path}", headers=headers(role, context))
                response.raise_for_status()
                return response.json()

            record(
                "Unauthenticated workspace denied",
                client.get(f"{api}/api/v1/workspace").status_code == 401,
            )
            for role, target in zip(ROLES, TARGETS, strict=True):
                rest_headers = headers(role) | {"apikey": local["PUBLISHABLE_KEY"]}
                response = client.get(
                    f"{base}/rest/v1/knowledge_chunks",
                    headers=rest_headers,
                    params={
                        "select": "id,document_id,source_id,content,embedding",
                        "limit": "1000",
                    },
                )
                response.raise_for_status()
                rows = rows_by_role[role] = response.json()
                expected = {
                    s["source_id"] for s in manifest["sources"] if role in s["allowed_roles"]
                }
                record(
                    f"{role}: complete manifest allow/deny boundary",
                    {row["source_id"] for row in rows} == expected,
                )
                record(
                    f"{role}: API sources match RLS-visible documents",
                    {s["id"] for s in get("/api/v1/sources", role)["sources"]}
                    == {row["document_id"] for row in rows},
                )
                chosen = next(row for row in rows if row["source_id"] == target)
                vector = chosen["embedding"]
                if isinstance(vector, str):
                    vector = json.loads(vector)
                retrieval = client.post(
                    f"{base}/rest/v1/rpc/match_knowledge_chunks",
                    headers=rest_headers,
                    json={
                        "query_embedding": vector,
                        "query_text": chosen["content"],
                        "match_count": 12,
                    },
                )
                retrieval.raise_for_status()
                found = retrieval.json()
                record(
                    f"{role}: stored-vector authorized retrieval",
                    any(row["source_id"] == target for row in found)
                    and all(row["source_id"] in expected for row in found),
                    "Real local RPC using an authorized stored embedding; no provider call.",
                )
                preview = client.get(f"{api}/api/v1/sources/{chosen['id']}", headers=headers(role))
                record(f"{role}: authorized citation lookup", preview.status_code == 200)
                if role != "CEO":
                    foreign = next(
                        row for row in rows_by_role["CEO"] if row["source_id"] not in expected
                    )
                    for kind, path in [
                        ("citation", foreign["id"]),
                        ("document", f"{foreign['document_id']}/preview"),
                        ("original", f"{foreign['document_id']}/original"),
                        ("rendered page", f"{foreign['document_id']}/original?page=1"),
                    ]:
                        hidden = client.get(f"{api}/api/v1/sources/{path}", headers=headers(role))
                        record(f"{role}: forbidden {kind} lookup", hidden.status_code == 404)
                    forged = client.get(f"{api}/api/v1/workspace", headers=headers(role, "CEO"))
                    record(f"{role}: forged CEO context denied", forged.status_code == 403)
                switch = client.post(
                    f"{api}/api/v1/demo/switch", headers=headers("CEO"), json={"role": role}
                )
                switch.raise_for_status()
                workspace = get("/api/v1/workspace", "CEO", role)
                record(
                    f"CEO identity preserved in {role} context",
                    switch.json()["active_role"] == role
                    and workspace["identity"]["user_id"] == identities["CEO"]
                    and workspace["identity"]["role"] == "CEO"
                    and workspace["active_role"] == role
                    and {s["id"] for s in workspace["documents"]}
                    == {row["document_id"] for row in rows},
                )
            labels = get("/api/v1/security", "CEO")["security_tests"]
            record(
                "Security labels unmeasured facts honestly",
                labels["unauthorized_evidence_to_model"]
                == "not independently measured in this trace"
                and labels["database_row_level_security"]
                == "configured; status not checked by this endpoint",
            )
            forged = client.post(
                f"{api}/api/v1/chat/query",
                headers=headers("Finance Manager"),
                json={"query": "invoice", "role": "CEO", "evidence": []},
            )
            record("Client-supplied identity/evidence rejected", forged.status_code == 422)
            forged_org = client.post(
                f"{api}/api/v1/chat/query",
                headers=headers("HR Manager"),
                json={"query": "invoice", "organization_id": "foreign-org"},
            )
            record("Client-supplied organization rejected", forged_org.status_code == 422)
            finance_rest = headers("Finance Manager") | {"apikey": local["PUBLISHABLE_KEY"]}
            history = client.get(
                f"{base}/rest/v1/query_history",
                headers=finance_rest,
                params={"select": "conversation_id", "limit": "1"},
            )
            history.raise_for_status()
            if history.json():
                foreign_id = history.json()[0]["conversation_id"]
                foreign = client.get(
                    f"{api}/api/v1/conversations/{foreign_id}", headers=headers("HR Manager")
                )
                record("Foreign Finance conversation denied to HR", foreign.status_code == 404)
            else:
                blocked(
                    "Foreign Finance conversation denied to HR", "No saved Finance conversation"
                )
            vector = rows_by_role["Finance Manager"][0]["embedding"]
            if isinstance(vector, str):
                vector = json.loads(vector)
            for role, query, label in [
                (
                    "Finance Manager",
                    "invoice ACM-INV-999999 total",
                    "Exact nonexistent ID never substitutes another invoice",
                ),
                (
                    "HR Manager",
                    "invoice ACM-INV-2048 total",
                    "HR exact Finance identifier returns no evidence",
                ),
            ]:
                result = client.post(
                    f"{base}/rest/v1/rpc/match_knowledge_chunks",
                    headers=headers(role) | {"apikey": local["PUBLISHABLE_KEY"]},
                    json={"query_embedding": vector, "query_text": query, "match_count": 12},
                )
                result.raise_for_status()
                record(label, result.json() == [])
            # Existing deletion tombstones only; never delete a demo source to test.
            deleted = client.get(
                f"{base}/rest/v1/source_cleanup_jobs",
                headers={
                    "apikey": local["SERVICE_ROLE_KEY"],
                    "Authorization": "Bearer " + local["SERVICE_ROLE_KEY"],
                },
                params={"select": "source_id", "limit": "1"},
            )
            deleted.raise_for_status()
            if deleted.json():
                deleted_id = deleted.json()[0]["source_id"]
                for suffix in ("", "/original", "/original?page=1"):
                    result = client.get(
                        f"{api}/api/v1/sources/{deleted_id}{suffix}", headers=headers("CEO")
                    )
                    record("Deleted source lookup denied" + suffix, result.status_code == 404)
            else:
                blocked("Deleted source lookup denied", "No deletion tombstone available")
            contract = next(
                row for row in rows_by_role["CEO"] if row["source_id"] == "ACM-MSA-2026-07"
            )
            pdf_page = client.get(
                f"{api}/api/v1/sources/{contract['document_id']}/original?page=1",
                headers=headers("CEO"),
            )
            record(
                "Authorized exact PDF page renders without a browser PDF plugin",
                pdf_page.status_code == 200
                and pdf_page.headers.get("content-type") == "image/png"
                and pdf_page.content.startswith(b"\x89PNG\r\n\x1a\n")
                and pdf_page.headers.get("cache-control") == "no-store",
            )
            # The live provider check is authorized for this fictional corpus,
            # not arbitrary uploads. Bind every visible document to its local
            # synthetic fixture before allowing any generation request.
            documents = client.get(
                f"{base}/rest/v1/documents",
                headers=headers("CEO") | {"apikey": local["PUBLISHABLE_KEY"]},
                params={"select": "id,metadata,content_hash", "limit": "1000"},
            )
            documents.raise_for_status()
            fixture_hashes = {
                source["path"]: hashlib.sha256(
                    (ROOT / "data/demo" / source["path"]).read_bytes()
                ).hexdigest()
                for source in manifest["sources"]
            }
            synthetic_only = synthetic_corpus_is_bound(documents.json(), fixture_hashes)
            record(
                "Provider context limited to file-hash-bound synthetic demo sources", synthetic_only
            )
            if not synthetic_only:
                blocked("Real Gemini answer/source inspection", "Synthetic corpus boundary failed.")
            elif args.skip_generation:
                blocked("Real Gemini answer/source inspection", "Explicitly skipped.")
            else:
                query = "What amount is shown on Acme's scanned invoice?"
                answer = client.post(
                    f"{api}/api/v1/chat/query",
                    headers=headers("CEO", "Finance Manager"),
                    json={"query": query},
                )
                if answer.status_code == 503:
                    failure = answer.json()
                    blocked(
                        "Real Gemini answer/source inspection",
                        str(failure.get("code", "service_unavailable")),
                    )
                    checks[-1]["timing_ms"] = failure.get("timing_ms")
                else:
                    answer.raise_for_status()
                    result = answer.json()
                    if result["state"] == "VERIFIED_EVIDENCE":
                        blocked(
                            "Real Gemini answer/source inspection",
                            str(result["trace"]["provider_failure"]["code"]),
                        )
                        record(
                            "Explicit generation-independent evidence response",
                            result["trace"]["generation_model"] is None and bool(result["claims"]),
                        )
                    else:
                        record(
                            "Real Gemini finance amount with validated citations",
                            result["state"]
                            in {"CITATION_VALIDATED", "PARTIALLY_CITATION_VALIDATED"}
                            and bool(result["trace"]["generation_model"])
                            and bool(result["claims"])
                            and any(
                                "48000" in c["text"].replace(",", "") for c in result["claims"]
                            ),
                        )
                    allowed = {row["id"] for row in rows_by_role["Finance Manager"]}
                    canonical = {
                        row["id"]: row["content"] for row in rows_by_role["Finance Manager"]
                    }
                    for claim in result["claims"]:
                        for citation in claim["citations"]:
                            preview = get(
                                f"/api/v1/sources/{citation['citation_id']}",
                                "CEO",
                                "Finance Manager",
                            )
                            record(
                                "Returned citation has authorized inspected evidence",
                                citation["citation_id"] in allowed
                                and bool(preview["excerpt"])
                                and citation["title"] == preview["title"]
                                and citation["location"] == preview["location"]
                                and preview["excerpt"] == canonical[citation["citation_id"]],
                            )
                            inspected.append(
                                {
                                    "claim": claim["text"],
                                    "citation": citation,
                                    "excerpt": preview["excerpt"],
                                }
                            )
                    record(
                        "Inspected evidence contains the returned USD 48,000 amount",
                        any(
                            "48000" in s["claim"].replace(",", "")
                            and "48000" in s["excerpt"].replace(",", "")
                            for s in inspected
                        ),
                    )
            # This refusal has no relevant authorized evidence and must not
            # depend on the unrelated finance provider request succeeding.
            denial = client.post(
                f"{api}/api/v1/chat/query",
                headers=headers("CEO", "HR Manager"),
                json={"query": "What amount is shown on Acme's scanned invoice?"},
            )
            if denial.status_code != 200:
                blocked("HR refusal", str(denial.json().get("code", "service_unavailable")))
            else:
                body = denial.json()
                record(
                    "HR refusal without evidence supplied to generation",
                    body["state"] == "INSUFFICIENT_EVIDENCE"
                    and body["claims"] == []
                    and body["trace"]["generation_model"] is None
                    and body["trace"]["evidence_items_sent_to_model"] == 0,
                )

    except (httpx.HTTPError, OSError, ValueError, RuntimeError, KeyError, StopIteration) as exc:
        blocked("Suite dependency or runtime", type(exc).__name__)
    failed = sum(c["status"] == "failed" for c in checks)
    unavailable = sum(c["status"] == "blocked" for c in checks)
    report = {
        "scope": "fresh-local-synthetic-security-verification",
        "completed_at": datetime.now(UTC).isoformat(),
        "checkout_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "tracked_diff_sha256": hashlib.sha256(
            subprocess.check_output(["git", "diff", "HEAD"], cwd=ROOT)
        ).hexdigest(),
        "state": "failed" if failed else "blocked" if unavailable else "passed",
        "checks": checks,
        "inspected_sources": inspected,
        "limitations": "No hosted verification, general entailment proof, or injection benchmark.",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if REPORT.is_file():
        previous = json.loads(REPORT.read_text())
        stamp = str(previous.get("completed_at", "unknown")).replace(":", "-")
        archive = REPORT.with_name(f"security-verification-{stamp}.json")
        archive.write_text(REPORT.read_text())
        archive.chmod(0o600)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    REPORT.chmod(0o600)
    print(f"Saved {REPORT.relative_to(ROOT)}: {report['state']}", flush=True)
    return 1 if failed else 2 if unavailable else 0


if __name__ == "__main__":
    raise SystemExit(main())
