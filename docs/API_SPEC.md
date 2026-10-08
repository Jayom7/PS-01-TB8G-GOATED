# API Contract

Protected routes require verified Supabase bearer identity. Optional `X-Demo-Role` is resolved only by the local CEO broker; it is never authoritative by itself.

| Method / route | Behavior |
|---|---|
| GET /health | Liveness only |
| GET /api/v1/workspace | Authorized sources/counts, identity/context, configuration labels |
| GET /api/v1/security | Scope and in-process request trace; no live RLS certification |
| GET /api/v1/sources | RLS-visible source metadata |
| GET /api/v1/sources/{chunk_id} | Authorized canonical chunk/record fields |
| GET /api/v1/sources/{document_id}/preview | First authorized source excerpt |
| GET /api/v1/sources/{document_id}/original | Local private PDF/image bytes; document grant required |
| POST /api/v1/chat/query | Query and optional conversation UUID; canonical final result |
| POST /api/v1/chat/stream | Real progress events, then validated result or safe error |
| GET /api/v1/conversations | Recent actor/org/current-role conversations, bounded to 200 turns |
| GET /api/v1/conversations/{id} | Reauthorized/reconstructed turns |
| DELETE /api/v1/conversations/{id} | Owner-scoped soft hide |
| POST /api/v1/demo/switch | Local CEO context broker |
| POST /api/v1/ingest/file | CEO/local file upload, max 25 MB |
| POST /api/v1/ingest/structured | CEO/local typed row persistence and indexing |
| GET /api/v1/evaluation | CEO/local recorded synthetic measurements |
| POST /api/v1/evaluation/run | CEO/local actual retrieval suite |

Generation claims contain only evidence IDs. Public claims contain canonical text plus backend-built citations (chunk ID, evidence ID, document ID, modality, location, excerpt). States: `CITATION_VALIDATED`, `PARTIALLY_CITATION_VALIDATED`, or `INSUFFICIENT_EVIDENCE`. These are extractive provenance states, not semantic truth scores.

SSE progress stages reflect access, search, evidence selection, generation, and validation. No raw generated answer delta is released. Provider failures use safe codes; 429 never falls back. The final trace reports measured timings, configured/used model, context count, and history-save outcome. Ranking-only duration remains null because ranking occurs in the RPC. History replay discards stored trace metadata and reports current source-access rebuilding with no model call or original timings.
