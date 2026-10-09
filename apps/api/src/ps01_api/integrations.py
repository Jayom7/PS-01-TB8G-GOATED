from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from typing import Any

import httpx

from .config import Settings
from .rag import GENERATION_POLICY

GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


class IntegrationFailure(Exception):
    """An upstream provider or database integration failed safely."""

    def __init__(self, message: str, *, code: str = "upstream_unavailable") -> None:
        super().__init__(message)
        self.code = code
        self.retry_after: int | None = None
        self.provider_status: int | None = None
        self.evidence: list[dict] = []
        self.timing_ms: dict[str, float | None] | None = None
        self.stage: str | None = None
        self.model_attempts: list[dict] = []


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
        raise provider_failure(response)
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


_MODEL_INVENTORY: dict[str, tuple[float, set[str]]] = {}


async def generation_models(client, settings):
    key = settings.gemini_api_key.get_secret_value()
    fingerprint = hashlib.sha256(key.encode()).hexdigest()
    cached = _MODEL_INVENTORY.get(fingerprint)
    if not cached or cached[0] < time.monotonic():
        response = await client.get(
            f"{GEMINI_API_ROOT}/models", headers={"x-goog-api-key": key}, timeout=5.0
        )
        if response.is_error:
            raise provider_failure(response)
        try:
            available = {
                m["name"].removeprefix("models/")
                for m in response.json()["models"]
                if "generateContent" in m.get("supportedGenerationMethods", [])
            }
        except (ValueError, TypeError, KeyError) as exc:
            raise IntegrationFailure(
                "Invalid model catalogue", code="provider_invalid_response"
            ) from exc
        _MODEL_INVENTORY[fingerprint] = (time.monotonic() + 300, available)
    else:
        available = cached[1]
    configured = list(
        dict.fromkeys(
            m.removeprefix("models/")
            for m in (settings.gemini_chat_model, settings.gemini_fallback_chat_model)
            if m
        )
    )
    eligible = [m for m in configured if m in available]
    if not eligible:
        raise IntegrationFailure("Configured models are unsupported", code="provider_invalid_model")
    return eligible


def provider_failure(response):
    code = {
        429: "provider_rate_limited",
        401: "provider_authentication_failed",
        403: "provider_authentication_failed",
        404: "provider_invalid_model",
        400: "provider_invalid_request",
        504: "provider_timeout",
    }.get(response.status_code, "provider_unavailable")
    failure = IntegrationFailure(f"Gemini request failed (HTTP {response.status_code})", code=code)
    failure.provider_status = response.status_code
    try:
        error = response.json().get("error", {})
        details = error.get("details", [])
        for detail in details:
            delay = detail.get("retryDelay", "")
            if delay.endswith("s"):
                failure.retry_after = max(1, math.ceil(float(delay[:-1])))
        header = response.headers.get("retry-after", "")
        if header.isdigit():
            failure.retry_after = int(header)
    except (ValueError, TypeError, AttributeError):
        pass
    return failure


def model_scoped_quota(response):
    """Switch once only when all quota violations explicitly name this model.

    Unknown/project/global quotas stop immediately; switching cannot fix them.
    """
    try:
        details = response.json()["error"]["details"]
        violations = [v for detail in details for v in detail.get("violations", [])]
        return bool(violations) and all(
            v.get("quotaDimensions", {}).get("model") for v in violations
        )
    except (ValueError, KeyError, TypeError):
        return False


async def generate_claims(client, settings, prompt, before_attempt=None):
    if not settings.gemini_api_key:
        raise IntegrationFailure("Gemini is not configured", code="provider_unavailable")
    attempts = []
    try:
        async with asyncio.timeout(settings.generation_budget_seconds):
            return await _generate_bounded(client, settings, prompt, before_attempt, attempts)
    except IntegrationFailure as exc:
        exc.model_attempts = attempts
        raise
    except TimeoutError as exc:
        failure = IntegrationFailure("Generation budget exceeded", code="provider_timeout")
        failure.model_attempts = attempts
        raise failure from exc


async def _generate_bounded(client, settings, prompt, before_attempt, attempts):
    models = await generation_models(client, settings)
    payload = {
        "systemInstruction": {"parts": [{"text": GENERATION_POLICY}]},
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
                                "evidence_ids": {"type": "ARRAY", "items": {"type": "STRING"}}
                            },
                            "required": ["evidence_ids"],
                        },
                    }
                },
                "required": ["claims"],
            },
        },
    }
    for index, model in enumerate(models):
        # Gemini 3 Flash defaults to medium thinking. This bounded selector
        # resolves IDs rather than composing facts; low avoids spending the
        # request deadline/token budget on unnecessary reasoning. Other model
        # families keep their own supported defaults.
        if model in {"gemini-3.8-flash", "gemini-3.7-flash"}:
            payload["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}
        else:
            payload["generationConfig"].pop("thinkingConfig", None)
        if before_attempt:
            payload["contents"][0]["parts"][0]["text"] = await before_attempt()
        attempt = {"model": model}
        attempts.append(attempt)
        started = time.perf_counter()
        try:
            response = await client.post(
                f"{GEMINI_API_ROOT}/models/{model}:generateContent",
                headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()},
                json=payload,
                timeout=httpx.Timeout(20.0, connect=5.0),
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            attempt["code"] = (
                "provider_timeout"
                if isinstance(exc, httpx.TimeoutException)
                else "provider_unavailable"
            )
            if index + 1 < len(models):
                await asyncio.sleep(0.25)
                continue
            raise IntegrationFailure(
                "Gemini transport failed",
                code=(
                    "provider_timeout"
                    if isinstance(exc, httpx.TimeoutException)
                    else "provider_unavailable"
                ),
            ) from exc
        finally:
            attempt["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        attempt["provider_status"] = response.status_code
        if response.is_error:
            failure = provider_failure(response)
            attempt["code"] = failure.code
            retryable = response.status_code in {404, 500, 502, 503, 504} or (
                response.status_code == 429 and model_scoped_quota(response)
            )
            if retryable and index + 1 < len(models):
                # A different model is a different quota bucket; never retry this
                # exhausted model before its RetryInfo interval has elapsed.
                await asyncio.sleep(0.25)
                continue
            raise failure
        try:
            body = response.json()
            if body.get("promptFeedback", {}).get("blockReason"):
                raise IntegrationFailure("Provider safety block", code="provider_safety_block")
            candidate = body["candidates"][0]
            if candidate.get("finishReason") in {"SAFETY", "RECITATION", "PROHIBITED_CONTENT"}:
                raise IntegrationFailure("Provider safety block", code="provider_safety_block")
            output = json.loads("".join(p.get("text", "") for p in candidate["content"]["parts"]))
            if not isinstance(output, dict) or not isinstance(output.get("claims"), list):
                raise ValueError("Invalid claims")
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise IntegrationFailure(
                "Malformed structured output", code="provider_invalid_response"
            ) from exc
        attempt["code"] = "success"
        return output | {
            "_model": model,
            "_fallback_used": model != settings.gemini_chat_model,
            "_attempts": attempts,
        }
    raise IntegrationFailure("No eligible model", code="provider_invalid_model")
