"""Hosted storage, real-identity administration, OCR adapter and origin boundaries."""

import subprocess
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ps01_api.config import Settings
from ps01_api.integrations import IntegrationFailure
from ps01_api.main import _require_ceo, app, source_original
from ps01_api.originals import PREFIX, delete_original, object_name, read_original, upload_original
from ps01_api.tesseract_ocr import TesseractOCR

ORG = "11111111-1111-4111-8111-111111111111"
DOC = "22222222-2222-4222-8222-222222222222"
IDENTITY = {"user_id": "actor", "organization_id": ORG, "role": "CEO", "roles": ["CEO"]}


def config():
    return Settings(
        _env_file=None,
        supabase_url="https://hosted.test",
        supabase_publishable_key=SecretStr("public"),
        supabase_secret_key=SecretStr("server-only"),
        ingestion_enabled=True,
        original_storage="supabase",
    )


async def test_hosted_admin_requires_verified_ceo_and_rejects_forged_context():
    with (
        patch("ps01_api.main.get_settings", return_value=config()),
        patch("ps01_api.main.require_session", AsyncMock(return_value="actor-token")),
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch("ps01_api.main._context_token", AsyncMock(return_value=("actor-token", "CEO"))),
    ):
        assert await _require_ceo(AsyncMock(), "Bearer actor-token", None) == (
            "actor-token",
            IDENTITY,
        )
    hr = {**IDENTITY, "role": "HR Manager", "roles": ["HR Manager"]}
    with (
        patch("ps01_api.main.get_settings", return_value=config()),
        patch("ps01_api.main.require_session", AsyncMock(return_value="hr-token")),
        patch("ps01_api.main._identity", AsyncMock(return_value=hr)),
    ):
        with pytest.raises(HTTPException) as error:
            await _require_ceo(AsyncMock(), "Bearer hr-token", "CEO")
        assert error.value.status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        PREFIX + ORG + "/../secret.pdf",
        PREFIX + ORG + "/wrong.pdf",
        PREFIX + ORG + "/" + DOC + ".exe",
        "https://evil.test/file.pdf",
    ],
)
def test_storage_path_cannot_escape_document_identity(path):
    with pytest.raises(IntegrationFailure):
        object_name(path, DOC, ORG)


async def test_original_storage_uses_private_server_credentials_and_no_upsert():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer server-only"
        return httpx.Response(200, content=b"%PDF-example")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        path = await upload_original(client, config(), ORG, DOC, ".pdf", b"%PDF-example")
        content, suffix = await read_original(
            client, config(), {"id": DOC, "organization_id": ORG, "storage_path": path}
        )
        assert content == b"%PDF-example" and suffix == ".pdf"
        assert await delete_original(client, config(), path, DOC)
    assert requests[0].headers["x-upsert"] == "false"
    assert "/object/authenticated/clearframe-originals/" in str(requests[1].url)
    assert requests[2].method == "DELETE"


async def test_hidden_hosted_document_never_fetches_private_object():
    with (
        patch("ps01_api.main.get_settings", return_value=config()),
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch("ps01_api.main._context_token", AsyncMock(return_value=("actor-token", "CEO"))),
        patch("ps01_api.main._rest_rows", AsyncMock(return_value=httpx.Response(200, json=[]))),
        patch("ps01_api.main.read_original", AsyncMock()) as storage,
    ):
        with pytest.raises(HTTPException) as error:
            await source_original(DOC, None, "Bearer actor-token", None)
        assert error.value.status_code == 404
        storage.assert_not_awaited()


async def test_hosted_original_reads_after_document_rls_and_never_redirects_to_signed_url():
    doc = {
        "id": DOC,
        "organization_id": ORG,
        "source_type": "image_ocr",
        "storage_path": f"{PREFIX}{ORG}/{DOC}.png",
    }
    with (
        patch("ps01_api.main.get_settings", return_value=config()),
        patch("ps01_api.main._identity", AsyncMock(return_value=IDENTITY)),
        patch("ps01_api.main._context_token", AsyncMock(return_value=("actor-token", "CEO"))),
        patch(
            "ps01_api.main._rest_rows", AsyncMock(return_value=httpx.Response(200, json=[doc]))
        ) as rows,
        patch("ps01_api.main.read_original", AsyncMock(return_value=(b"image", ".png"))),
    ):
        response = await source_original(DOC, None, "Bearer actor-token", None)
    assert rows.await_args.args[2:4] == ("actor-token", "documents")
    assert response.body == b"image" and response.headers["cache-control"] == "no-store"
    assert "location" not in response.headers


def test_native_ocr_preserves_line_text_region_and_confidence():
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t10\t20\t40\t10\t95\tInvoice\n"
        "5\t1\t1\t1\t1\t2\t55\t20\t50\t10\t90\tACM-INV-2048\n"
    )
    with patch(
        "ps01_api.tesseract_ocr.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, tsv.encode(), b""),
    ) as run:
        result = TesseractOCR().predict("source.png")[0]
    assert result["rec_texts"] == ["Invoice ACM-INV-2048"]
    assert result["rec_boxes"] == [[10, 20, 105, 30]]
    assert run.call_args.kwargs["timeout"] == 30


def test_native_ocr_timeout_is_honest_ingestion_error():
    from ps01_api.ingestion import IngestionError

    with patch(
        "ps01_api.tesseract_ocr.subprocess.run", side_effect=subprocess.TimeoutExpired([], 30)
    ):
        with pytest.raises(IngestionError):
            TesseractOCR().predict("source.png")


def test_cors_allows_only_configured_origin_and_health_discloses_no_details():
    from ps01_api.config import get_settings

    client = TestClient(app)
    headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization,X-Source-Name",
    }
    assert (
        client.options(
            "/api/v1/ingest/file", headers=headers | {"Origin": get_settings().web_origin}
        ).status_code
        == 200
    )
    assert (
        client.options(
            "/api/v1/ingest/file", headers=headers | {"Origin": "https://untrusted.test"}
        ).status_code
        == 400
    )
    assert client.get("/health").json() == {"status": "ok"}
