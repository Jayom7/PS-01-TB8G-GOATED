# PS-01 — Secure Multi-Modal RAG

Competition prototype for Atmiya University Code Carnival 3.0. The goal is a
single retrieval path over PDF text, image OCR, and structured records, with
authorization applied before evidence can enter a model prompt and exact,
validated source references in answers.

**Current state:** architecture and security contracts are being established.
No application services, migrations, demo data, or automated test results
exist yet. Architecture choices in `docs/` are planned until implemented and
verified.

## Architecture

- Next.js, TypeScript, and Tailwind for the judge-facing web app.
- FastAPI and Pydantic for the API and ingestion/retrieval services.
- Supabase PostgreSQL with pgvector and full-text search for one unified
  `knowledge_chunks` retrieval surface.
- Supabase Auth identities and user-scoped database requests; end-user
  retrieval must not use the service-role credential.
- Gemini Embedding 2 at a configurable 1536 dimensions and Gemini 3.8 Flash
  as current stable starting defaults. Both are configuration, not code-level
  dependencies on one provider.
- PyMuPDF for PDF text and a local OCR adapter for images/scanned pages.

See [the architecture](docs/ARCHITECTURE.md), [security model](docs/SECURITY_ARCHITECTURE.md),
and [implementation plan](docs/IMPLEMENTATION_PLAN.md). These documents are
design contracts, not evidence that the system is already secure or functional.

## Setup

The application scaffold has not been created yet. For credentials, copy
`.env.example` to `.env` and supply real values locally; never commit `.env`.
The Supabase service-role key is restricted to future administrative ingestion
work and must never be sent to a browser or used for ordinary user retrieval.

## Verification

There are currently no application tests, database migrations, or builds to
run. Verification results will be recorded in `DEVELOPMENT_LOG.md` as each
vertical slice is implemented.

## Demo data

The planned demo uses synthetic NovaCore Industries data only. Do not place
private, customer, or otherwise restricted source data in this repository.
