# Architecture

## Product boundary

PS-01 is a competition prototype for answering questions over synthetic
enterprise material. It combines PDFs, images processed with OCR, and
structured business records. One retrieval abstraction and one canonical
chunk table serve every source type. This is a design target; no services are
implemented yet.

## Runtime components

```text
Browser (Next.js) ── Supabase Auth session ──> FastAPI
                                                │
                     user JWT scoped request ───┼──> Supabase Postgres
                                                │      RLS + unified RPC/query
                                                ├──> Gemini embedding adapter
                                                └──> Gemini generation adapter

Admin ingestion job ── restricted credential ───────> source storage + chunks
```

The browser handles presentation and session UX. FastAPI validates the bearer
token and constructs a user-scoped database client for query and source access.
The database is the authorization boundary for retrieval. A distinct,
server-only administrative ingestion path may use elevated credentials to
write data; it is not reachable from the ordinary query path.

## Unified retrieval model

PDF pages, OCR regions, and structured rows normalize into `KnowledgeUnit`s,
then into `knowledge_chunks`. Each item has a common ID, source type, source
identity, provenance/location, tenant, classification, ACL relationship,
text representation, metadata, and embedding. One `SecureRetriever` issues
authorized semantic and keyword searches across all types, fuses authorized
results, and returns a typed evidence set. Cross-modal results are a supported
contract, not separate query systems merged after retrieval.

Source-specific original assets remain in object storage; chunks retain stable
references and exact page, row, or OCR-region coordinates. Structured values
are rendered into deterministic searchable text while preserving typed row
fields and primary-key provenance.

## Application boundaries

- `apps/web`: Next.js/TypeScript UI, auth session, chat, source preview,
  security trace, ingestion status, and evaluation screens.
- `apps/api`: FastAPI routes, Pydantic contracts, token validation, query
  orchestration, ingestion adapters, provider adapters, and audit events.
- `packages/shared`: API shapes and source/citation vocabulary only where
  sharing prevents drift; Python domain types remain authoritative for API.
- `supabase/migrations`: schema, RLS, vector/full-text indexes, and retrieval
  functions; `supabase/tests`: database authorization tests.
- `data/demo`: synthetic PDF/image/structured fixtures; never private data.

## Model and index starting choices

Use `gemini-embedding-2` with output dimension 1536 as a configurable baseline;
Google currently lists the model as stable and recommends 768/1536/3072 output
dimensions. Use `gemini-3.8-flash` as the configurable stable chat model. Verify
account availability, quota, SDK behavior, and exact output shape during
integration. PostgreSQL uses pgvector cosine distance and HNSW initially, plus
`tsvector` full-text retrieval. These choices must be revisited against the
representative evaluation set and query plans.

## Critical request sequence

1. Validate the Supabase-issued JWT and derive the subject from its verified
   claims; ignore client-supplied role, user, organization, or ACL claims.
2. Embed the query through a provider adapter.
3. Search semantic and lexical candidates through a database operation whose
   effective identity is the authenticated user and whose RLS/ACL predicates
   are part of that operation.
4. Fuse and bound only authorized results. Do not fetch protected candidates
   into Python and filter them afterward.
5. Build an immutable context from the authorized evidence set and retain the
   exact evidence IDs passed to the generator.
6. Generate typed claims and candidate source IDs; validate every source ID,
   evidence membership, authorization, and location against the context.
7. Return validated citations or a controlled insufficient-evidence response.

## Deployment shape

Remain provider-agnostic for the API and database while developing locally.
The frontend may deploy to Vercel; the API can later use Cloud Run or an
equivalent container host. No deployment architecture is implemented or
validated yet.

## Constraints

- RLS and filtering must cover rows and metadata, not just answer text.
- No normal query path may use a service-role credential.
- No generated factual claim may survive without validated evidence.
- Ingestion and query credentials, roles, and code paths are separate.
- Evaluation results are measured outputs; no seeded or hand-authored metrics.
