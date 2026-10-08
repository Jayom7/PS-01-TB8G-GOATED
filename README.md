# Clearframe — Secure Knowledge Workspace

Clearframe is the product identity for PS-01: a workspace for answering
questions from documents, images, and business records while keeping the
requester's identity attached to retrieval.

## Current implementation

- Next.js sign-in and a Supabase-authenticated workspace with Dashboard, Ask,
  Sources, Ingest, Security, and Evaluation views.
- Authenticated FastAPI chat, source lookup, workspace/security status, and
  evaluation results. Query evidence is retrieved with the user's token and
  database RLS; the API sends only those returned chunks to Gemini.
- Local demo identity switching uses the seeded role users and changes the
  actual Supabase Auth session. It is enabled only for loopback Supabase and
  the ignored `.local-demo-credentials.json` file.
- CEO-only local ingestion accepts PDFs, images, and structured JSON, creates
  Gemini embeddings, and persists documents/chunks and role grants. Original
  uploads are stored privately under ignored `data/private/ingest/`.
- Citation responses check model-context membership, exact supporting excerpts,
  coarse lexical overlap, and source provenance. These bounded deterministic
  checks do not prove semantic claim entailment. Empty evidence returns
  `INSUFFICIENT_EVIDENCE`.
- Evaluation runs the local retrieval cases and reports recall, rank,
  authorization violations, citation provenance, OCR, structured, cross-modal,
  and latency results. Results are saved locally and exposed to authenticated
  workspace users.

The configured generation path is Gemini 3.8 Flash primary and Gemini 3.7 Flash
fallback; Embedding 2 uses 1536 dimensions. Model IDs remain configurable.
HTTP 429 stops after one request rather than spending a fallback request.
Previous local migration, pgTAP, browser, and evaluation results are
historical; see `docs/REVIEW_NEEDED.md`. In this session Docker is installed but
the API socket returns permission denied, and the repo-local Supabase CLI
executable is absent. Hosted Supabase remains unverified. Earlier real Gemini
queries returned 429, and no fresh answer has been verified in this pass.

## Local setup

Copy `.env.example` to the repository root as `.env` and replace the server
values. Copy `apps/web/.env.local.example` to `apps/web/.env.local`; that file
contains only the public Supabase URL/key and API base URL. Both local files
are ignored by Git. Never place `GEMINI_API_KEY` or `SUPABASE_SECRET_KEY` in a
`NEXT_PUBLIC_` variable or the web env file.

First ensure Docker Desktop is running and accessible, and install the
repo-pinned dependencies from both lockfiles:

```sh
npm ci
pnpm --dir apps/web install --frozen-lockfile
```

Create the local API environment once if needed and install the optional
ingestion dependencies:

```sh
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[ingestion]'
```

Then start local Supabase and seed the demo users/data:

```sh
PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" ./node_modules/.bin/supabase start
.venv/bin/python apps/api/scripts/seed_local_demo.py
```

Start the API and web app in separate terminals:

```sh
.venv/bin/python apps/api/scripts/run_local_api.py
pnpm --dir apps/web dev
```

The API launcher reads local Supabase CLI credentials, refuses remote URLs,
and binds to `127.0.0.1`. Install optional PDF/OCR dependencies with
`pip install -e 'apps/api[ingestion]'` from the repository root, or use the
setup documented in [API setup](apps/api/README.md).

Demo account passwords are generated on first seed and stored only in the
ignored, owner-readable `.local-demo-credentials.json` file. Read that file
locally when preparing the demo; do not paste its contents into chat or Git.
Do not use these local identities for a hosted project. The role
switcher exchanges the signed-in local account for one of those real Auth
sessions; it does not edit a client-side role label.

See [API setup](apps/api/README.md), [demo plan](docs/DEMO_PLAN.md),
[implementation plan](docs/IMPLEMENTATION_PLAN.md), and
[review items](docs/REVIEW_NEEDED.md) for setup details and remaining proof
boundaries. Hosted migration, hosted RLS, hosted retrieval, and production
ingestion remain unverified; see the review file before using beyond the local
demo.
