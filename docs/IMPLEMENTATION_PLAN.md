# Implementation Plan and Current Checkpoint

This is the existing Next.js + FastAPI + Supabase implementation. Do not
re-scaffold it. This checkpoint describes repository state on 2026-10-08;
historical test evidence is called out separately in `REVIEW_NEEDED.md`.

## Implemented in the repository

- Six authenticated pages and Supabase Auth route protection.
- User-session retrieval/source lookup, local CEO-brokered demo contexts, and
  local CEO-gated ingestion.
- Hybrid PostgreSQL vector/full-text retrieval, PDF/OCR/structured ingestion,
  citation/source provenance, and a synthetic evaluation runner.
- Configurable Gemini REST adapters and bounded query context.
- Five demo roles: CEO, Finance Manager, HR Manager, Sales Manager, Engineer.
- Safe provider errors, configurable model fallback, and citation membership
  checking. The current pass adds quote-integrity/lexical checks.

## Current blockers

- Docker client exists, but this session cannot access the Docker API socket:
  `permission denied ... unix:///Users/Jayom/.docker/run/docker.sock`.
- Repo-local Supabase CLI executable is absent/broken despite a dependency
  declaration; `node_modules/.bin/supabase` does not resolve. The local database
  and clean end-to-end demo cannot be started here. Do not switch to a remote
  database as fallback.
- Gemini API quota/access was previously observed returning HTTP 429. This
  session did not spend another live provider request.
- Hosted Supabase CLI auth and hosted policy state remain unverified.

## Remaining order

1. Restore Docker socket access, install the repository-pinned JavaScript
   dependencies from the lockfile, verify local Supabase CLI, start local
   Supabase, run the seed command, and start the API/web using the documented
   commands in `README.md`.
2. Run the complete API suite, Ruff, web lint/typecheck/build, and browser checks
   across the six routes, roles, and responsive breakpoints.
3. Once provider quota/access is restored, verify one allowed finance answer,
   exact citation/source preview, and HR insufficient-evidence result. Avoid
   repeated retries when 429 persists.
4. Repeat local pgTAP/schema checks only after the local database starts. Hosted
   state requires its own separately authorized credentials and review.
5. Address the deeper items in `REVIEW_NEEDED.md`: hosted RLS review, filtered
   HNSW benchmarks/query plans, semantic entailment methodology, provider
   resilience, and production ingestion/storage review.

## Scope boundary

The product is a local hackathon demo slice, not production-ready. Do not
weaken authorization or replace the stack to bypass unavailable infrastructure.
