from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from ps01_api.config import Settings
from ps01_api.integrations import create_document_embedding, create_embedding, generate_claims


def settings() -> Settings:
    return Settings(
        gemini_api_key=SecretStr("test-key"),
        gemini_chat_model="gemini-3.8-flash",
        gemini_embedding_model="gemini-embedding-2",
        embedding_dimensions=1536,
    )


async def captured_embedding(call, response_text: str) -> tuple[list[float], dict[str, object]]:
    payload: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        payload.update(json.loads(request.content))
        return httpx.Response(200, json={"embedding": {"values": [0.25] * 1536}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        embedding = await call(client, settings(), response_text)
    return embedding, payload


@pytest.mark.asyncio
async def test_query_embedding_uses_gemini_embedding_2_search_query_prefix() -> None:
    embedding, payload = await captured_embedding(
        lambda client, config, text: create_embedding(client, config, text),
        "What payment terms apply?",
    )

    assert len(embedding) == 1536
    content = payload["content"]
    assert isinstance(content, dict)
    assert content["parts"][0]["text"] == ("task: search result | query: What payment terms apply?")


@pytest.mark.asyncio
async def test_document_embedding_uses_title_and_text_structure() -> None:
    async def embed(client, config, text):
        return await create_document_embedding(client, config, "Acme contract", text)

    embedding, payload = await captured_embedding(embed, "Net 30 payment terms")

    assert len(embedding) == 1536
    content = payload["content"]
    assert isinstance(content, dict)
    assert content["parts"][0]["text"] == ("title: Acme contract | text: Net 30 payment terms")


@pytest.mark.asyncio
async def test_generation_falls_back_after_transient_primary_model_outage() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return inventory()
        model = request.url.path.split("/")[-1].split(":")[0]
        calls.append(model)
        if model == "gemini-3.8-flash":
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"claims":[]}'}]}}]},
        )

    config = settings()
    config.gemini_fallback_chat_model = "gemini-3.7-flash"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        output = await generate_claims(client, config, "Return no claims.")

    assert calls == ["gemini-3.8-flash", "gemini-3.7-flash"]
    assert output["claims"] == []
    assert output["_model"] == "gemini-3.7-flash"
    assert output["_fallback_used"] is True
    assert [attempt["provider_status"] for attempt in output["_attempts"]] == [503, 200]
    assert [attempt["code"] for attempt in output["_attempts"]] == [
        "provider_unavailable",
        "success",
    ]


@pytest.mark.asyncio
async def test_generation_falls_back_when_primary_model_times_out() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return inventory()
        model = request.url.path.split("/")[-1].split(":")[0]
        calls.append(model)
        if model == "gemini-3.8-flash":
            raise httpx.ReadTimeout("primary model timed out")
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"claims":[]}'}]}}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        output = await generate_claims(client, settings(), "Return no claims.")

    assert calls == ["gemini-3.8-flash", "gemini-3.7-flash"]
    assert output["_model"] == "gemini-3.7-flash"
    assert output["_fallback_used"] is True


@pytest.mark.asyncio
async def test_generation_reports_provider_outage_after_trying_configured_fallback() -> None:
    from ps01_api.integrations import IntegrationFailure

    async def handler(_request: httpx.Request) -> httpx.Response:
        if _request.method == "GET":
            return inventory()
        return httpx.Response(503)

    config = settings()
    config.gemini_fallback_chat_model = "gemini-3.7-flash"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as failure:
            await generate_claims(client, config, "Generate a grounded answer.")

    assert failure.value.code == "provider_unavailable"


@pytest.mark.asyncio
async def test_429_stops_without_fallback():
    from ps01_api.integrations import IntegrationFailure

    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        return httpx.Response(429)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as failure:
            await generate_claims(client, settings(), "Answer")
    assert failure.value.code == "provider_rate_limited"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_only_one_fallback_on_repeated_503():
    from ps01_api.integrations import IntegrationFailure

    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure):
            await generate_claims(client, settings(), "Answer")
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_malformed_output_is_not_blindly_retried():
    from ps01_api.integrations import IntegrationFailure

    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": "not JSON"}]}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as failure:
            await generate_claims(client, settings(), "Answer")
    assert failure.value.code == "provider_invalid_response"
    assert len(calls) == 1


