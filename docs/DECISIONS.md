# Architecture Decisions

Status terms: **proposed** means a planned choice awaiting implementation and
verification; **accepted** means implemented and reviewed. All entries below
are proposed as of 2026-10-08.

## D-001 — One unified chunk index

**Decision:** PDF, OCR, and structured evidence share a `knowledge_chunks`
model and `SecureRetriever` contract.

**Reason:** cross-modal retrieval and authorization need one query boundary,
provenance vocabulary, and evidence set before generation.

## D-002 — Database-enforced user retrieval

**Decision:** ordinary queries use a user-scoped database identity and RLS;
the service-role credential is reserved for separate server-side admin tasks.

**Reason:** filtering in the API after privileged retrieval does not satisfy
the requirement. Exact implementation remains subject to RLS tests.

## D-003 — PostgreSQL with pgvector and full text

**Decision:** Supabase PostgreSQL is the initial persistence and unified
retrieval store, with pgvector cosine search and PostgreSQL full-text search.

**Reason:** one relational transaction and policy boundary can cover source
rows, ACLs, metadata, and embeddings. This is a target, not a benchmark result.

## D-004 — HNSW is a measured starting point

**Decision:** begin with HNSW and measure filtered recall and plans before
acceptance. Verify extension version and iterative-scan configuration.

**Reason:** approximate search is practical, but Supabase documents that
selective filters may return fewer than requested unless scans continue.
See [Supabase HNSW guidance](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes).

## D-005 — Configurable Gemini defaults

**Decision:** start with Gemini Embedding 2 at 1536 dimensions and Gemini 3.8
Flash for generation; inject provider/model through configuration and
interfaces.

**Reason:** current official Google docs list these stable model IDs and
recommend 1536 as an embedding size. Check project access, limits, SDK, and
quality during integration; neither provider choice is embedded in domain
contracts. See [Gemini models](https://ai.google.dev/gemini-api/docs/models)
and [Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings).

## D-006 — Local OCR/PDF adapters

**Decision:** use a local OCR adapter (PaddleOCR candidate) and PyMuPDF
candidate, preserving originals and precise source coordinates.

**Reason:** source-level control and demo reproducibility. Select concrete
versions after checking platform support and installation constraints.

## D-007 — No LangChain core

**Decision:** implement the small retrieval/generation pipeline directly.

**Reason:** the needed components have explicit contracts and security
boundaries; no orchestration framework is currently required.
