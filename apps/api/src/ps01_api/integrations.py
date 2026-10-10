from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from dataclasses import dataclass, field
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


async def create_embedding(
    client: httpx.AsyncClient, settings: Settings, text: str, before_attempt=None
) -> list[float]:
    return await _create_embedding(
        client,
        settings,
        f"task: search result | query: {text}",
        before_attempt,
    )


async def create_document_embedding(
    client: httpx.AsyncClient, settings: Settings, title: str, text: str, before_attempt=None
) -> list[float]:
    return await _create_embedding(
        client,
        settings,
        f"title: {title or 'none'} | text: {text}",
        before_attempt,
    )


def provider_projects(settings):
    """At most two operator-provisioned Gemini projects; same models and space."""
    if not settings.gemini_api_key or not settings.gemini_api_key.get_secret_value().strip():
        raise IntegrationFailure("Gemini is not configured", code="provider_invalid_request")
    if settings.gemini_secondary_api_key:
        if (
            not settings.gemini_project_id
            or not settings.gemini_secondary_project_id
            or not settings.gemini_project_id.strip()
            or not settings.gemini_secondary_project_id.strip()
            or settings.gemini_project_id.strip() == settings.gemini_secondary_project_id.strip()
            or not settings.gemini_secondary_api_key.get_secret_value().strip()
            or settings.gemini_api_key == settings.gemini_secondary_api_key
        ):
            raise IntegrationFailure(
                "Independent project configuration required", code="provider_invalid_request"
            )
    projects = [settings]
    if settings.gemini_secondary_api_key:
        projects.append(
            settings.model_copy(
                update={
                    "gemini_api_key": settings.gemini_secondary_api_key,
                    "gemini_project_id": settings.gemini_secondary_project_id,
                    "gemini_secondary_api_key": None,
                }
            )
        )
    return projects


def redundancy_eligible(failure):
    return failure.code in {
        "provider_rate_limited",
        "provider_timeout",
        "provider_unavailable",
    }


async def _create_embedding(client, settings, input_text, before_attempt=None):
    # One fixed model/dimension pair for both projects. No alternate space or
    # model substitution is permitted against the existing index.
    if (
        settings.embedding_dimensions != 1536
        or settings.gemini_embedding_model.removeprefix("models/") != "gemini-embedding-2"
    ):
        raise IntegrationFailure("Index dimension mismatch", code="provider_invalid_request")
    last_failure = None
    try:
        async with asyncio.timeout(settings.generation_budget_seconds):
            for project in provider_projects(settings):
                model = project.gemini_embedding_model.removeprefix("models/")
                circuit = _circuit(project, "embedding:" + model)
                # Serialize requests per project so a failed chunk stops queued
                # requests before they multiply quota failures. No text cache.
                async with circuit.lock:
                    if failure := _blocked(circuit):
                        if not redundancy_eligible(failure):
                            raise failure
                        last_failure = failure
                        continue
                    # Run after queued requests/cooldowns and immediately before
                    # sending private input. Access failures never cool a provider.
                    if before_attempt:
                        await before_attempt()
                    try:
                        response = await client.post(
                            f"{GEMINI_API_ROOT}/models/{model}:embedContent",
                            headers={"x-goog-api-key": project.gemini_api_key.get_secret_value()},
                            json={
                                "model": f"models/{model}",
                                "content": {"parts": [{"text": input_text}]},
                                "outputDimensionality": project.embedding_dimensions,
                            },
                            timeout=httpx.Timeout(20.0, connect=5.0),
                        )
                        if response.is_error:
                            raise provider_failure(response)
                        body = response.json()
                        values = body.get("embedding", {}).get("values")
                        if (
                            not isinstance(values, list)
                            or len(values) != settings.embedding_dimensions
                            or not all(type(v) in {int, float} and math.isfinite(v) for v in values)
                        ):
                            raise ValueError("Invalid vector")
                    except (httpx.TransportError, TimeoutError) as exc:
                        last_failure = _transport_failure(exc)
                        _cool_down(circuit, last_failure)
                        continue
                    except IntegrationFailure as exc:
                        _cool_down(circuit, exc)
                        if not redundancy_eligible(exc):
                            raise
                        last_failure = exc
                        continue
                    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
                        raise IntegrationFailure(
                            "Invalid embedding response", code="provider_invalid_response"
                        ) from exc
                    circuit.failure, circuit.until = None, 0
                    return [float(value) for value in values]
    except TimeoutError as exc:
        raise _transport_failure(exc) from exc
    raise last_failure or IntegrationFailure("Embedding unavailable", code="provider_unavailable")


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


@dataclass
class _Circuit:
    until: float = 0
    failure: IntegrationFailure | None = None
    in_flight: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


