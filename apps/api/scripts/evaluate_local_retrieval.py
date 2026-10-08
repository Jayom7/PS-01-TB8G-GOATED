from __future__ import annotations

import asyncio
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ps01_api.config import get_settings
from ps01_api.integrations import create_embedding
from ps01_api.rag import citation_from_row

ROOT = Path(__file__).resolve().parents[3]
CREDENTIALS = ROOT / ".local-demo-credentials.json"
CLI = ROOT / "node_modules" / ".bin" / "supabase"
DOCKER_BIN = "/Applications/Docker.app/Contents/Resources/bin"
TOP_K = 12
CASES = [
    {
        "name": "invoice amount in OCR",
        "role": "Finance Manager",
        "query": "What amount is shown on Acme's scanned invoice?",
        "expected": {"ACM-INV-2048-SCAN"},
    },
    {
        "name": "contract payment terms",
        "role": "Sales Manager",
        "query": "What payment terms are specified in Acme's contract?",
        "expected": {"ACM-MSA-2026-07"},
    },
    {
        "name": "exact invoice identifier",
        "role": "Finance Manager",
        "query": "Find invoice ACM-INV-2048 and report its due date.",
        "expected": {"ACM-INV-2048-SCAN", "nova-finance-records"},
    },
    {
        "name": "structured finance record",
        "role": "Finance Manager",
        "query": "What is the recorded payment status for invoice ACM-INV-2048?",
        "expected": {"nova-finance-records"},
    },
    {
        "name": "HR cannot retrieve finance source",
        "role": "HR Manager",
        "query": "What amount is shown on Acme's scanned invoice?",
        "expected": set(),
        "forbidden": {"ACM-INV-2048-SCAN", "nova-finance-records"},
    },
]


