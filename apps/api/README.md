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

The migration at `supabase/migrations/` is applied to the local Supabase stack.
The local pgTAP suite passes 17 authorization, retrieval, and schema checks;
`supabase db lint --local` reports no schema errors. The hosted project is not
migrated because Supabase CLI authentication is missing. Provider/network
errors return generic safe messages; secrets and raw prompts are not logged.

PDF text, scanned PDF and image OCR, and structured-record normalization are
available as ingestion primitives. The local seed tool embeds and persists the
synthetic fixtures with role ACLs; this is a developer tool, not a user upload
route. There is no private original-file storage or background ingestion job.
Install optional parser dependencies with `pip install -e '.[dev,ingestion]'`.

## Local demo

Start the Docker-backed local Supabase stack, then seed the synthetic corpus
and five role users:

```sh
./node_modules/.bin/supabase start
.venv/bin/python apps/api/scripts/seed_local_demo.py
.venv/bin/python apps/api/scripts/evaluate_local_retrieval.py
```

The seed tool refuses non-loopback Supabase URLs. It saves local passwords to
`.local-demo-credentials.json`, which is git-ignored and mode `600`.
`configure_local_web.py` points the ignored Next.js env file to local
Supabase; `run_local_api.py` launches FastAPI with the local project URL and
public key. Start the UI with `pnpm --dir apps/web dev`. The full Gemini
generation flow is exercised with
`.venv/bin/python apps/api/scripts/run_local_demo.py`; temporary provider 503s
are reported as incomplete demo runs.
