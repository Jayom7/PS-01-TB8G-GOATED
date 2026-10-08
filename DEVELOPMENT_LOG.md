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

- Install GitHub CLI and authenticate with `gh auth login` before creating the
  private GitHub repository and pushing.
- Install Docker Desktop (or another Docker-compatible runtime) before using
  Supabase local development or Docker-based integration checks.
- Supply Gemini and Supabase project credentials before live provider/database
  integration; no actual provider credentials were inspected. The example file
  now contains blank values only.
