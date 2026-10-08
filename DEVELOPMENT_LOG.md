# Development Log

## 2026-10-08 — Architecture foundation

- Inspected the project directory: it was empty and had no Git repository,
  dependencies, application code, migrations, or tests.
- Recorded the first architecture and security contracts under `docs/` before
  creating application code.
- Current official Google documentation lists `gemini-3.8-flash` as a stable
  Flash model and `gemini-embedding-2` as a stable multimodal embedding model;
  the latter recommends 768, 1536, or 3072 dimensions. Set 1536 as a
  configurable starting point, subject to API/project availability checks.
- Supabase documents selective-filter recall risks for HNSW and iterative
  scans in pgvector 0.8.0+. Retrieval SQL and authorization behavior remain
  unimplemented and require tests before any security claim.
- Environment inspected: Git 2.54.0, Node 24.13.0, npm 11.6.2, pnpm 11.25.0,
  Python 3.14.2; Docker and GitHub CLI (`gh`) are not installed.
- No dependencies, credentials, remote repository, commit, migration, or test
  were created/executed in this initial architecture step.
- Initialized local Git and created first commit `3307dc5` after a narrow
  workspace permission escalation; repository has no remote yet.
- Generated desktop, denial-state, and mobile UI design references under
  `docs/design/` and recorded implementation tokens in `docs/UI_DESIGN.md`.
  The Superdesign CLI preflight remained silent for about a minute and was
  stopped; no Superdesign canvas draft was created. Image concepts contain
  inconsistent synthetic finance figures, so they are not canonical data.
- Official Next.js docs confirm App Router support and current TypeScript,
  ESLint, and Tailwind setup; Supabase local stack requires Docker-compatible
  runtime. No frontend/backend scaffold or package install has been started.

## 2026-10-08 — Web workspace preview

- Scaffolded `apps/web` with Next.js 16.4.0, React 19.3.0, Tailwind 4.3.3,
  TypeScript, and ESLint using the official Next.js generator. Package versions
  were read from the generated manifest/lockfile.
- Implemented an accessible three-panel workspace with responsive navigation,
  a mobile evidence sheet, citations that open source details, preview identity
  switching, and truthful empty states for Sources/Ingestion/Evaluation.
- The chat answer and two sources are synthetic local preview data. The UI
  visibly states that authentication, authorization, retrieval, and model calls
  are not connected; changing the preview identity is not an auth boundary.
- `pnpm lint` passed. `pnpm build` passed via `next build --webpack`, including
  TypeScript and static route generation. Default Turbopack build failed when
  its worker tried to bind a local port under this environment; the supported
  Webpack build option is now the package script. Default Turbopack development
  mode served and hydrated successfully. Webpack development mode emitted a
  Next client runtime error and is not used.
- Browser inspection confirmed the answer/citation/source interactions and
  that the HR preview shows no finance source names, IDs, or counts. Mobile
  layout was visually inspected in the narrow in-app browser. No backend,
  database, auth, ingestion, or retrieval tests exist yet.
- GitHub CLI and Docker are still unavailable; no remote repository, database,
  credentials, or live provider integration was created.

## 2026-10-08 — API and database foundation draft

- Added a FastAPI health-only service skeleton with typed environment settings.
  It has no authenticated query or ingestion route yet.
- Added an ordered SQL migration for one PDF/image-OCR/structured chunk index,
  HNSW and full-text indexes, subject/role/organization grants, RLS policies,
  and an invoker hybrid retrieval RPC. This migration is a draft and has not
  been applied to PostgreSQL.
- The database policies and candidate query are not verified. No database
  allow/deny tests, filtered-HNSW recall measurements, or query plans exist.
  Deeper RLS review remains an explicit blocker before relying on this design.
- Replaced a credential-shaped value in `.env.example` with an empty value and
  amended the unpushed initial commit. No remote is configured. The previous
  local commit object was pruned. If that value was a live provider key, rotate
  it in the provider account.
- Python packages, the API service, Supabase CLI/local stack, and migration
  runner have not been installed or executed in this phase.
- `python3 -m compileall -q apps/api/src` passed. `pnpm lint` and
  `pnpm build` passed again after the foundation edits. These checks do not
  validate runtime FastAPI dependencies or PostgreSQL migration behavior.

## Open setup items

- Authenticate the Supabase CLI and link the existing hosted project before
  applying the migration there. The local project migration and 17 pgTAP tests
  pass; the hosted schema remains unverified.

