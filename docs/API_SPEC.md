# API Contract

Base path: `/api/v1`. Protected routes require a Supabase bearer session.
FastAPI validates that session before workspace data access. Request schemas
reject extra query fields, including caller-provided identity or evidence.

## Current routes

- `GET /health`: liveness only; no provider/database check.
- `GET /api/v1/workspace`: authorized counts/source metadata and system
  configuration labels. `Gemini configured` does not mean reachable.
- `GET /api/v1/security`: current identity/context, effective-scope text, and
  recent in-memory retrieval events. It does not independently count
  unauthorized evidence or query hosted RLS state.
- `GET /api/v1/sources`: session-scoped authorized sources.
- `GET /api/v1/sources/{source_id}`: authorized excerpt lookup. Hidden/missing
  rows are returned as not found.
- `POST /api/v1/chat/query`: query embedding, authorized hybrid retrieval,
  bounded generation context, and server-built citations.
- `POST /api/v1/ingestion/upload` and `/api/v1/ingestion/structured`: local
  CEO-gated write paths; require configured local demo support.
- `GET /api/v1/evaluation` and `POST /api/v1/evaluation/run`: local synthetic
  retrieval/authorization evaluation.

## Query response and checks

`state` is `CITATION_VALIDATED`, `PARTIALLY_CITATION_VALIDATED`, or
`INSUFFICIENT_EVIDENCE`. Each factual claim is expected to contain citation IDs
and `supporting_quotes` in generation output. The API checks each ID belongs to
the exact bounded context, the quote occurs in that citation's content after
whitespace normalization, a coarse lexical overlap threshold, and a usable
source location. Only claim text and server-created citations are returned.
These deterministic checks reject some obvious unsupported output; they do not
prove semantic entailment.

The successful query trace reports authenticated-session use, authorized
evidence-item count, model/fallback, and timings. It deliberately has no
numeric unauthorized-evidence counter because that quantity is not separately
measured. Database ranking time is included in retrieval timing. Provider
errors use safe API details; HTTP 429 is `provider_rate_limited` and does not
trigger a second model request.

The API also returns local dashboard state and evaluation measurements; see
`REVIEW_NEEDED.md` for the exact historical verification boundary. Hosted
Supabase behavior and current provider availability are unverified.
