# Clearframe API

FastAPI service for authenticated queries, source access, local ingestion, and
workspace operations.

## Routes

- `GET /health` — liveness check.
- `GET /api/v1/workspace` and `GET /api/v1/security` — current authenticated
  identity, role-scoped data counts, and recent request security traces.
- `POST /api/v1/chat/query` — verifies the Supabase bearer session, embeds the
  question, calls `match_knowledge_chunks` with the same user token, and sends
  only RLS-returned evidence to Gemini. The request accepts a query, not a
  client-supplied identity, role, ACL, or evidence set.
- `GET /api/v1/sources`, `GET /api/v1/sources/{citation_id}`, and
  `GET /api/v1/sources/{document_id}/preview` — list and open only
  documents/chunks visible to the signed-in user. Hidden and missing source
  rows share the same 404 response.
- `GET /api/v1/evaluation` — authenticated read of current evaluation results;
  `POST /api/v1/evaluation/run` is CEO-only and local-demo-only.
- `POST /api/v1/demo/switch` — changes to a seeded role user's real Supabase
  Auth session. Available only for a loopback Supabase URL when the ignored
  `.local-demo-credentials.json` exists.
- `POST /api/v1/ingest/file` and `POST /api/v1/ingest/structured` — CEO-only
  local-demo ingestion for PDF/image files and structured JSON records.
  Uploads are bounded to 25 MB and originals are stored privately under
  ignored `data/private/ingest/`.

Normal retrieval uses the caller's bearer token and RLS. The server-side
Supabase secret key is used only by local CEO-gated ingestion, after the local
launcher confirms that Supabase URL is loopback. Do not expose it to the web
app or use this local flow against a hosted database.

## Local setup

From the repository root, install API dependencies and optional document
parsers:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e 'apps/api[dev,ingestion]'
```

Create `.env` from `.env.example` for the Gemini server key. Start Docker
Desktop, then Supabase with
`PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" ./node_modules/.bin/supabase start`;
the local API launcher obtains the
local Supabase URL and keys directly from the CLI without displaying them,
refuses remote URLs, then binds FastAPI to `127.0.0.1:8000`:

```sh
.venv/bin/python apps/api/scripts/run_local_api.py
```

Seed local demo data and accounts with
`.venv/bin/python apps/api/scripts/seed_local_demo.py`. Credentials are stored
in the ignored `.local-demo-credentials.json` file with mode `600`.

## Verification

Run the API checks with:

```sh
.venv/bin/ruff check apps/api/src apps/api/scripts apps/api/tests
.venv/bin/pytest apps/api/tests -q
PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" ./node_modules/.bin/supabase test db
```

The local evaluation runner exercises retrieval and authorization against the
seeded corpus:

```sh
.venv/bin/python apps/api/scripts/evaluate_local_retrieval.py
```
