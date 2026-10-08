from __future__ import annotations

import json
import math
from typing import Any

import httpx

from .config import Settings

GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


class IntegrationFailure(Exception):
    """An upstream provider or database integration failed safely."""

    def __init__(self, message: str, *, code: str = "upstream_unavailable") -> None:
        super().__init__(message)
        self.code = code
        self.timing_ms: dict[str, float | None] | None = None


async def verify_supabase_session(
    client: httpx.AsyncClient, settings: Settings, access_token: str
) -> dict[str, Any] | None:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise IntegrationFailure("Supabase is not configured")
    response = await client.get(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
        headers={
            "apikey": settings.supabase_publishable_key.get_secret_value(),
            "Authorization": f"Bearer {access_token}",
        },
    )
    if response.status_code in (401, 403):
        return None
    if response.is_error:
        raise IntegrationFailure("Supabase authentication is unavailable")
    try:
        user = response.json()
    except ValueError as exc:
        raise IntegrationFailure("Supabase returned an invalid authentication response") from exc
    return user if isinstance(user, dict) and isinstance(user.get("id"), str) else None


async def create_embedding(client: httpx.AsyncClient, settings: Settings, text: str) -> list[float]:
    return await _create_embedding(
        client,
        settings,
        f"task: search result | query: {text}",
    )


async def create_document_embedding(
    client: httpx.AsyncClient, settings: Settings, title: str, text: str
) -> list[float]:
    return await _create_embedding(
        client,
        settings,
        f"title: {title or 'none'} | text: {text}",
    )


async def _create_embedding(
    client: httpx.AsyncClient, settings: Settings, input_text: str
) -> list[float]:
    if not settings.gemini_api_key:
        raise IntegrationFailure("Gemini is not configured", code="provider_unavailable")
    if settings.embedding_dimensions != 1536:
        raise IntegrationFailure(
            "Gemini dimensions do not match the configured database schema",
            code="provider_unavailable",
        )
    model = settings.gemini_embedding_model.removeprefix("models/")
    response = await client.post(
        f"{GEMINI_API_ROOT}/models/{model}:embedContent",
        headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()},
        json={
            "model": f"models/{model}",
            "content": {"parts": [{"text": input_text}]},
            "embedContentConfig": {
                "outputDimensionality": settings.embedding_dimensions,
            },
        },
    )
    if response.is_error:
        raise IntegrationFailure("Gemini embedding request failed", code="provider_unavailable")
    try:
        body = response.json()
    except ValueError as exc:
        raise IntegrationFailure(
            "Gemini returned an invalid embedding response", code="provider_unavailable"
        ) from exc
    embedding = body.get("embedding")
    values = embedding.get("values") if isinstance(embedding, dict) else None
    if (
        not isinstance(values, list)
        or len(values) != settings.embedding_dimensions
        or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values)
    ):
        raise IntegrationFailure(
            "Gemini returned an invalid embedding", code="provider_unavailable"
        )
    return [float(value) for value in values]


async def retrieve_chunks(
    client: httpx.AsyncClient,
    settings: Settings,
    access_token: str,
    query: str,
    embedding: list[float],
) -> list[dict[str, Any]]:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise IntegrationFailure("Supabase is not configured")
    response = await client.post(
        f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/match_knowledge_chunks",
        headers={
            "apikey": settings.supabase_publishable_key.get_secret_value(),
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "query_embedding": embedding,
            "query_text": query,
            "match_count": 12,
        },
    )
    if response.is_error:
        raise IntegrationFailure(
            "Authorized retrieval is unavailable", code="retrieval_unavailable"
        )
    try:
        rows = response.json()
    except ValueError as exc:
        raise IntegrationFailure(
            "Supabase returned invalid retrieval data", code="retrieval_unavailable"
        ) from exc
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise IntegrationFailure(
            "Supabase returned an invalid retrieval response", code="retrieval_unavailable"
        )
    return rows


async def generate_claims(
    client: httpx.AsyncClient, settings: Settings, prompt: str
) -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise IntegrationFailure("Gemini is not configured", code="provider_unavailable")
    models = list(
        dict.fromkeys(
            model.removeprefix("models/")
            for model in (settings.gemini_chat_model, settings.gemini_fallback_chat_model)
            if model
        )
    )
    if not models:
        raise IntegrationFailure(
            "Gemini has no configured generation model", code="provider_unavailable"
        )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 1024,
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "claims": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "text": {"type": "STRING"},
                                "citation_ids": {
                                    "type": "ARRAY",
                                    "items": {"type": "STRING"},
                                },
                                "supporting_quotes": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "citation_id": {"type": "STRING"},
                                            "quote": {"type": "STRING"},
                                        },
                                        "required": ["citation_id", "quote"],
                                    },
                                },
                            },
                            "required": ["text", "citation_ids", "supporting_quotes"],
                        },
                    }
                },
                "required": ["claims"],
            },
        },
    }
    response = None
    used_model = models[0]
    fallback_used = False
    last_failure: IntegrationFailure | None = None
    for model_index, model in enumerate(models):
        used_model = model
        fallback_used = model_index > 0
        try:
            response = await client.post(
                f"{GEMINI_API_ROOT}/models/{model}:generateContent",
                headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()},
                json=payload,
                timeout=httpx.Timeout(15.0, connect=5.0),
            )
        except httpx.TimeoutException as exc:
            last_failure = IntegrationFailure(
                "Gemini generation timed out", code="provider_timeout"
            )
            if model_index + 1 < len(models):
                continue
            raise last_failure from exc
        except httpx.TransportError as exc:
            last_failure = IntegrationFailure(
                "Gemini could not be reached", code="provider_unavailable"
            )
            if model_index + 1 < len(models):
                continue
            raise last_failure from exc
        if response.status_code in {500, 502, 503, 504} and model_index + 1 < len(models):
            continue
        break
    if response is None:
        raise last_failure or IntegrationFailure(
            "Gemini generation failed", code="provider_unavailable"
        )
    if response.is_error:
        code = (
            "provider_rate_limited"
            if response.status_code == 429
            else "provider_timeout"
            if response.status_code == 504
            else "provider_unavailable"
        )
        raise IntegrationFailure(
            f"Gemini generation is temporarily unavailable (HTTP {response.status_code})",
            code=code,
        )
    try:
        body = response.json()
        candidates = body.get("candidates") if isinstance(body, dict) else None
        model_text = candidates[0]["content"]["parts"][0]["text"]
        output = json.loads(model_text)
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise IntegrationFailure(
            "Gemini returned malformed structured output", code="provider_invalid_response"
        ) from exc
    if not isinstance(output, dict):
        raise IntegrationFailure(
            "Gemini returned malformed structured output", code="provider_invalid_response"
        )
    output["_model"] = used_model
    output["_fallback_used"] = fallback_used
    return output
