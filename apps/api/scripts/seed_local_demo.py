from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import shlex
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ps01_api.config import Settings, get_settings
from ps01_api.ingestion import (
    ChunkCandidate,
    extract_image_ocr,
    extract_pdf,
    structured_record_candidates,
)
from ps01_api.integrations import create_document_embedding

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "data" / "demo"
MANIFEST = CORPUS / "manifest.json"
CREDENTIALS = ROOT / ".local-demo-credentials.json"
CLI = ROOT / "node_modules" / ".bin" / "supabase"
DOCKER_BIN = "/Applications/Docker.app/Contents/Resources/bin"
ROLES = ("CEO", "Finance Manager", "HR Manager", "Sales Manager", "Engineer")


def local_supabase_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PATH"] = f"{DOCKER_BIN}:{environment.get('PATH', '')}"
    result = subprocess.run(
        [str(CLI), "status", "-o", "env"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Local Supabase is not running; start it with `supabase start`.")
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, separator, raw_value = line.partition("=")
        if separator:
            parts = shlex.split(raw_value)
            if parts:
                values[name] = parts[0]
    required = {"API_URL", "PUBLISHABLE_KEY", "SERVICE_ROLE_KEY"}
    if not required.issubset(values):
        raise RuntimeError("Local Supabase did not provide the expected API settings.")
    if urlparse(values["API_URL"]).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Refusing to seed a non-local Supabase URL.")
    return values


def credentials() -> dict[str, dict[str, str]]:
    if CREDENTIALS.exists():
        saved = json.loads(CREDENTIALS.read_text())
        if isinstance(saved, dict):
            return saved
    return {}


def save_credentials(values: dict[str, dict[str, str]]) -> None:
    CREDENTIALS.write_text(json.dumps(values, indent=2) + "\n")
    CREDENTIALS.chmod(0o600)


def rest_headers(api_key: str) -> dict[str, str]:
    return {"apikey": api_key, "Authorization": f"Bearer {api_key}"}


def request_rows(
    client: httpx.Client,
    base_url: str,
    key: str,
    table: str,
    *,
    params: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    response = client.get(
        f"{base_url}/rest/v1/{table}", headers=rest_headers(key), params=params
    )
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, list) or any(not isinstance(row, dict) for row in body):
        raise RuntimeError(f"Local Supabase returned invalid rows for {table}.")
    return body


def write_rows(
    client: httpx.Client,
    base_url: str,
    key: str,
    table: str,
    rows: list[dict[str, object]],
    *,
    on_conflict: str | None = None,
) -> list[dict[str, object]]:
    headers = rest_headers(key) | {"Content-Type": "application/json"}
    if on_conflict:
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    else:
        headers["Prefer"] = "return=representation"
    params = {"on_conflict": on_conflict} if on_conflict else None
    response = client.post(
        f"{base_url}/rest/v1/{table}", headers=headers, params=params, json=rows
    )
    if response.is_error:
        raise RuntimeError(f"Local Supabase rejected writes to {table} ({response.status_code}).")
    body = response.json()
    if not isinstance(body, list) or any(not isinstance(row, dict) for row in body):
        raise RuntimeError(f"Local Supabase returned invalid write results for {table}.")
    return body


def seed_users(
    client: httpx.Client,
    base_url: str,
    service_key: str,
    org_id: str,
    role_ids: dict[str, str],
    saved_credentials: dict[str, dict[str, str]],
) -> dict[str, str]:
    users: dict[str, str] = {}
    for role in ROLES:
        slug = role.lower().replace(" ", "-")
        email = f"{slug}@novacore.demo"
        secret = saved_credentials.get(role, {}).get("password") or secrets.token_urlsafe(20)
        response = client.post(
            f"{base_url}/auth/v1/admin/users",
            headers=rest_headers(service_key) | {"Content-Type": "application/json"},
            json={"email": email, "password": secret, "email_confirm": True},
        )
        if response.status_code == 422 and "already" in response.text.lower():
            matches = client.get(
                f"{base_url}/auth/v1/admin/users",
                headers=rest_headers(service_key),
                params={"page": 1, "per_page": 1000},
            )
            matches.raise_for_status()
            data = matches.json()
            existing = next(
                (user for user in data.get("users", []) if user.get("email") == email),
                None,
            )
            if not existing:
                raise RuntimeError("A demo auth user exists but could not be loaded.")
            user_id = str(existing["id"])
            update = client.put(
                f"{base_url}/auth/v1/admin/users/{user_id}",
                headers=rest_headers(service_key) | {"Content-Type": "application/json"},
                json={"password": secret, "email_confirm": True},
            )
            update.raise_for_status()
        else:
            response.raise_for_status()
            body = response.json()
            user = body.get("user", body) if isinstance(body, dict) else {}
            user_id = str(user["id"])
        users[role] = user_id
        saved_credentials[role] = {"email": email, "password": secret}

    save_credentials(saved_credentials)
    profiles = [
        {"user_id": user_id, "organization_id": org_id, "display_name": role}
        for role, user_id in users.items()
    ]
    write_rows(client, base_url, service_key, "profiles", profiles, on_conflict="user_id")
    assignments = [
        {
            "user_id": user_id,
            "role_id": role_ids[role],
            "organization_id": org_id,
        }
        for role, user_id in users.items()
    ]
    write_rows(
        client,
        base_url,
        service_key,
        "user_roles",
        assignments,
        on_conflict="user_id,role_id",
    )
    return users


def collect_candidates() -> list[tuple[dict[str, object], ChunkCandidate]]:
    manifest = json.loads(MANIFEST.read_text())
    output: list[tuple[dict[str, object], ChunkCandidate]] = []
    for source in manifest["sources"]:
        path = CORPUS / source["path"]
        source_id = source["source_id"]
        if source["source_type"] == "pdf":
            candidates = extract_pdf(path, source_id)
        elif source["source_type"] == "image_ocr":
            candidates = extract_image_ocr(path, source_id)
        else:
            structured = json.loads(path.read_text())
            candidates = []
            for record in structured["records"]:
                row_id = str(next(iter(record.values())))
                fields = {key: value for key, value in record.items()}
                candidates.extend(
                    structured_record_candidates(
                        table_name=structured["table"],
                        row_id=row_id,
                        source_name=path.name,
                        fields=fields,
                        source_id=source_id,
                    )
                )
        output.extend((source, candidate) for candidate in candidates)
    return output


async def embed_candidate(
    client: httpx.AsyncClient,
    settings: Settings,
    candidate: ChunkCandidate,
) -> list[float]:
    return await create_document_embedding(
        client, settings, candidate.source_name, candidate.content
    )


async def main() -> None:
    local = local_supabase_environment()
    base_url = local["API_URL"].rstrip("/")
    service_key = local["SERVICE_ROLE_KEY"]
    saved = credentials()
    manifest = json.loads(MANIFEST.read_text())
    settings = get_settings()

    with httpx.Client(timeout=20.0) as client:
        org_rows = request_rows(
            client,
            base_url,
            service_key,
            "organizations",
            params={"name": "eq.NovaCore Systems", "select": "id"},
        )
        if org_rows:
            org_id = str(org_rows[0]["id"])
        else:
            org_id = str(
                write_rows(
                    client,
                    base_url,
                    service_key,
                    "organizations",
                    [{"name": "NovaCore Systems"}],
                )[0]["id"]
            )

        role_ids: dict[str, str] = {}
        for role in ROLES:
            rows = request_rows(
                client,
                base_url,
                service_key,
                "roles",
                params={
                    "organization_id": f"eq.{org_id}",
                    "name": f"eq.{role}",
                    "select": "id",
                },
            )
            if rows:
                role_ids[role] = str(rows[0]["id"])
            else:
                inserted = write_rows(
                    client,
                    base_url,
                    service_key,
                    "roles",
                    [{"organization_id": org_id, "name": role}],
                )
                role_ids[role] = str(inserted[0]["id"])

        users = seed_users(
            client,
            base_url,
            service_key,
            org_id,
            role_ids,
            saved,
        )

        candidates = collect_candidates()
        async with httpx.AsyncClient(timeout=35.0) as embedding_client:
            vectors = await asyncio.gather(
                *(
                    embed_candidate(embedding_client, settings, candidate)
                    for _, candidate in candidates
                )
            )

        source_documents: dict[str, str] = {}
        for source in manifest["sources"]:
            path = CORPUS / source["path"]
            raw_bytes = path.read_bytes()
            content_hash = hashlib.sha256(raw_bytes).hexdigest()
            rows = request_rows(
                client,
                base_url,
                service_key,
                "documents",
                params={
                    "organization_id": f"eq.{org_id}",
                    "content_hash": f"eq.{content_hash}",
                    "select": "id",
                },
            )
            document_metadata = {
                "category": source["category"],
                "local_demo_path": str(path.relative_to(CORPUS)),
                "synthetic": True,
            }
            if rows:
                document_id = str(rows[0]["id"])
                updated = client.patch(
                    f"{base_url}/rest/v1/documents",
                    headers=rest_headers(service_key)
                    | {"Content-Type": "application/json", "Prefer": "return=minimal"},
                    params={"id": f"eq.{document_id}"},
                    json={"storage_path": None, "metadata": document_metadata},
                )
                updated.raise_for_status()
            else:
                document_rows = write_rows(
                    client,
                    base_url,
                    service_key,
                    "documents",
                    [
                        {
                            "organization_id": org_id,
                            "source_type": source["source_type"],
                            "source_name": path.name,
                            "content_hash": content_hash,
                            "metadata": document_metadata,
                            "created_by": users["CEO"],
                        }
                    ],
                )
                document_id = str(document_rows[0]["id"])
            source_documents[source["source_id"]] = document_id

        chunk_rows: list[dict[str, object]] = []
        for (source, candidate), vector in zip(candidates, vectors, strict=True):
            chunk_rows.append(
                {
                    "organization_id": org_id,
                    "document_id": source_documents[source["source_id"]],
                    "source_type": candidate.source_type,
                    "source_name": candidate.source_name,
                    "source_id": candidate.source_id,
                    "page_number": candidate.page_number,
                    "row_id": candidate.row_id,
                    "image_id": candidate.image_id,
                    "ocr_region": candidate.ocr_region,
                    "chunk_index": candidate.chunk_index,
                    "content": candidate.content,
                    "metadata": {
                        **(candidate.metadata or {}),
                        "category": source["category"],
                    },
                    "embedding": vector,
                }
            )
        write_rows(
            client,
            base_url,
            service_key,
            "knowledge_chunks",
            chunk_rows,
            on_conflict="document_id,chunk_index",
        )

        grants: list[dict[str, object]] = []
        for source in manifest["sources"]:
            for role in source["allowed_roles"]:
                grants.append(
                    {
                        "organization_id": org_id,
                        "document_id": source_documents[source["source_id"]],
                        "principal_type": "role",
                        "principal_id": role_ids[role],
                        "can_read": True,
                    }
                )
        existing_grants = request_rows(
            client,
            base_url,
            service_key,
            "access_grants",
            params={"organization_id": f"eq.{org_id}", "select": "id"},
        )
        if not existing_grants:
            write_rows(client, base_url, service_key, "access_grants", grants)

    print(f"Seeded {len(users)} local demo identities and {len(chunk_rows)} source chunks.")
    print(f"Local-only credentials saved to {CREDENTIALS.name} (mode 600; git-ignored).")


if __name__ == "__main__":
    asyncio.run(main())
