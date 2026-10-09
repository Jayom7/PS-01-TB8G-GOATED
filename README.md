# Clearframe — Secure Knowledge Workspace

Clearframe implements PS-01, a secure multimodal RAG workspace for NovaCore Industries. PDF pages, OCR regions, and relational records share an authorized vector/metadata index. The five demo roles are CEO, Finance Manager, HR Manager, Sales Manager, and Engineer.

Repository: [Jayom7/PS-01-TB8G-GOATED](https://github.com/Jayom7/PS-01-TB8G-GOATED). Existing SSH remote retained; no duplicate repository or hosted deployment.

## Current evidence — 2026-10-09 acceptance pass

**VERIFIED LOCALLY:** 79 backend tests, Ruff check/format, frontend ESLint, TypeScript, production build, 43/43 local pgTAP assertions, and 50 live authorization/source checks. The documented launcher runs local Supabase, API and web. All three local migrations are applied. The real persisted corpus contains 19 sources, 45 embedded chunks and 7 typed relational rows; five role sessions and protected PDF/OCR/record previews work.

**LIVE ANSWERS BLOCKED:** A full `./scripts/verify_demo` attempt reached Gemini HTTP 503 after the configured fallback. A subsequent bounded raw diagnostic returned HTTP 429 `RESOURCE_EXHAUSTED`: the `gemini-3.8-flash` free-tier generation request limit was 20, with a reported retry interval of 22h 48m 46s. Embeddings worked; no fresh successful generated answer, answer-citation audit, HR generated refusal or live injection outcome is claimed. The latest `--skip-generation` run intentionally exits 2: 50 checks passed and 2 generation checks were blocked. Hosted Supabase was untouched and remains unverified.

All six real authenticated routes were inspected at 1440×900, 820×900 and 390×844 in light/dark modes. Live role switching, source filtering/sorting, protected previews, overlay closing/focus, account/logout controls, empty history and draft reset were exercised. Fresh images in `docs/design/live-*.png` show the real app. Populated answer/history/trace states remain blocked. Older fixture screenshots and provider results are historical.

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
