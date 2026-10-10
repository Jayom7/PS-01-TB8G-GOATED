# Clearframe API

FastAPI service for authenticated queries, source access, local ingestion, and
workspace operations. For complete **Windows/WSL2 and macOS installation**, use
the [root README](../../README.md), including prerequisites, migrations, Gemini
configuration, OCR options, generated credentials and troubleshooting. Run its
commands from the repository root; starting this service alone does not seed
the database or launch the frontend.

## Routes

- `GET /health` — liveness check.
- `GET /api/v1/workspace` and `GET /api/v1/security` — current authenticated
  identity, role-scoped data counts, and recent request security traces.
- `POST /api/v1/chat/stream` — real operational SSE events with validated final output.
- `POST /api/v1/chat/query` — verifies the Supabase bearer session, embeds the
  question, calls `match_knowledge_chunks` with the same user token, and sends
  only RLS-returned evidence to Gemini. The request accepts a query, not a
  client-supplied identity, role, ACL, or evidence set.
- `GET /api/v1/sources`, `GET /api/v1/sources/{citation_id}`, and
  `GET /api/v1/sources/{document_id}/preview` — list and open only
  documents/chunks visible to the signed-in user. Hidden and missing source
  rows share the same 404 response.
- `GET /api/v1/evaluation` — local CEO-context read of recorded evaluation results;
  `POST /api/v1/evaluation/run` is CEO-only and local-demo-only.
- `POST /api/v1/demo/switch` — changes to a seeded role user's real Supabase
  Auth session. Available only for a loopback Supabase URL when the ignored
  `.local-demo-credentials.json` exists.
- `POST /api/v1/ingest/file` and `POST /api/v1/ingest/structured` — CEO-only
  ingestion for PDF/image files and structured JSON records. Local originals
  stay under ignored `data/private/ingest/`; explicitly configured hosted
  ingestion uses private Supabase Storage. File uploads are bounded to 25 MB.

Normal retrieval uses the caller's bearer token and RLS. The server-side
Supabase secret key is reserved for authorized administrative operations,
including CEO-gated ingestion and private original storage. Never expose it
to the web app or use it for ordinary retrieval. Local launch/seed scripts
refuse non-loopback Supabase URLs; hosted provisioning is separate and is not
a verified one-click deployment.

## Local setup

Follow the root README for first installation. After dependencies, local
configuration and Docker are ready, the complete first launch is:

```sh
./scripts/dev --seed
```

Use `./scripts/dev` for subsequent launches without reseeding. To launch only
the API against an already running, migrated local Supabase stack:

```sh
.venv/bin/python apps/api/scripts/run_local_api.py
```

The API launcher reads local Supabase settings privately from the CLI.
Credentials generated during initial seeding are stored in ignored
`.local-demo-credentials.json` with mode `600`. Initial seeding requires real
Gemini embeddings and successful OCR; a credentials file alone does not prove
the seed completed.

## Verification

Run the API checks with:

```sh
.venv/bin/ruff check apps/api/src apps/api/scripts apps/api/tests
.venv/bin/pytest apps/api/tests -q
./node_modules/.bin/supabase test db
```

The local evaluation runner exercises retrieval and authorization against the
seeded corpus:

```sh
.venv/bin/python apps/api/scripts/evaluate_local_retrieval.py
```

## Running-checkout security verification

Run `.venv/bin/python apps/api/scripts/run_local_demo.py` from the repository
root after starting the API/web. This checks all five local roles, forbidden
citation/document lookup, forged contexts, CEO identity preservation, and
honest Security labels. It requires the database documents to match the
fictional repository fixtures before attempting real Gemini generation.
`--skip-generation` leaves generation/source inspection and HR refusal blocked.
Exit codes: 0 complete pass, 1 failed checks, 2 incomplete/blocked checks.
Reports are saved only under ignored `data/local/`; no credentials are printed.

Evaluation schema 2 reports hit rate@12 over positive queries and retrieved
citation-location presence, not Recall@12 or semantic answer provenance.
Legacy saved files are relabeled as historical on read without being rerun.

Read-only readiness while the app runs:
`.venv/bin/python apps/api/scripts/verify_services.py`. The fuller
`./scripts/verify_demo` also runs database/integration checks and can contact
the provider. Typed-row origin, protected originals and conversation endpoints
are documented in [API_SPEC](../../docs/API_SPEC.md). Historical proof and
blockers remain in [FINAL_BUILD_REPORT](../../docs/FINAL_BUILD_REPORT.md).
