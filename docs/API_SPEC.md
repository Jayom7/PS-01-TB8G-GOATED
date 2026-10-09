# API Contract

Protected routes require verified Supabase bearer identity. Optional `X-Demo-Role` is resolved only by the local CEO broker; it is never authoritative by itself.

| Method / route | Behavior |
|---|---|
| GET /health | Liveness only |
| GET /api/v1/workspace | Authorized sources/counts, identity/context, configuration labels |
| GET /api/v1/security | Scope and durable actor/org/context metadata events; no live RLS certification |
| GET /api/v1/sources | RLS-visible source metadata |
| GET /api/v1/sources/{chunk_id} | Authorized canonical chunk/record fields |
| GET /api/v1/sources/{document_id}/preview | First authorized source excerpt |
| GET /api/v1/sources/{document_id}/original | Local private PDF/image bytes; document grant required |
| DELETE /api/v1/sources/{document_id} | Local CEO transactional source/grant/chunk/typed-row removal, audit and private-original cleanup |
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

Generation claims contain only evidence IDs. Public claims contain canonical text plus backend-built citations (chunk ID, evidence ID, document ID, modality, location, excerpt). States: `CITATION_VALIDATED`, `PARTIALLY_CITATION_VALIDATED`, `INSUFFICIENT_EVIDENCE`, explicitly labeled `SMALL_TALK`, `CLARIFICATION_NEEDED` (no factual claim), or `VERIFIED_EVIDENCE`. The latter is deterministic extraction after transient generation failure, with an explicit no-language-model message, null generation_model, response_mode=verified_evidence and provider_failure metadata. It is never live generation success. These are extractive provenance states, not semantic truth scores.

SSE progress payloads contain only a stage name, reflecting access, search, retrieval completion, evidence selection, generation, final access recheck and validation; composing_verified_evidence appears only on that fallback path. Insufficient evidence never claims model generation. No raw generated answer delta is released. Provider failures use safe codes; 429 switches only for explicit model-scoped quota violations; unknown/global quota stops. Machine causes and retry guidance survive SSE. Unexecuted stages are null. The final trace reports measured timings, configured/used model, context count, safe per-model attempts (model/status/cause/elapsed time), and history-save outcome. Failure responses also preserve attempted-model metadata. Ranking-only duration remains null because ranking occurs in the RPC. History replay discards stored trace metadata and reports current source-access rebuilding with no model call or original timings.

Web auth routes: GET /auth/settings exposes Google enablement only (no-store); GET /auth/callback exchanges PKCE code and allowlists dashboard/reset destinations. /forgot-password and /reset-password implement recovery without granting roles. Local same-origin /api/v1 rewrites preserve bearer/context headers and require FastAPI authorization.

Closeout behavior: finite wording repairs never fuzzy-match IDs. Recent conversation citations are only referent pointers, reread under current RLS; every business follow-up embeds/retrieves anew. Unclear referents or multiple currently matching invoices request clarification without listing identifiers or amounts.

Transient408/5xx/transport/timeout errors may try one configured fallback. Model-specific429 may switch; shared/unknown quotas fail fast. Metadata-only credential/model circuits cool down30–120 seconds and allow one in-flight call/probe per model per worker. Skipped attempts have attempted=false/cooldown=true; upstream status/retry diagnostics are retained separately from ordinary chat copy. Terminal400/401/403/404, safety and malformed output never trigger blind fallback.

Evaluation GET distinguishes restricted, not_run, unavailable and completed. Latest and up to10 previous local JSON artifacts are loaded honestly; legacy/CLI origin is not relabelled as app execution. POST runs the real existing retrieval suite with a120-second bound, captures current corpus counts/run UUID/completion/duration and atomically replaces the private0600 artifact after archiving the previous bytes. Concurrent app runs in the worker return409; failed runs preserve prior results. This is local file persistence, not invented database evaluation rows.