# Metadata only, credential/provider/model scoped, per API worker. One in-flight
# call per model also prevents concurrent half-open probes from causing a storm.
_GENERATION_CIRCUITS: dict[tuple[str, str], _Circuit] = {}


def _circuit(settings, model):
    fingerprint = hashlib.sha256(settings.gemini_api_key.get_secret_value().encode()).hexdigest()
    key = (settings.gemini_project_id or fingerprint, model)
    if key not in _GENERATION_CIRCUITS and len(_GENERATION_CIRCUITS) >= 512:
        expired = [
            k
            for k, v in _GENERATION_CIRCUITS.items()
            if not v.in_flight and v.until <= time.monotonic()
        ]
        for old in expired:
            del _GENERATION_CIRCUITS[old]
    return _GENERATION_CIRCUITS.setdefault(key, _Circuit())


def _blocked(circuit):
    if not circuit.in_flight and circuit.until <= time.monotonic():
        return None
    previous = circuit.failure
    failure = IntegrationFailure(
        "Generation cooldown" if previous else "Generation already in flight",
        code=previous.code if previous else "provider_unavailable",
    )
    if previous:
        failure.provider_status = previous.provider_status
        failure.retry_after = previous.retry_after
    return failure


def _cool_down(circuit, failure):
    circuit.failure = failure
    # A long upstream RetryInfo is diagnostic, never an hours-long local lockout.
    # At most one bounded probe becomes eligible again in 30–120 seconds.
    circuit.until = time.monotonic() + min(120, max(30, failure.retry_after or 30))


def _transport_failure(exc):
    return IntegrationFailure(
        "Gemini transport failed",
        code="provider_timeout"
        if isinstance(exc, (httpx.TimeoutException, TimeoutError))
        else "provider_unavailable",
    )


async def generation_models(client, settings):
    key = settings.gemini_api_key.get_secret_value()
    fingerprint = hashlib.sha256(key.encode()).hexdigest()
    cached = _MODEL_INVENTORY.get(fingerprint)
    if not cached or cached[0] < time.monotonic():
        circuit = _circuit(settings, "catalogue")
        if failure := _blocked(circuit):
            raise failure
        circuit.in_flight = True
        try:
            response = await client.get(
                f"{GEMINI_API_ROOT}/models", headers={"x-goog-api-key": key}, timeout=5.0
            )
        except (httpx.TransportError, TimeoutError) as exc:
            failure = _transport_failure(exc)
            _cool_down(circuit, failure)
            raise failure from exc
        finally:
            circuit.in_flight = False
        if response.is_error:
            failure = provider_failure(response)
            _cool_down(circuit, failure)
            raise failure
        try:
            available = {
                m["name"].removeprefix("models/")
                for m in response.json()["models"]
                if "generateContent" in m.get("supportedGenerationMethods", [])
            }
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise IntegrationFailure(
                "Invalid model catalogue", code="provider_invalid_response"
            ) from exc
        _MODEL_INVENTORY[fingerprint] = (time.monotonic() + 300, available)
        circuit.failure, circuit.until = None, 0
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
        408: "provider_timeout",
        504: "provider_timeout",
    }.get(
        response.status_code,
        "provider_invalid_request" if 400 <= response.status_code < 500 else "provider_unavailable",
    )
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
    except (ValueError, KeyError, TypeError, AttributeError):
        return False


async def _generation_backoff(attempts):
    # Share one retry schedule across models and projects. The enclosing total
    # budget also bounds these waits; never retry the same cooled-down target.
    sent = sum(attempt.get("attempted") is True for attempt in attempts)
    await asyncio.sleep(min(4.0, 2.0 ** max(0, sent - 1)))


async def generate_claims(client, settings, prompt, before_attempt=None, attempt_observer=None):
    attempts = []
    try:
        async with asyncio.timeout(settings.generation_budget_seconds):
            projects = provider_projects(settings)
            last_failure = None
            for project_index, project in enumerate(projects):
                if not project.gemini_api_key:
                    continue
                try:
                    output = await _generate_bounded(
                        client,
                        project,
                        prompt,
                        before_attempt,
                        attempts,
                        attempt_observer,
                        request_timeout=10.0 if len(projects) > 1 else 20.0,
                    )
                    output["_fallback_used"] |= project is not settings
                    return output
                except IntegrationFailure as exc:
                    if not redundancy_eligible(exc):
                        raise
                    last_failure = exc
                    if project_index + 1 < len(projects):
                        await _generation_backoff(attempts)
            raise last_failure or IntegrationFailure(
                "No eligible project", code="provider_unavailable"
            )
    except IntegrationFailure as exc:
        exc.model_attempts = attempts
        raise
    except TimeoutError as exc:
        failure = IntegrationFailure("Generation budget exceeded", code="provider_timeout")
        failure.model_attempts = attempts
        raise failure from exc


