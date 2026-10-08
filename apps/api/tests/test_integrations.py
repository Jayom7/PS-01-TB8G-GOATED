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
async def test_generation_falls_back_after_transient_primary_model_outage(monkeypatch) -> None:
    calls: list[str] = []

    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr("ps01_api.integrations.asyncio.sleep", no_wait)

    async def handler(request: httpx.Request) -> httpx.Response:
        model = request.url.path.split("/")[-1].split(":")[0]
        calls.append(model)
        if model == "gemini-3.8-flash":
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"claims":[]}'}]}}]},
        )

    config = settings()
    config.gemini_fallback_chat_model = "gemini-3.6-flash"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        output = await generate_claims(client, config, "Return no claims.")

    assert calls == ["gemini-3.8-flash"] * 3 + ["gemini-3.6-flash"]
    assert output["claims"] == []
    assert output["_model"] == "gemini-3.6-flash"


@pytest.mark.asyncio
async def test_generation_falls_back_when_primary_model_times_out() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
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

    assert calls == ["gemini-3.8-flash", "gemini-3.6-flash"]
    assert output["_model"] == "gemini-3.6-flash"