def local_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{DOCKER_BIN}:{env.get('PATH', '')}"
    result = subprocess.run(
        [str(CLI), "status", "-o", "env"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Local Supabase is not running.")
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator:
            parts = shlex.split(value)
            if parts:
                values[name] = parts[0]
    if urlparse(values["API_URL"]).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Refusing to evaluate a non-local Supabase URL.")
    return values


async def run() -> dict[str, object]:
    local = local_environment()
    credentials = json.loads(CREDENTIALS.read_text())
    base_url = local["API_URL"].rstrip("/")
    api_key = local["PUBLISHABLE_KEY"]
    settings = get_settings()
    results: list[dict[str, object]] = []
    retrieved_rows: list[dict[str, object]] = []
    async with httpx.AsyncClient(timeout=35.0) as client:
        tokens: dict[str, str] = {}
        for role in {case["role"] for case in CASES}:
            login = await client.post(
                f"{base_url}/auth/v1/token?grant_type=password",
                headers={"apikey": api_key},
                json={
                    "email": credentials[role]["email"],
                    "password": credentials[role]["password"],
                },
            )
            login.raise_for_status()
            tokens[role] = login.json()["access_token"]

        for case in CASES:
            started = time.perf_counter()
            embedding = await create_embedding(client, settings, case["query"])
            response = await client.post(
                f"{base_url}/rest/v1/rpc/match_knowledge_chunks",
                headers={
                    "apikey": api_key,
                    "Authorization": f"Bearer {tokens[case['role']]}",
                    "Content-Type": "application/json",
                },
                json={
                    "query_embedding": embedding,
                    "query_text": case["query"],
                    "match_count": TOP_K,
                },
            )
            response.raise_for_status()
            rows = response.json()
            retrieved_rows.extend(rows)
            found = [str(row["source_id"]) for row in rows]
            expected = case["expected"]
            relevant_ranks = [index for index, source in enumerate(found, 1) if source in expected]
            forbidden = case.get("forbidden", set())
            forbidden_hits = sorted(set(found) & forbidden)
            results.append(
                {
                    "name": case["name"],
                    "role": case["role"],
                    "top_k": TOP_K,
                    "hit": bool(relevant_ranks) if expected else not forbidden_hits,
                    "reciprocal_rank": 1 / relevant_ranks[0] if relevant_ranks else 0.0,
                    "authorized_rows": len(rows),
                    "source_types_found": sorted(
                        {str(row.get("source_type")) for row in rows if row.get("source_type")}
                    ),
                    "forbidden_source_hits": forbidden_hits,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )

        finance_key = local["PUBLISHABLE_KEY"]
        hr_headers = {
            "apikey": finance_key,
            "Authorization": f"Bearer {tokens['HR Manager']}",
        }
        unauthorized_chunks = await client.get(
            f"{base_url}/rest/v1/knowledge_chunks",
            headers=hr_headers,
            params={
                "select": "id,source_name,metadata,content",
                "source_id": "eq.ACM-INV-2048-SCAN",
            },
        )
        unauthorized_chunks.raise_for_status()
        chunk_leaks = len(unauthorized_chunks.json())
        unauthorized_documents = await client.get(
            f"{base_url}/rest/v1/documents",
            headers=hr_headers,
            params={
                "select": "id,source_name,metadata",
                "source_name": "eq.acme-invoice-ACM-INV-2048.png",
            },
        )
        unauthorized_documents.raise_for_status()
        document_leaks = len(unauthorized_documents.json())
        results.append(
            {
                "name": "HR direct table and metadata access",
                "role": "HR Manager",
                "hit": chunk_leaks == 0 and document_leaks == 0,
                "unauthorized_chunk_rows": chunk_leaks,
                "unauthorized_document_rows": document_leaks,
                "forbidden_source_hits": [],
            }
        )

    return summarize_results(results, retrieved_rows)


def summarize_results(results: list[dict], retrieved_rows: list[dict]) -> dict[str, object]:
    positive = [row for row, case in zip(results, CASES, strict=False) if case.get("expected")]
    cited = [citation_from_row(row) for row in retrieved_rows]
    citation_checks = [bool(item.get("citation_id") and item.get("location")) for item in cited]
    invoice_modalities = set(results[0].get("source_types_found", []))
    structured_result = results[3]
    latency_values = [
        float(row["latency_ms"])
        for row in results
        if isinstance(row.get("latency_ms"), (int, float))
    ]
    return {
        "schema_version": 2,
        "scope": "local-synthetic-retrieval",
        "dataset": "novacore-synthetic-v1",
        "top_k": TOP_K,
        "query_count": len(CASES),
        "positive_query_count": len(positive),
        "retrieval_hit_rate_at_k": round(
            sum(bool(row["hit"]) for row in positive) / len(positive), 3
        ),
        "mean_reciprocal_rank": round(
            sum(float(row["reciprocal_rank"]) for row in positive) / len(positive), 3
        ),
        "authorization_violations": sum(len(row["forbidden_source_hits"]) for row in results)
        + sum(
            int(row.get("unauthorized_chunk_rows", 0))
            + int(row.get("unauthorized_document_rows", 0))
            for row in results
        ),
        "measured_checks": {
            "ocr_retrieval": "image_ocr" in invoice_modalities,
            "structured_record_retrieval": bool(structured_result["hit"]),
            "cross_modal_retrieval": {"image_ocr", "structured"}.issubset(invoice_modalities),
            "retrieved_citation_locations_present": sum(citation_checks),
            "retrieved_citation_locations_checked": len(citation_checks),
            "mean_latency_ms": round(sum(latency_values) / len(latency_values), 1)
            if latency_values
            else None,
        },
        "metric_definitions": {
            "retrieval_hit_rate_at_k": (
                "Fraction of positive queries with any expected source in top k; not recall."
            ),
            "mean_reciprocal_rank": (
                "Mean reciprocal rank of the first expected source over positive queries."
            ),
            "retrieved_citation_locations_present": (
                "Retrieved rows with nonempty citation ID and location; "
                "not answer provenance or entailment."
            ),
            "authorization_violations": (
                "Forbidden-source hits in these cases plus the direct HR table checks; "
                "not a global security count."
            ),
        },
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run()), indent=2))
