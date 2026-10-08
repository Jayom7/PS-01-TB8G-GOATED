# Clearframe API

FastAPI service for authenticated knowledge queries and source lookup.

## Current routes

- `GET /health` is liveness only.
- `POST /api/v1/chat/query` requires a Supabase bearer session. The API checks
  the session with Supabase Auth, creates a Gemini Embedding 2 vector, calls
  `match_knowledge_chunks` with the same user token, and sends only retrieved
  evidence to Gemini Flash.
- `GET /api/v1/sources/{citation_id}` uses the same user session to fetch an
  exact chunk. Missing and RLS-hidden rows share the same 404 response.

The body accepts only a `query`; client-supplied user, organization, role,
ACL, or evidence fields are rejected. Retrieval does not use
`SUPABASE_SECRET_KEY`. That credential is reserved for a future separately
authorized ingestion path and is not currently read by the query implementation.

## Local setup

From the repository root, copy `.env.example` to `.env`. The API loads that
file regardless of the launch directory. Start the API with:

```sh
python -m venv .venv
source .venv/bin/activate
cd apps/api
pip install -e '.[dev]'
uvicorn --app-dir src ps01_api.main:app --reload
```

The current RPC requires the migration at `supabase/migrations/`. It is not
applied or database-tested yet. Provider/network errors return generic safe
messages; secrets and raw prompts are not logged.