async def _generate_bounded(
    client, settings, prompt, before_attempt, attempts, attempt_observer=None, request_timeout=20.0
):
    shared = _circuit(settings, "shared-quota")
    if failure := _blocked(shared):
        raise failure
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
    last_failure = None
    for index, model in enumerate(models):
        circuit = _circuit(settings, model)
        if failure := _blocked(circuit):
            if not redundancy_eligible(failure):
                raise failure
            last_failure = failure
            attempts.append(
                {
                    "model": model,
                    "code": failure.code,
                    "attempted": False,
                    "cooldown": True,
                    "provider_status": failure.provider_status,
                }
            )
            continue
        # Gemini 3 Flash defaults to medium thinking. This bounded selector
        # resolves IDs rather than composing facts; low avoids spending the
        # request deadline/token budget on unnecessary reasoning. Other model
        # families keep their own supported defaults.
        if model in {"gemini-3.8-flash", "gemini-3.7-flash"}:
            payload["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}
        else:
            payload["generationConfig"].pop("thinkingConfig", None)
        # Reserve before the asynchronous access check; otherwise concurrent
        # requests can all pass the closed-circuit check while awaiting RLS.
        circuit.in_flight = True
        try:
            if before_attempt:
                payload["contents"][0]["parts"][0]["text"] = await before_attempt()
        except BaseException:
            circuit.in_flight = False
            raise
        attempt = {
            "model": model,
            "attempted": False,
            "provider": "gemini",
            "project": "secondary"
            if settings.gemini_project_id
            and settings.gemini_project_id == settings.gemini_secondary_project_id
            else "primary",
        }
        attempts.append(attempt)
        if attempt_observer:
            try:
                await attempt_observer("started", attempt, payload)
            except BaseException as exc:
                circuit.in_flight = False
                attempt["code"] = getattr(exc, "code", "not_sent")
                raise
        attempt["attempted"] = True
        try:
            started = time.perf_counter()
            try:
                response = await client.post(
                    f"{GEMINI_API_ROOT}/models/{model}:generateContent",
                    headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()},
                    json=payload,
                    timeout=httpx.Timeout(request_timeout, connect=5.0),
                )
            except (httpx.TransportError, TimeoutError) as exc:
                failure = _transport_failure(exc)
                _cool_down(circuit, failure)
                attempt["code"] = failure.code
                last_failure = failure
                if index + 1 < len(models):
                    await _generation_backoff(attempts)
                    continue
                raise failure from exc
            except asyncio.CancelledError:
                failure = _transport_failure(TimeoutError())
                _cool_down(circuit, failure)
                attempt["code"] = failure.code
                raise
            finally:
                circuit.in_flight = False
                attempt["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
            attempt["provider_status"] = response.status_code
            if response.is_error:
                failure = provider_failure(response)
                attempt["code"] = failure.code
                retryable = (
                    response.status_code == 408
                    or response.status_code >= 500
                    or (response.status_code == 429 and model_scoped_quota(response))
                )
                _cool_down(circuit, failure)
                if response.status_code == 429 and not model_scoped_quota(response):
                    _cool_down(shared, failure)
                last_failure = failure
                if retryable and index + 1 < len(models):
                    # A different model is a different quota bucket; never retry this
                    # exhausted model before its RetryInfo interval has elapsed.
                    await _generation_backoff(attempts)
                    continue
                raise failure
            try:
                body = response.json()
                if body.get("promptFeedback", {}).get("blockReason"):
                    raise IntegrationFailure("Provider safety block", code="provider_safety_block")
                candidate = body["candidates"][0]
                if candidate.get("finishReason") in {"SAFETY", "RECITATION", "PROHIBITED_CONTENT"}:
                    raise IntegrationFailure("Provider safety block", code="provider_safety_block")
                output = json.loads(
                    "".join(p.get("text", "") for p in candidate["content"]["parts"])
                )
                if not isinstance(output, dict) or not isinstance(output.get("claims"), list):
                    raise ValueError("Invalid claims")
            except (IndexError, KeyError, TypeError, ValueError, AttributeError) as exc:
                raise IntegrationFailure(
                    "Malformed structured output", code="provider_invalid_response"
                ) from exc
            attempt["code"] = "success"
            circuit.failure, circuit.until = None, 0
            return output | {
                "_model": model,
                "_fallback_used": model != settings.gemini_chat_model,
                "_attempts": attempts,
            }
        except IntegrationFailure as exc:
            attempt["code"] = exc.code
            raise
        finally:
            if attempt_observer:
                await attempt_observer("finished", attempt, payload)
    raise last_failure or IntegrationFailure("No eligible model", code="provider_invalid_model")
