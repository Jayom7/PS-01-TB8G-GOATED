"""Private hosted originals; callers must first authorize the document with RLS."""

from pathlib import PurePosixPath
from uuid import UUID

from .ingestion import MAX_SOURCE_BYTES
from .integrations import IntegrationFailure

BUCKET = "clearframe-originals"
PREFIX = f"supabase://{BUCKET}/"
MEDIA = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def object_name(storage_path, source_id, organization_id=None):
    if not isinstance(storage_path, str) or not storage_path.startswith(PREFIX):
        raise IntegrationFailure("Invalid original location", code="storage_unavailable")
    name = storage_path[len(PREFIX) :]
    parts = name.split("/")
    try:
        organization, filename = parts
        UUID(organization)
        path = PurePosixPath(filename)
        if (
            str(UUID(source_id)) != path.stem
            or path.suffix not in MEDIA
            or (organization_id is not None and organization != str(organization_id))
        ):
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise IntegrationFailure("Invalid original location", code="storage_unavailable") from exc
    return name


def headers(settings):
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise IntegrationFailure("Original storage is unavailable", code="storage_unavailable")
    key = settings.supabase_secret_key.get_secret_value()
    return {"apikey": key, "Authorization": f"Bearer {key}"}


async def upload_original(client, settings, organization_id, source_id, suffix, data):
    storage_path = f"{PREFIX}{organization_id}/{source_id}{suffix}"
    name = object_name(storage_path, source_id, organization_id)
    response = await client.post(
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{BUCKET}/{name}",
        headers=headers(settings) | {"Content-Type": MEDIA[suffix], "x-upsert": "false"},
        content=data,
    )
    if response.is_error:
        raise IntegrationFailure("Original could not be stored", code="storage_unavailable")
    return storage_path


async def read_original(client, settings, doc):
    name = object_name(doc["storage_path"], doc["id"], doc["organization_id"])
    async with client.stream(
        "GET",
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/authenticated/{BUCKET}/{name}",
        headers=headers(settings),
    ) as response:
        if response.is_error:
            raise IntegrationFailure("Original is unavailable", code="storage_unavailable")
        data = bytearray()
        async for part in response.aiter_bytes():
            data.extend(part)
            if len(data) > MAX_SOURCE_BYTES:
                raise IntegrationFailure("Original exceeds its limit", code="storage_unavailable")
        if not data:
            raise IntegrationFailure("Original is unavailable", code="storage_unavailable")
    return bytes(data), PurePosixPath(name).suffix


async def delete_original(client, settings, storage_path, source_id):
    name = object_name(storage_path, source_id)
    response = await client.request(
        "DELETE",
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{BUCKET}",
        headers=headers(settings),
        json={"prefixes": [name]},
    )
    return response.status_code in {200, 204, 404}
