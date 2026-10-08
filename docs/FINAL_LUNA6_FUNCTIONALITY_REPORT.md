> Historical record. Current implementation and verification: [FINAL_BUILD_REPORT.md](FINAL_BUILD_REPORT.md) and [REVIEW_NEEDED.md](REVIEW_NEEDED.md). The current manifest again contains 19 sources; older six-source notes do not describe this pass.

# Current Luna 6 Functional Pass Report

**Snapshot:** 2026-10-08. This is a bounded local implementation pass on the
existing Clearframe repository. It is not production-readiness or hosted
security certification.

## Changes in this pass

- Stops Gemini generation fallback on HTTP 429; adds a distinct safe error and
  an Ask-page retry action.
- Replaces hardcoded unauthorized-evidence zeroes with “not independently
  measured in this trace”. Dashboard Gemini status now means configured, and
  Security says its endpoint did not query RLS status.
- Requires exact supporting quotes per model claim/citation and applies
  deterministic exact-quote inclusion plus coarse lexical overlap checks
  before returning claims. It does not prove semantic entailment.
- Validates PNG/JPEG header dimensions before OCR and rejects images over
  16,000,000 pixels. UI reports one real indexing state without suggesting
  unreported per-stage progress.
- Adds a source-type filter alongside authorized source search; centralizes
  CSS color use in shared light/dark design tokens.
- Reconciles README, architecture/security/API/data/RAG/plan/review/design/demo
  docs, and adds judge/recording scripts.

## Verified in this pass

- Backend tests: **42 passed** (`apps/api/tests`).
- Ruff: passed (`apps/api/src`, `apps/api/tests`).
- Ruff format check: passed.
- Web ESLint: passed.
- TypeScript: passed using `apps/web/node_modules/.bin/tsc --noEmit -p apps/web/tsconfig.json`.
- Next.js production build: passed; six authenticated routes were included.
- `git diff --check`: passed after the final source and docs edits.
- Unit tests cover exact context/source membership, quote inclusion, unrelated
  quote rejection, oversized PNG rejection before OCR, JPEG dimension parsing,
  and no fallback request after a mocked 429.

These checks do not establish live Auth, current local database state, browser
role switching, current OCR engine behavior, or a live Gemini answer.

## Runtime and provider blockers

- Docker CLI is installed, but the current process cannot access
  `/Users/Jayom/.docker/run/docker.sock` (permission denied). Local Supabase
  could not be started or queried.
- Root declares Supabase CLI but `node_modules/.bin/supabase` points to a
  missing `node_modules/supabase/dist/supabase.js`. Run `npm ci` after Docker
  access is restored; the app must not silently use a remote database.
- No API/web server or authenticated browser session was started in this pass.
- Previous live Gemini attempts returned HTTP 429. No extra live request was
  made; one fresh successful answer, citation, and source preview are required
  after quota/access recovers.
- The ignored local demo credential file exists and contains five records, but
  passwords were not read into this report. Retrieve them locally from
  `.local-demo-credentials.json`; never commit or paste that file.
- Hosted Supabase remains unverified. Historical local migration/pgTAP and
  browser checks are described as such in `REVIEW_NEEDED.md`.

## Exact local startup sequence

Prepare dependencies once:

```sh
npm ci
pnpm --dir apps/web install --frozen-lockfile
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[ingestion]'
```

Start local database and seed (after Docker socket and CLI are available):

```sh
PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" ./node_modules/.bin/supabase start
.venv/bin/python apps/api/scripts/seed_local_demo.py
```

In separate terminals:

```sh
.venv/bin/python apps/api/scripts/run_local_api.py
pnpm --dir apps/web dev
```

Do not replace the local Supabase target with hosted credentials for the demo.
The API launcher is intended to reject remote URLs.

## Remaining priorities

### A. MUST FIX BEFORE DEMO

1. Restore Docker socket access and root Supabase CLI install; start local stack
   and run seed flow. Confirm local DB readiness and all six routes.
2. Re-run local pgTAP and API authorization tests; verify CEO identity remains
   fixed while changing Finance/HR context. Confirm HR gets insufficient
   evidence for the finance prompt and source preview remains authorized.
3. When Gemini quota/access is available, verify one actual finance answer,
   cited OCR source preview, and one HR denial. If provider returns 429, stop
   and do not use mock output.
4. Run fresh browser checks for login, direct route guards, all six views,
   light/dark, desktop/tablet/mobile, drawer, and no horizontal overflow.

### B. HIGH-VALUE IMPROVEMENTS

1. Make the local startup/dependency flow reproducible on a clean machine and
   retain a clear operator preflight for Docker, seed, API, web, and Gemini.
2. Inspect the real Ask path under restored runtime; measure auth, embedding,
   retrieval+ranking, generation, validation, and total. Current historical
   failures suggest model generation dominates; no fresh successful latency
   measurement exists.
3. Add systematic evaluator cases for exact quote and lexical-check false
   positives/negatives, plus prompt injection once provider is available.
4. Make current local Evaluation timestamp and corpus modality coverage
   visible only from real result data; keep the synthetic/small-sample labels.

### C. NICE TO HAVE

1. Add server-reported upload/job stage events if ingestion later becomes
   asynchronous; keep the current single honest indexing state until then.
2. Add source date/ingestion-state facets only if those fields are actually
   populated and authorization-safe.
3. Run screen recording using `SCREEN_RECORDING_SCRIPT.md` after the live
   preflight succeeds.

### D. SHOULD BE LEFT FOR A STRONGER MODEL

1. Hosted Supabase migration/RLS review and hosted allow/deny verification.
2. Filtered-HNSW recall/query-plan work at representative scale.
3. Semantic entailment methodology and adversarial safety evaluation beyond
   current quote/overlap heuristics.
4. Production review of role-session brokering, privileged ingestion,
   transaction rollback, storage lifecycle, observability, and rate limits.

Luna 6 can safely finish the remaining bounded local functional work when
Docker and provider access are available. A stronger model is appropriate for
the hosted-security, retrieval-research, and semantic-entailment items above;
those are intentionally not claimed as completed here.