## 2026-10-08 — Current local build and presentation handoff

- Re-audited the working tree, implementation, test suite, current docs, and
  local runtime prerequisites before continuing. Earlier log entries are
  historical snapshots, not assertions about the runtime in this session.
- The current Docker client cannot access
  `/Users/Jayom/.docker/run/docker.sock` (permission denied); the root
  `node_modules/.bin/supabase` link has no package target. Therefore this pass
  did not start the local database, API, or authenticated web demo. Hosted
  endpoints were not substituted.
- Gemini model settings remain configurable: 3.8 Flash primary, 3.7 Flash
  fallback, Embedding 2 at 1536 dimensions. The code now stops on generation
  HTTP 429 after one request, returns a rate-limit-specific code/message, and
  the Ask page offers a retry action. No new live provider request was made.
- Security status and traces no longer return/display an unmeasured zero for
  unauthorized evidence. Gemini dashboard state means configured, not live
  availability. RLS status now explicitly says that endpoint did not check it.
- Claim output now requires a supporting quote per citation. Deterministic
  validation checks quote inclusion and coarse lexical overlap in addition to
  membership/location; tests cover absent/incorrect and unrelated quotes. This
  is not semantic entailment proof.
- PNG/JPEG header dimensions are checked before OCR and constrained to 16M
  pixels. Ingest UI now reports one real indexing state instead of implying
  per-stage progress.
- Updated current architecture, security, API, data model, implementation,
  decisions, review, and demo docs. Added judge and screen-recording scripts.
- Verification of this modified tree: 40 API tests passed; Ruff passed; web
  ESLint passed; direct project TypeScript check passed; Next.js production
  build passed. No browser auth, live data, Supabase migration, OCR engine, or
  Gemini generation check was performed in this pass.

## 2026-10-08 — Authenticated query slice

- Added Supabase password sign-in, a server-side `getClaims()` route gate, and
  sign-out. The query request schema rejects extra identity, role, organization,
  ACL, or evidence fields.
- Added FastAPI query and source-lookup routes. Authentication is checked with
  Supabase Auth; retrieval and source lookup forward the same user bearer token
  with the publishable key. The secret key is not used by these paths.
