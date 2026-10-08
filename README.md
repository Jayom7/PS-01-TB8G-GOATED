# Clearframe — Secure Knowledge Workspace

Clearframe is the product identity for PS-01: a workspace for answering
questions from documents, images, and business records while keeping the
requester's identity attached to retrieval.

## Current implementation

- Next.js sign-in form backed by Supabase Auth and a server-side session gate
  for the workspace.
- FastAPI `POST /api/v1/chat/query` verifies the Supabase session, embeds the
  question with Gemini Embedding 2, calls the user-token-scoped
  `match_knowledge_chunks` RPC, and sends only the bounded returned evidence to
  Gemini Flash.
- Claims are returned only when their proposed citation IDs belong to the
  exact model context and have a supported source location. This validates
  citation membership and provenance, not semantic claim support; the API
  labels this `CITATION_VALIDATED`. An empty result becomes
  `INSUFFICIENT_EVIDENCE`.
- Citation lookup uses the same user token against `knowledge_chunks`.
- The frontend shows real session state, query states, source details, and
  honest setup states for areas that are not connected yet.

The migration has been applied to the local Supabase stack. Its 17 database
allow/deny tests and the local schema linter pass. The hosted project has not
been migrated because the Supabase CLI is not authenticated. Gemini embedding
and generation requests and Supabase Auth settings requests have succeeded
with the configured credentials. These checks do not validate the hosted
database or the full demo flow.

PDF text extraction, bounded OCR for scanned PDFs and images, and structured
record normalization are implemented as ingestion primitives. They are not
yet connected to an authenticated upload route or database persistence path.
Synthetic demo fixtures are in `data/demo/`.

## Local setup

Copy `.env.example` to the repository root as `.env` and replace the server
values. Copy `apps/web/.env.local.example` to `apps/web/.env.local`; that file
contains only the public Supabase URL/key and the API base URL. Both local files
are ignored by Git. Never place `GEMINI_API_KEY` or `SUPABASE_SECRET_KEY` in a
`NEXT_PUBLIC_` variable or the web env file.

```sh
cd apps/web
pnpm install
pnpm dev
```

```sh
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn --app-dir src ps01_api.main:app --reload
```

Install optional PDF/OCR dependencies with `pip install -e '.[dev,ingestion]'`.

See [API setup](apps/api/README.md), [implementation plan](docs/IMPLEMENTATION_PLAN.md),
and [review items](docs/REVIEW_NEEDED.md) for the current proof boundaries.
