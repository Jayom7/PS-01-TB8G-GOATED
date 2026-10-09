# Clearframe — Secure Knowledge Workspace

Clearframe is the PS-01 multimodal RAG product. NovaCore Industries is its fictional demo tenant. PDF pages, real OCR regions and seven typed PostgreSQL business tables share a pgvector/metadata index with retrieval-time RLS.

## Current acceptance — 2026-10-09

**Verified locally:** 103 backend tests, 5 session/redirect tests, 55 pgTAP assertions, Ruff/format, frontend lint/types/build and 51 live authorization/refusal checks. Five local migrations are applied. Fresh browser PDF/OCR/invoice workflows passed 29 checks and 22 deletion checks; the resume added 30 real deletion/generated-history/cleanup checks. The retained corpus is 19 sources, 45 chunks and 7 typed rows. Six routes passed both themes at four sizes (48 combinations), with 8 additional populated Ask checks.

**Real Gemini success:** the browser returned the scanned USD 48,000 amount and contract terms using `gemini-3.8-flash`; the normal API returned fresh PDF/database answers using the configured `gemini-3.7-flash` fallback. A real API integration with a deliberately interrupted primary request produced all three source types through the real fallback, verified previews, and captured outbound IDs against Finance RLS visibility. Generated history survived reload/API restart and deleted-source claims were removed on replay.

**Remaining blocker:** availability is intermittent: both configured models still returned 503/timeouts on some normal cross-modal requests and the latest full verifier. Fresh OCR-specific generation remains incomplete. Google completion needs private operator configuration; actual password change requires user handoff. See [the acceptance checklist](docs/MASTER_ACCEPTANCE_CHECKLIST.md) for exact scopes and all unfinished checks. No hosted Supabase, credentials, billing or provider changes were made.

Ask preserves the submitted question on failure, offers retry and authorized source inspection, and renders one real SSE stage. Real helper and generated OCR/contract conversation persistence were verified across browser refresh and an actual API restart. Local recovery email → PKCE callback → reset form works without changing the account password. Google is explicitly unavailable until configured.

## Boundaries and behavior

- Ordinary reads use verified caller/broker JWTs and SECURITY INVOKER/RLS. Demo contexts are bound to actor, organization and role and rechecked on reuse; only the explicitly seeded local CEO can broker them.
- Every provider attempt rechecks the actor and current authorized source state. An external request cannot atomically span concurrent revocation; already viewed/sent bytes cannot be recalled.
- Gemini selects canonical passage IDs; trusted policy uses systemInstruction. Server-owned passages and bounded business summaries reject unknown IDs, model text/quotes, unrelated/poisoned selections and bounded invoice contradictions. These checks do not prove general semantic entailment.
- CEO local ingestion and transactional source deletion are separated from retrieval. A durable cleanup job removes private upload originals; immutable seed files remain on disk but become inaccessible if their source is deleted. Referenced business parents return a safe conflict.
- Conversations reauthorize/reconstruct current evidence on replay. Security events persist metadata only and are scoped to the real actor/organization/context.
- The local launcher uses a native Next same-origin API rewrite to avoid cross-origin browser request failures. FastAPI continues to enforce bearer authentication; production may configure its existing public API URL.

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
node --experimental-strip-types --test apps/web/tests/session.test.mjs
(cd apps/web && ./node_modules/.bin/eslint)
apps/web/node_modules/.bin/tsc --noEmit --incremental false -p apps/web/tsconfig.json
(cd apps/web && ./node_modules/.bin/next build --webpack)
./scripts/verify_demo
```

`verify_demo` checks service reachability, local Auth, typed tables/seed, history schema, pgTAP, then five-role retrieval/source checks and one bounded real generation flow; the HR zero-evidence refusal runs independently. `--skip-generation` intentionally reports incomplete verification. Reports stay under ignored `data/local/`; failed checks never become successful metrics.

See [submission matrix](docs/SUBMISSION_MATRIX.md), [demo runbook](docs/DEMO_RUNBOOK.md), [final report](docs/FINAL_BUILD_REPORT.md), and [review boundaries](docs/REVIEW_NEEDED.md).