def inventory():
    return httpx.Response(
        200,
        json={
            "models": [
                {"name": f"models/{m}", "supportedGenerationMethods": ["generateContent"]}
                for m in ["gemini-3.8-flash", "gemini-3.7-flash"]
            ]
        },
    )


@pytest.fixture(autouse=True)
def clear_inventory():
    from ps01_api.integrations import _GENERATION_CIRCUITS, _MODEL_INVENTORY

    _MODEL_INVENTORY.clear()
    _GENERATION_CIRCUITS.clear()


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "provider_authentication_failed"),
        (403, "provider_authentication_failed"),
        (400, "provider_invalid_request"),
    ],
)
async def test_terminal_provider_errors(status, code):
    from ps01_api.integrations import IntegrationFailure

    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        return httpx.Response(status)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as error:
            await generate_claims(client, settings(), "Question")
    assert error.value.code == code
    assert len(calls) == 1


async def test_model_scoped_quota_fallback_success_and_system_boundary():
    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        payload = json.loads(request.content)
        assert "Application policy" in payload["systemInstruction"]["parts"][0]["text"]
        assert payload["contents"][0]["parts"][0]["text"] == "Untrusted question"
        assert payload["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}
        if len(calls) == 1:
            return httpx.Response(
                429,
                json={
                    "error": {
                        "details": [
                            {"violations": [{"quotaDimensions": {"model": "gemini-3.8-flash"}}]},
                            {"retryDelay": "30s"},
                        ]
                    }
                },
            )
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": '{"claims":[]}'}]}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        output = await generate_claims(client, settings(), "Untrusted question")
    assert output["_fallback_used"]
    assert len(calls) == 2


async def test_all_model_quotas_exhausted_preserve_retry():
    from ps01_api.integrations import IntegrationFailure

    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        return httpx.Response(
            429,
            json={
                "error": {
                    "details": [
                        {"violations": [{"quotaDimensions": {"model": "current"}}]},
                        {"retryDelay": "100s"},
                    ]
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as error:
            await generate_claims(client, settings(), "Question")
    assert error.value.retry_after == 100
    assert error.value.code == "provider_rate_limited"
    assert len(calls) == 2


async def test_unsupported_inventory_never_generates():
    from ps01_api.integrations import IntegrationFailure

    async def handler(request):
        assert request.method == "GET"
        return httpx.Response(200, json={"models": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as error:
            await generate_claims(client, settings(), "Question")
    assert error.value.code == "provider_invalid_model"


async def test_revocation_before_fallback_prevents_second_submission():
    from ps01_api.integrations import IntegrationFailure

    submissions, rechecks = [], []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        submissions.append(request.url.path)
        return httpx.Response(503)

    async def recheck():
        rechecks.append(True)
        if len(rechecks) > 1:
            raise IntegrationFailure("revoked", code="evidence_changed")
        return "Current evidence only"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as error:
            await generate_claims(client, settings(), "old snapshot", before_attempt=recheck)
    assert error.value.code == "evidence_changed"
    assert len(submissions) == 1


async def test_total_budget_includes_provider_wait():
    import asyncio

    from ps01_api.integrations import IntegrationFailure

    async def handler(request):
        if request.method == "GET":
            return inventory()
        await asyncio.sleep(2)
        return httpx.Response(503)

    config = settings()
    config.generation_budget_seconds = 1
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as error:
            await generate_claims(client, config, "Question")
    assert error.value.code == "provider_timeout"


async def test_safety_block_is_terminal():
    from ps01_api.integrations import IntegrationFailure

    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(True)
        return httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(IntegrationFailure) as error:
            await generate_claims(client, settings(), "Question")
    assert error.value.code == "provider_safety_block"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_inventory_excluded_primary_reports_actual_fallback():
    async def handler(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-3.7-flash",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                },
            )
        assert "gemini-3.7-flash:generateContent" in str(request.url)
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": '{"claims":[]}'}]}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        output = await generate_claims(client, settings(), "Answer")
    assert output["_fallback_used"] is True


@pytest.mark.parametrize("status", [408, 500, 502, 503, 504, 507])
async def test_transient_status_uses_only_one_configured_fallback(status):
    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        if len(calls) == 1:
            return httpx.Response(status, headers={"Retry-After": "46080"})
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": '{"claims":[]}'}]}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        output = await generate_claims(client, settings(), "Question")
    assert len(calls) == 2
    assert output["_model"] == "gemini-3.7-flash"
    first = output["_attempts"][0]
    assert first["provider_status"] == status
    assert first["code"] == ("provider_timeout" if status in {408, 504} else "provider_unavailable")


async def test_network_failure_uses_fallback():
    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(True)
        if len(calls) == 1:
            raise httpx.ConnectError("unavailable")
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": '{"claims":[]}'}]}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        output = await generate_claims(client, settings(), "Question")
    assert len(calls) == 2
    assert output["_attempts"][0]["code"] == "provider_unavailable"


async def test_cooldown_skips_repeated_outages_and_recovers_with_one_probe():
    import time

    from ps01_api.integrations import _GENERATION_CIRCUITS, IntegrationFailure

    calls, available = [], False

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        if not available:
            return httpx.Response(503, headers={"Retry-After": "46080"})
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": '{"claims":[]}'}]}}]}
        )

    config = settings()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        for _ in range(4):
            with pytest.raises(IntegrationFailure) as error:
                await generate_claims(client, config, "Question")
            assert error.value.code == "provider_unavailable"
            assert error.value.provider_status == 503
        assert len(calls) == 2
        assert all(c.until <= time.monotonic() + 120 for c in _GENERATION_CIRCUITS.values())
        available = True
        for circuit in _GENERATION_CIRCUITS.values():
            circuit.until = time.monotonic() - 1
        output = await generate_claims(client, config, "Question")
    assert output["_model"] == "gemini-3.8-flash"
    assert len(calls) == 3


async def test_shared_quota_cooldown_is_credential_scoped():
    from ps01_api.integrations import IntegrationFailure

    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(True)
        return httpx.Response(429, json={"error": {"details": [{"retryDelay": "46080s"}]}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        for _ in range(3):
            with pytest.raises(IntegrationFailure) as error:
                await generate_claims(client, settings(), "Question")
            assert error.value.code == "provider_rate_limited"
        assert len(calls) == 1
        other = settings()
        other.gemini_api_key = SecretStr("another-test-key")
        with pytest.raises(IntegrationFailure):
            await generate_claims(client, other, "Question")
        assert len(calls) == 2


async def test_concurrent_requests_and_half_open_probes_are_bounded():
    import asyncio
    import time

    from ps01_api.integrations import _GENERATION_CIRCUITS, IntegrationFailure

    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        if "3.8" in request.url.path:
            entered.set()
            await release.wait()
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        first = asyncio.create_task(generate_claims(client, settings(), "Question"))
        await entered.wait()
        for _ in range(3):
            with pytest.raises(IntegrationFailure):
                await generate_claims(client, settings(), "Question")
        release.set()
        with pytest.raises(IntegrationFailure):
            await first
        assert len(calls) == 2
        for circuit in _GENERATION_CIRCUITS.values():
            circuit.until = time.monotonic() - 1
        entered.clear()
        release.clear()
        probe = asyncio.create_task(generate_claims(client, settings(), "Question"))
        await entered.wait()
        with pytest.raises(IntegrationFailure):
            await generate_claims(client, settings(), "Question")
        release.set()
        with pytest.raises(IntegrationFailure):
            await probe
        assert len(calls) == 4


async def test_catalogue_outage_is_classified_and_cooled_down():
    from ps01_api.integrations import IntegrationFailure

    calls = []

    async def handler(request):
        calls.append(request.method)
        raise httpx.ReadTimeout("catalogue timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        for _ in range(3):
            with pytest.raises(IntegrationFailure) as error:
                await generate_claims(client, settings(), "Question")
            assert error.value.code == "provider_timeout"
    assert calls == ["GET"]


async def test_async_authorization_gate_does_not_allow_concurrent_model_storm():
    import asyncio

    from ps01_api.integrations import IntegrationFailure

    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def recheck():
        entered.set()
        await release.wait()
        return "current evidence"

    async def handler(request):
        if request.method == "GET":
            return inventory()
        calls.append(request.url.path)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        first = asyncio.create_task(
            generate_claims(client, settings(), "Question", before_attempt=recheck)
        )
        await entered.wait()
        with pytest.raises(IntegrationFailure):
            await generate_claims(client, settings(), "Question")
        release.set()
        with pytest.raises(IntegrationFailure):
            await first
    assert len(calls) == 2
