# Clearframe — Secure Knowledge Workspace

Clearframe implements PS-01, a secure multimodal RAG workspace for NovaCore Industries. PDF pages, OCR regions, and relational records share an authorized vector/metadata index. The five demo roles are CEO, Finance Manager, HR Manager, Sales Manager, and Engineer.

Repository: [Jayom7/PS-01-TB8G-GOATED](https://github.com/Jayom7/PS-01-TB8G-GOATED). Existing SSH remote retained; no duplicate repository or hosted deployment.

## Current evidence — 2026-10-09

**VERIFIED LOCALLY:** 76 backend tests, Ruff check/format, frontend ESLint, TypeScript, and production build. Real local extraction produced 45 candidates from 19 synthetic sources: 8 PDF chunks, 30 image OCR regions, and 7 structured fixture records. These are extraction counts, not freshly persisted database counts.

**BLOCKED:** Docker engine is unavailable; local Postgres at 54322 refuses connections. The new additive migration, 43-assertion pgTAP suite, five-role live database checks, and clean end-to-end restart are not verified. Gemini model inventory returned HTTP 200 for configured 3.8 Flash and 3.7 Flash IDs, but one bounded synthetic generation attempt ended in HTTP 503 after the single fallback. No fresh successful answer, HR refusal, or live injection outcome is claimed. Hosted Supabase is **UNVERIFIED**.

Browser checks covered actual public login plus a separate, explicitly labeled UI fixture server for all six workspace routes, both themes, desktop/tablet/mobile, role controls, history, and evidence overlays. Fixture screenshots establish layout and interactions only. Previous database/provider results are **RECORDED BUT NOT FRESH**.

## Implementation

- Next.js 16 / Supabase Auth frontend; FastAPI verifies identity and forwards user or brokered demo-role sessions to the database.
- `match_knowledge_chunks` remains `SECURITY INVOKER`. RLS filters candidates before model context; ordinary retrieval never uses the service key.
- Seven typed business tables and owner-scoped query history are added by the new migration. Fixtures seed real rows; the seed rereads persisted rows before generating index text. Stale/deleted structured rows deny indexed evidence until reindexed.
- Gemini selects evidence IDs only. The backend renders canonical excerpts and source locations; fabricated text/quotes never become evidence. This verifies extractive provenance, not general entailment or relevance.
- Ask uses real operational SSE events and releases factual text only after validation. History replay reauthorizes and rebuilds answers from current evidence.
- Protected originals require document access. PDF page, OCR region overlay, and database fields are available in the evidence inspector. Timings belong in Retrieval Trace.
- CEO-only local ingestion handles PDF, PNG/JPEG, and typed records. Files are private; grants include the chosen role and CEO. No invented per-stage ingestion progress.

## Setup and startup

Install the existing lockfile dependencies once:

```sh
npm ci
pnpm --dir apps/web install --frozen-lockfile
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[dev,ingestion]'
```

Create ignored root `.env` from `.env.example` and configure the server-side Gemini key. Keep secrets out of `NEXT_PUBLIC_` variables. Start your existing Docker runtime, then:

```sh
./scripts/dev --seed
```

This starts local Supabase, applies additive local migrations without resetting data, configures ignored web public settings, seeds synthetic data, and launches API/web. Seeding can contact Gemini for embeddings. Later launches use `./scripts/dev` to reuse the seed. Supabase stays running when the launcher exits; it stops only the API/web processes it created.

Open `http://localhost:3000/login`. Use the local CEO account in ignored, owner-readable `.local-demo-credentials.json`; never display or commit that file. The browser remains signed in as CEO while the API brokers another seeded role session for the selected access context. Both launchers refuse hosted Supabase URLs.

## Verification

```sh
.venv/bin/pytest apps/api/tests -q
.venv/bin/ruff check apps/api/src apps/api/scripts apps/api/tests
.venv/bin/ruff format --check apps/api/src apps/api/scripts apps/api/tests
(cd apps/web && ./node_modules/.bin/eslint)
apps/web/node_modules/.bin/tsc --noEmit --incremental false -p apps/web/tsconfig.json
(cd apps/web && ./node_modules/.bin/next build --webpack)
./scripts/verify_demo
```

`verify_demo` checks service reachability, local Auth, typed tables/seed, history schema, pgTAP, then five-role retrieval/source checks and one bounded real generation flow. `--skip-generation` intentionally reports incomplete verification. Reports stay under ignored `data/local/`; failed checks never become successful metrics.

See [submission matrix](docs/SUBMISSION_MATRIX.md), [demo runbook](docs/DEMO_RUNBOOK.md), [final report](docs/FINAL_BUILD_REPORT.md), and [review boundaries](docs/REVIEW_NEEDED.md).
