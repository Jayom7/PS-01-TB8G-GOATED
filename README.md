# Clearframe — Secure Knowledge Workspace

Clearframe is the product identity for PS-01: a workspace for answering
questions from documents, images, and business records while keeping the
requester's identity attached to retrieval.

Canonical GitHub repository: [Jayom7/PS-01-TB8G-GOATED](https://github.com/Jayom7/PS-01-TB8G-GOATED).
The SSH remote was checked on 2026-10-08; the spelling without `01` was not accessible.

## Current implementation

- Next.js sign-in and a Supabase-authenticated workspace with Dashboard, Ask,
  Sources, Ingest, Security, and Evaluation views.
- Authenticated FastAPI chat, source lookup, workspace/security status, and
  evaluation results. Query evidence is retrieved with the user's token and
  database RLS; the API sends only those returned chunks to Gemini.
- Local demo identity switching uses the seeded role users and brokers a real role-scoped
  Supabase Auth session server-side while preserving the signed-in CEO identity. It is enabled only for loopback Supabase and
  the ignored `.local-demo-credentials.json` file.
- CEO-only local ingestion accepts PDFs, images, and structured JSON, creates
  Gemini embeddings, and persists documents/chunks and role grants. Original
  uploads are stored privately under ignored `data/private/ingest/`.
- Citation responses check model-context membership, exact supporting excerpts,
  coarse lexical overlap, a bounded paid/unpaid contradiction guard, and source location.
  Every quote must match its authorized passage; any unauthorized reference rejects the claim. These bounded deterministic
  checks do not prove semantic claim entailment. Empty evidence returns
  `INSUFFICIENT_EVIDENCE`.
- Evaluation runs the local retrieval cases and reports positive-query hit rate, rank,
  checked forbidden-source hits, retrieved citation-location presence, OCR, structured, cross-modal,
  and latency results. Results are saved locally and exposed to authenticated
  workspace users.

The configured generation path is Gemini 3.8 Flash primary and Gemini 3.7 Flash
fallback; Embedding 2 uses 1536 dimensions. Model IDs remain configurable.
HTTP 429 stops after one request rather than spending a fallback request.
Current local Docker/Supabase is running; both migrations are applied. The
lockfile-pinned CLI was restored with `npm ci`, and API/web were rebuilt and
restarted from this checkout. Fresh local pgTAP passed 24/24. Hosted Supabase
remains unverified. The latest real Ask attempt reached authorized retrieval,
but Gemini generation returned HTTP 503 after its fallback path; no fresh
successful answer or HR refusal is claimed. See `docs/PHASE1_VERIFICATION.md`
and `docs/REVIEW_NEEDED.md` for current evidence and limits.

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
.venv/bin/pip install -e 'apps/api[dev,ingestion]'
```

Then start local Supabase and seed the demo users/data:

```sh
PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" ./node_modules/.bin/supabase start
.venv/bin/python apps/api/scripts/seed_local_demo.py
.venv/bin/python apps/api/scripts/configure_local_web.py
```

Start the API and web app in separate terminals from the repository root:

```sh
.venv/bin/python apps/api/scripts/run_local_api.py
pnpm --dir apps/web build
pnpm --dir apps/web start --hostname 127.0.0.1 --port 3000
```

Open `http://localhost:3000` consistently; the API CORS origin uses that name.
The API launcher reads local Supabase CLI credentials, refuses remote URLs,
and binds to `127.0.0.1`. Install optional PDF/OCR dependencies with
`pip install -e 'apps/api[ingestion]'` from the repository root, or use the
setup documented in [API setup](apps/api/README.md).

Demo account passwords are generated on first seed and stored only in the
ignored, owner-readable `.local-demo-credentials.json` file. Read that file
locally when preparing the demo; do not paste its contents into chat or Git.
Do not use these local identities for a hosted project. The role
switcher preserves the signed-in CEO identity and resolves the selected context
to a real role-scoped session on the server; it does not edit authorization
with a client-side label.

See [API setup](apps/api/README.md), [demo plan](docs/DEMO_PLAN.md),
[implementation plan](docs/IMPLEMENTATION_PLAN.md), and
[review items](docs/REVIEW_NEEDED.md) for setup details and remaining proof
boundaries. Hosted migration, hosted RLS, hosted retrieval, and production
ingestion remain unverified; see the review file before using beyond the local
demo.

## Fresh local verification

With the local services running:

```sh
.venv/bin/pytest apps/api/tests -q
.venv/bin/ruff check apps/api/src apps/api/scripts apps/api/tests
.venv/bin/ruff format --check apps/api/src apps/api/scripts apps/api/tests
pnpm --dir apps/web lint
apps/web/node_modules/.bin/tsc --noEmit --incremental false -p apps/web/tsconfig.json
PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" ./node_modules/.bin/supabase test db
.venv/bin/python apps/api/scripts/run_local_demo.py
```

The final command verifies the running API without spawning another server or
reseeding. It refuses hosted API URLs and checks the synthetic corpus boundary
before real Gemini generation. Use `--skip-generation` for local-only checks;
that intentionally returns exit code 2 (incomplete), not success. Exit code 1
means failed checks; 0 means every required check passed. Timestamped reports
and the latest report live under ignored `data/local/security-verification*.json`.
No password or token is saved in those reports. Provider failure does not
replace historical evaluation results with invented values.
