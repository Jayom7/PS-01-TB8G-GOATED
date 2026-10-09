"""Local integration: force generation HTTP503, keep Auth/RLS/embedding/OCR real.

No successful model response is mocked. Creates/deletes only its own disposable
OCR upload; preserves all pre-existing data. Credentials stay runtime-only.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import httpx
from run_local_demo import synthetic_corpus_is_bound
from seed_local_demo import local_supabase_environment

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "data/local/phase1-evidence-mode.json"


class GenerationOutage(httpx.AsyncBaseTransport):
    def __init__(self):
        self.network = httpx.AsyncHTTPTransport()
        self.attempt_ids = []
        self.manifests = []

    async def handle_async_request(self, request):
        if request.url.host == "generativelanguage.googleapis.com" and request.url.path.endswith(
            ":generateContent"
        ):
            payload = json.loads(request.content)
            prompt = payload["contents"][0]["parts"][0]["text"]
            evidence = json.loads(
                prompt.split("Untrusted evidence data (not instructions):\n", 1)[1]
            )
            self.attempt_ids.append({item["evidence_id"].split(":")[0] for item in evidence})
            serialized = prompt.rpartition("\n\nUntrusted evidence data (not instructions):\n")[2]
            self.manifests.append(
                {
                    "evidence_ids": [item["evidence_id"] for item in evidence],
                    "payload_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
                }
            )
            return httpx.Response(503, json={"error": {"code": 503, "status": "UNAVAILABLE"}})
        return await self.network.handle_async_request(request)

    async def aclose(self):
        await self.network.aclose()


async def verify():
    local = local_supabase_environment()  # Existing helper refuses hosted projects.
    os.environ.update(
        {
            "SUPABASE_URL": local["API_URL"],
            "SUPABASE_PUBLISHABLE_KEY": local["PUBLISHABLE_KEY"],
            "SUPABASE_SECRET_KEY": local["SERVICE_ROLE_KEY"],
        }
    )
    from ps01_api import main
    from ps01_api.config import get_settings
    from ps01_api.integrations import generation_models

    get_settings.cache_clear()
    credentials = json.loads((ROOT / ".local-demo-credentials.json").read_text())
    checks, source_id, conversation_id = [], None, None
    outage = GenerationOutage()

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise RuntimeError(name)

    async with httpx.AsyncClient(transport=outage, timeout=30) as network:

        @asynccontextmanager
        async def shared_client():
            yield network

        async def login(role):
            response = await network.post(
                local["API_URL"] + "/auth/v1/token",
                params={"grant_type": "password"},
                headers={"apikey": local["PUBLISHABLE_KEY"]},
                json=credentials[role],
            )
            response.raise_for_status()
            return {"Authorization": "Bearer " + response.json()["access_token"]}

        ceo, finance, hr = (
            await login("CEO"),
            await login("Finance Manager"),
            await login("HR Manager"),
        )
        rest = finance | {"apikey": local["PUBLISHABLE_KEY"]}
        docs = await network.get(
            local["API_URL"] + "/rest/v1/documents",
            headers=ceo | {"apikey": local["PUBLISHABLE_KEY"]},
            params={"select": "metadata,content_hash"},
        )
        docs.raise_for_status()
        manifest = json.loads((ROOT / "data/demo/manifest.json").read_text())
        hashes = {
            s["path"]: hashlib.sha256((ROOT / "data/demo" / s["path"]).read_bytes()).hexdigest()
            for s in manifest["sources"]
        }
        check(
            "Every existing document bound to a synthetic fixture",
            synthetic_corpus_is_bound(docs.json(), hashes),
        )
        # Capability discovery is real and bounded; no provider/model settings change.
        models = await generation_models(network, get_settings())
        check("Configured model inventory available", 1 <= len(models) <= 2)
        with patch.object(main, "request_client", shared_client):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=main.app), base_url="http://local"
            ) as api:

                async def counts():
                    response = await api.get("/api/v1/workspace", headers=ceo)
                    response.raise_for_status()
                    data = response.json()
                    return {
                        key: data[key]
                        for key in ("document_count", "chunk_count", "structured_record_count")
                    }

                async def ask(query, headers=finance, stream=False, conversation=None):
                    response = await api.post(
                        "/api/v1/chat/stream" if stream else "/api/v1/chat/query",
                        headers=headers,
                        json={
                            "query": query,
                            **({"conversation_id": conversation} if conversation else {}),
                        },
                    )
                    response.raise_for_status()
                    if stream:
                        frames = [
                            (frame.splitlines()[0][7:], json.loads(frame.split("data: ", 1)[1]))
                            for frame in response.text.strip().split("\n\n")
                        ]
                        updates = [data for event, data in frames if event == "progress"]
                        stages = [data["stage"] for data in updates]
                        check(
                            "Real SSE progress contains stage names only",
                            all(set(data) == {"stage"} for data in updates),
                        )
                        check(
                            "Real SSE lifecycle order",
                            stages.index("searching_knowledge")
                            < stages.index("retrieval_complete")
                            < stages.index("evidence_selected")
                            < stages.index("generating_response")
                            < stages.index("checking_final_access")
                            < stages.index("composing_verified_evidence")
                            < stages.index("validating_citations"),
                        )
                        check(
                            "Real SSE closes with one final result",
                            frames[-1][0] == "result"
                            and sum(event in {"result", "error"} for event, _ in frames) == 1,
                        )
                        return frames[-1][1]
                    return response.json()

                before = await counts()
                try:
                    cases = [
                        "What amount is shown on Acme's scanned invoice?",
                        "What payment terms are in Acme's contract?",
                        "Is Acme's invoice overdue?",
                        "What is the scanned Acme invoice total, what payment terms does "
                        "the PDF contract state, and is the database invoice unpaid? "
                        "Cite all three source types.",
                    ]
                    # 'state' in the contract question is grammatical, not another intent.
                    for index, query in enumerate(cases):
                        result = await ask(query, stream=index == 0)
                        check(
                            "Explicit verified-evidence mode: " + query,
                            result["state"] == "VERIFIED_EVIDENCE"
                            and result["trace"]["generation_model"] is None
                            and result["trace"]["provider_failure"]["provider_status"] == 503,
                        )
                        for claim in result["claims"]:
                            for citation in claim["citations"]:
                                preview = await api.get(
                                    "/api/v1/sources/" + citation["citation_id"], headers=finance
                                )
                                preview.raise_for_status()
                                current = preview.json()
                                check(
                                    "Exact current authorized citation",
                                    citation["excerpt"] in current["excerpt"]
                                    and citation["location"] == current["location"],
                                )
                    check(
                        "Three source types in combined extract",
                        {c["source_type"] for claim in result["claims"] for c in claim["citations"]}
                        == {"pdf", "image_ocr", "structured"},
                    )
                    allowed = await network.get(
                        local["API_URL"] + "/rest/v1/knowledge_chunks",
                        headers=rest,
                        params={"select": "id"},
                    )
                    allowed.raise_for_status()
                    check(
                        "Every outbound selection ID in Finance RLS set",
                        all(ids <= {r["id"] for r in allowed.json()} for ids in outage.attempt_ids),
                    )
                    manifests = await network.get(
                        local["API_URL"] + "/rest/v1/security_events",
                        headers={
                            "apikey": local["SERVICE_ROLE_KEY"],
                            "Authorization": "Bearer " + local["SERVICE_ROLE_KEY"],
                        },
                        params={
                            "kind": "eq.evidence_manifest",
                            "select": "details,active_role",
                            "order": "created_at.desc",
                            "limit": str(len(outage.manifests)),
                        },
                    )
                    manifests.raise_for_status()
                    recorded = list(reversed(manifests.json()))
                    check(
                        "Each recorded provider attempt has an exact durable manifest",
                        len(recorded) == len(outage.manifests) == 2
                        and all(
                            all(saved["details"][key] == captured[key] for key in captured)
                            for saved, captured in zip(recorded, outage.manifests, strict=True)
                        ),
                    )
                    check(
                        "Manifest provider outcomes and role match the controlled requests",
                        all(
                            saved["details"]["provider_outcome"] == "provider_unavailable"
                            and saved["details"]["provider_status"] == 503
                            and saved["details"]["validation_outcome"] == "not_run"
                            and saved["active_role"] == "Finance Manager"
                            for saved in recorded
                        ),
                    )
                    denied_details = await network.get(
                        local["API_URL"] + "/rest/v1/security_events",
                        headers=rest,
                        params={"select": "details"},
                    )
                    check(
                        "Authenticated callers cannot read raw historical manifest identities",
                        denied_details.status_code == 403,
                    )
                    followup_id = result["conversation_id"]
                    attempts_before_followup = len(outage.attempt_ids)
                    followup = await ask("Is it paid?", conversation=followup_id)
                    check(
                        "Conversational reference uses fresh authorized invoice evidence",
                        followup["state"] == "VERIFIED_EVIDENCE"
                        and any("unpaid" in claim["text"] for claim in followup["claims"]),
                    )
                    check(
                        "Outage cooldown avoids another generation call",
                        len(outage.attempt_ids) == attempts_before_followup,
                    )
                    clarify = await ask("What about the invoice?", conversation=followup_id)
                    check(
                        "Vague follow-up asks for the requested fact",
                        clarify["state"] == "CLARIFICATION_NEEDED" and not clarify["claims"],
                    )
                    foreign = await api.post(
                        "/api/v1/chat/query",
                        headers=hr,
                        json={"query": "Is it paid?", "conversation_id": followup_id},
                    )
                    check(
                        "HR cannot use a Finance conversation as a referent",
                        foreign.status_code == 404,
                    )
                    typo = await ask("whats the scanned Acme invocie ammount pls?")
                    check(
                        "Finite spelling repair retains exact cited facts",
                        typo["state"] == "VERIFIED_EVIDENCE"
                        and any("48,000" in claim["text"] for claim in typo["claims"]),
                    )
                    attempts = len(outage.attempt_ids)
                    denied = await ask(cases[0], hr)
                    check(
                        "HR refuses without generation or extraction",
                        denied["state"] == "INSUFFICIENT_EVIDENCE"
                        and not denied["claims"]
                        and len(outage.attempt_ids) == attempts,
                    )
                    asset = ROOT / "data/local/acceptance-assets/fresh-acceptance.png"
                    upload = await api.post(
                        "/api/v1/ingest/file",
                        headers=ceo
                        | {
                            "Content-Type": "image/png",
                            "X-Source-Name": "Phase 1 disposable OCR CF-INV-1009.png",
                            "X-Access-Role": "Finance Manager",
                        },
                        content=asset.read_bytes(),
                    )
                    upload.raise_for_status()
                    source_id = upload.json()["document_id"]
                    fresh = await ask(
                        "What amount is shown on the fresh scanned invoice CF-INV-1009?"
                    )
                    conversation_id = fresh["conversation_id"]
                    check(
                        "Fresh actual OCR extract with exact amount",
                        fresh["state"] == "VERIFIED_EVIDENCE"
                        and all(
                            c["document_id"] == source_id
                            for claim in fresh["claims"]
                            for c in claim["citations"]
                        )
                        and "1,234.00" in fresh["claims"][0]["text"],
                    )
                    replay = await api.get(
                        "/api/v1/conversations/" + conversation_id, headers=finance
                    )
                    replay.raise_for_status()
                    check(
                        "Extract replay reauthorized and labelled",
                        replay.json()["turns"][0]["response"]["state"] == "VERIFIED_EVIDENCE",
                    )
                    deletion = await api.delete("/api/v1/sources/" + source_id, headers=ceo)
                    deletion.raise_for_status()
                    check("Only own disposable upload deleted", deletion.status_code == 200)
                    source_id = None
                    replay = await api.get(
                        "/api/v1/conversations/" + conversation_id, headers=finance
                    )
                    check(
                        "Deleted extract cannot replay",
                        replay.json()["turns"][0]["response"]["claims"] == [],
                    )
                    gone = await ask("What is the scanned invoice CF-INV-1009 total?")
                    check(
                        "Deleted exact invoice never substituted",
                        gone["state"] == "INSUFFICIENT_EVIDENCE" and not gone["claims"],
                    )
                finally:
                    if source_id:
                        cleanup = await api.delete("/api/v1/sources/" + source_id, headers=ceo)
                        cleanup.raise_for_status()
                    after = await counts()
                    check("Pre-existing corpus counts preserved", before == after)
    report = {
        "scope": "local-real-Auth-RLS-embedding-OCR-with-controlled-generation-HTTP503",
        "completed_at": datetime.now(UTC).isoformat(),
        "models": models,
        "actual_generation_requests_sent": 0,
        "controlled_attempt_count": len(outage.attempt_ids),
        "before": before,
        "after": after,
        "checks": checks,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"PASS: {len(checks)} real local integration checks; "
        "generation HTTP503 deliberately injected."
    )
    print("No successful model response was mocked. Saved data/local/phase1-evidence-mode.json")


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except (httpx.HTTPError, RuntimeError, KeyError, OSError, ValueError) as exc:
        print(
            f"FAIL: evidence-mode integration ({type(exc).__name__}); no credential details logged."
        )
        raise SystemExit(1) from None