- Added Gemini Embedding 2 and structured Gemini Flash REST adapters, bounded
  model context, server-constructed citations, and fail-closed claim
  validation. The embedding REST response shape was checked against the
  [official Gemini API reference](https://ai.google.dev/api/embeddings).
- Replaced the hackathon preview UI with the Clearframe identity, real
  session-aware Ask surface, citation lookup, and honest setup states. The
  role switch remains absent until seeded users and real session switching
  exist. Added a new design concept at `docs/design/workspace-clearframe.png`.
- Normalized ignored `apps/web/.env.local` to the public Supabase pair plus
  `NEXT_PUBLIC_API_BASE_URL`; server-only keys remain in the ignored root
  `.env`. No values were printed or committed.
- Verification: six standard-library RAG unit tests passed; Python source
  compilation and `git diff --check` passed; `pnpm lint` and
  `pnpm build` passed. Browser inspection showed the sign-in form and verified
  an unauthenticated request to `/` redirects to `/login`.
- Blockers: the API dependency install failed resolving the package index;
  Supabase and Gemini provider checks also failed DNS resolution. Docker,
  Supabase CLI, and `gh` are missing. No migration, live auth, provider call,
  database allow/deny test, ingestion flow, or GitHub setup was verified.

## 2026-10-08 — Local secure retrieval and ingestion verification

- Verified GitHub SSH access with `git ls-remote`; Docker Desktop and the local
  Supabase stack are running. Supabase CLI is available locally, but its hosted
  project access token is not configured.
- Applied the existing migration to local Supabase. All 17 pgTAP tests passed,
  covering RLS/grants, authenticated RPC access, finance allow, HR denial,
  source visibility, and cross-organization isolation. `supabase db lint
  --local` reported no schema errors.
- Installed API development and optional ingestion dependencies in ignored
  `.venv`. Twenty-four API/RAG/ingestion tests passed. The API started locally
  and `/health` returned `{"status":"ok"}`. Ruff and Python compilation passed.
- Verified Supabase Auth settings requests and Gemini model resource requests.
  A real Gemini embedding returned 1536 dimensions, and structured generation
  succeeded. No key or embedding data was printed or persisted.
- Implemented bounded PDF extraction, scanned-page and image OCR, and
  structured-record normalization with source provenance. PaddleOCR was run
  on the synthetic invoice scan and detected its amount with page/region
  metadata. Added fictional, reproducible demo documents and records.
- Hosted Supabase migration remains blocked by missing CLI authentication or
  database credentials. No hosted data/users were modified or created.
- Seeded five local demo accounts, role grants, eight synthetic source
  documents, 16 extracted chunks, and 1536-dimensional Gemini embeddings.
  Stored local-only passwords in ignored `.local-demo-credentials.json` and
  configured the ignored web env file to use local Supabase/FastAPI.
- Retrieval evaluation on the five-case synthetic set measured Recall@12 1.0,
  MRR 0.775, and zero forbidden-source hits. This is a small smoke set, not a
  representative benchmark.
- The full generation demo reached a successful invoice query during one
  attempt, but subsequent requests received Gemini HTTP 503 `UNAVAILABLE`
  (“high demand”). The multi-query answer/citation demo remains incomplete
  until that provider endpoint recovers.

## 2026-10-08 — Final implementation and production browser pass

- Added direct protected routes for Dashboard, Ask, Sources, Ingest, Security,
  and Evaluation; refreshed local seed corpus to 19 sources, 45 chunks, and 7
  structured records; and made local role switching exchange actual Auth
  sessions. Seeded credentials remain only in ignored owner-readable storage.
- The old local API and Next dev processes served stale code. Restarted only
  those local runtimes, built the production web bundle, and verified the
  production server; protected dashboard, all six route destinations, source
  listing, and authorized source preview worked. Browser auth and CEO-to-HR
  switching worked; the HR dashboard showed 3 sources/8 chunks/1 record and
  finance queries returned insufficient evidence.
- Expanded the local pgTAP suite from 17 to 24 assertions. CEO, Finance, HR,
  Sales, and Engineer scope tests, source lookup denial, and forged org-claim
  checks passed. API suite: 32 passed. Ruff, frontend ESLint, TypeScript, and
  the normal production build passed.
- Production browser verification at 320px and 1440px included dashboard,
  routes, sources drawer, dark/light theme, role switch, finance denial, and a
  user-query prompt-injection denial. Evaluation reported Recall@12 1.000,
  MRR 0.775, six checks, and zero authorization leaks.
- One live Gemini scanned-invoice answer succeeded with a validated OCR source
  citation using the fallback model. Other contract, invoice-status,
  cross-modal, and document-injection requests hit timeout, malformed output,
  or unavailable-provider responses. The multi-query AI path is still
  unstable; citation validation is not semantic claim support.
- Hosted Supabase remains untouched because the Supabase CLI has no access
  token. `gh` is unavailable. Do not infer hosted correctness or a GitHub push
  from local test results.

## 2026-10-09 — Final scoped build and visual pass

Preserved the existing Next.js/FastAPI/Supabase invoker architecture. Added backend-owned canonical evidence IDs, conservative extractive answers, cross-modal invoice conflict checks, typed relational origin, restrictive stale-record denial, protected originals, real operational SSE, and actor/org/context history with current-evidence replay. Restored the full 19-source synthetic manifest and added local startup/readiness tooling.

The visual pass aligned the six-route shell, Ask/history/composer, source/trace drawers, structured fields, OCR original/overlay, source search/type/sort, ingestion validation, and recorded Evaluation states. Fixed focus return/trapping, mobile source actions, late-request races, duplicate labels/errors, and invisible refresh/run failures. Isolated labeled fixtures were used for protected-route visual checks; they were not live security/provider evidence.

VERIFIED LOCALLY: 76 backend tests, Ruff check/format, ESLint, TypeScript, production build, shell syntax, actual extraction of 45 candidates (8 PDF, 30 OCR, 7 structured) from 19 sources, and public login rendering. BLOCKED: new SQL/43 pgTAP assertions, live Auth/RLS/typed/history persistence and full restart because Docker/local Supabase is unavailable. Gemini inventory returned HTTP 200 for configured model IDs; one bounded generation request/fallback ended HTTP 503. Hosted Supabase and general semantic entailment remain UNVERIFIED. See FINAL_BUILD_REPORT, SUBMISSION_MATRIX, REVIEW_NEEDED, and DEMO_RUNBOOK for current boundaries.
