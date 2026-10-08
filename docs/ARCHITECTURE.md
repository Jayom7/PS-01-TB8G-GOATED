# Architecture

## Current implementation (2026-10-08)

Clearframe is a local demo built from Next.js 16, FastAPI, Supabase Auth/Postgres,
and Gemini REST adapters. The schema is in `supabase/migrations`; it contains
organizations, profiles, roles, user-role assignments, documents, chunks, and
access grants. HNSW plus PostgreSQL full-text search feed the authorized hybrid
retrieval RPC. This stack is implemented; today's local Supabase runtime is not
reachable from this checkout (see `REVIEW_NEEDED.md`).

```text
Browser ── Supabase Auth session ──> FastAPI
                                      ├── user/brokered role session ──> RLS + retrieval RPC
                                      ├── Gemini Embedding 2
                                      └── Gemini Flash generation
CEO-gated local ingestion ── server-only secret ──> documents/chunks/role grants
```

The ordinary query and citation lookup paths forward the verified user's
bearer token to Supabase. They do not use the secret key. Local CEO demo-role
switching is a server broker that exchanges the signed-in local CEO for a
separate seeded role session; it does not make a client role label
authoritative. The signed-in identity and active authorization context are
separate values. The local ingestion path uses the server-only secret for
writes and is explicitly restricted to local demo setup.

## Query and evidence flow

1. FastAPI validates the Supabase session and resolves the active role context.
2. Gemini Embedding 2 embeds the query (1536 dimensions by default).
3. Supabase's invoker RPC applies row authorization while returning hybrid
   ranked chunks; Python does not retrieve broad privileged evidence and filter
   it afterward.
4. `prepare_generation_context` bounds evidence to 32,000 characters and sends
   only the RPC result to Gemini.
5. Gemini returns claims, citation IDs, and exact supporting excerpts. The
   deterministic validator checks citation membership, exact excerpt presence,
   coarse lexical overlap, and citation locations. This is not semantic
   entailment verification.
6. The response contains server-built citations. A source preview repeats an
   authorized lookup using the active user/session.

Retrieval and database ranking share one timing value; the RPC does not expose
a ranking-only duration. No dedicated reranker or duplicate retrieval call is
used. Generation is configurable through environment settings: Gemini 3.8
Flash primary, Gemini 3.7 Flash fallback, Gemini Embedding 2 at 1536 dimensions.
Fallback is limited to transient transport/timeouts and 5xx; 429 stops after one
request. Provider availability depends on current project quota/access.

## Ingestion and UI

PDF text and scanned-page OCR, PNG/JPEG OCR, and structured records normalize
to `knowledge_chunks` with page/region/row provenance. Local PDF/OCR/record
flows and source preview were recorded as working in the previous runtime
session. Image ingestion checks file signature and header dimensions before OCR
and caps raster area at 16 million pixels. Original uploads are kept in the
ignored local private-data directory. There is no background job queue or
server-reported per-stage progress.

The six direct routes are Dashboard, Ask, Sources, Ingest, Security, and
Evaluation. Dashboard and Security API data are session-scoped; Evaluation is
the synthetic local suite. The UI supports light/dark theme and responsive
navigation. Current browser rendering is not reverified in this resumed pass.

## Proof boundaries

Earlier local migration and pgTAP results are recorded in `REVIEW_NEEDED.md`
and `FINAL_LUNA6_FUNCTIONALITY_REPORT.md`; they are not a live check of the
current runtime or hosted project. Hosted policies, representative-scale
retrieval recall/query plans, production ingestion, concurrency, and semantic
claim entailment remain unverified. Preserve those boundaries when changing
database authorization, session brokering, storage, or the exact evidence
context passed to the model.
