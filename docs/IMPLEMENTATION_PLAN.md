# Implementation Plan

Build the vertical slice on the existing Next.js, FastAPI, and Supabase
foundation. Do not replace the architecture.

## Current checkpoint

- Next.js sign-in and server-side route gate use Supabase Auth.
- FastAPI query and citation routes validate the session and use the same user
  token for database requests.
- Gemini Embedding 2 and structured Gemini Flash adapters are implemented.
- Claim validation binds each citation to the bounded evidence objects passed
  to generation; unsupported citations fail closed.
- Six focused RAG unit tests pass. Web lint and production build pass.
- The database migration remains unapplied. Live Supabase/Gemini checks failed
  at DNS resolution, and the Python runtime dependencies could not be
  installed because package download DNS failed.

## Remaining phases

1. **Database and authorization:** install/use Supabase CLI and Docker; validate
   the current migration, add the required business schema and synthetic
   records, apply it only after validation, then run database-backed allow and
   deny tests.
2. **Ingestion:** implement page-aware PDF extraction, OCR for images with
   provenance, structured row normalization, private source preservation, and
   an explicitly authorized transactional write path.
3. **Demo identity:** create CEO, Finance, HR, Sales, and Engineer Supabase
   users and switch between actual sessions in demo-only mode.
4. **Complete product surfaces:** connect Overview, Knowledge, Ingestion,
   Security, and Evaluation to real API/database state; do not fabricate
   metrics or seed results as live data.
5. **End-to-end proof:** run the four Acme query flows, finance allow, HR deny,
   prompt attack denial, citation lookup, and exact model-context tests against
   the applied database and real providers.
6. **Delivery:** repeat dependency install, backend tests, frontend lint and
   typecheck/build, migration checks, update this file and
   `REVIEW_NEEDED.md`, then set up GitHub after `gh` is installed and
   authenticated.

## Deferred review

Filtered HNSW recall, security-definer concerns, role/tenant edge cases, and
performance/concurrency review remain documented in `REVIEW_NEEDED.md` for the
stronger security pass.
