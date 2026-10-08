# Architecture Decisions

This file retains the design rationale from the initial scaffold. The choices
below are now implemented in the repository; that does not imply that hosted
deployment or production readiness is verified. Current proof limits are in
`REVIEW_NEEDED.md`.

## D-001 — One unified chunk index

**Decision:** PDF, OCR, and structured evidence share `knowledge_chunks` and
the `match_knowledge_chunks` RPC.

**Status:** migration and ingestion adapters implement this model; local
database evidence is historical and hosted operation is unverified.

## D-002 — Database-enforced user retrieval

**Decision:** ordinary queries use a user-scoped database identity and RLS;
the secret key is reserved for the separate local CEO-gated ingestion writer.

**Reason:** filtering in the API after privileged retrieval does not satisfy
the requirement. The RPC is invoker-security; local RLS results are recorded
separately from hosted verification.

## D-003 — PostgreSQL with pgvector and full text

**Decision:** Supabase PostgreSQL is the initial persistence and unified
retrieval store, with pgvector cosine search and PostgreSQL full-text search.

**Reason:** one relational transaction and policy boundary covers source
metadata, grants, and embeddings in this demo; this is not a scale benchmark.

## D-004 — HNSW is a measured starting point

**Decision:** begin with HNSW and measure filtered recall and plans before
acceptance. Verify extension version and iterative-scan configuration.

**Reason:** approximate search is practical, but Supabase documents that
selective filters may return fewer than requested unless scans continue.
See [Supabase HNSW guidance](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes).

## D-005 — Configurable Gemini defaults

**Decision:** use configurable Gemini Embedding 2 at 1536 dimensions, Gemini
3.8 Flash primary, and Gemini 3.7 Flash fallback for generation.

**Reason:** these settings are configurable and supported by the adapters.
Project quota/access is currently unverified; HTTP 429 does not trigger another
model request. See [Gemini models](https://ai.google.dev/gemini-api/docs/models)
and [Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings).

## D-006 — Local OCR/PDF adapters

**Decision:** use PyMuPDF and PaddleOCR adapters with page/region provenance,
preserving originals under private local storage.

**Reason:** source-level control and reproducible local ingestion; hosted
storage and write-path review remains open.

## D-007 — No LangChain core

**Decision:** implement the small retrieval/generation pipeline directly.

**Reason:** the needed components have explicit contracts and security
boundaries; no orchestration framework is currently required.

## D-006 — Backend-owned evidence

The model selects canonical passage IDs only; it cannot author displayed claim text or canonical quotes. This closes the lexical quote-combination weakness without pretending that general entailment is solved. Same-record/explicit-invoice paid/unpaid conflicts are rejected conservatively.

## D-007 — Relational record origin and history

Typed demo tables satisfy the structured-database requirement. RLS-visible live rows must match structured index metadata, so stale/deleted representations fail closed. History belongs to the authenticated actor; role context is separate metadata and replay reauthorizes evidence. The additive migration still requires fresh local database verification.
