# RAG Pipeline

## Ingestion and origin

PDF extraction preserves pages; scanned PDFs use bounded local OCR. PNG/JPEG inputs must pass signature, header and actual decode checks before OCR. Limits are 25 MB, 100 PDF pages, 16 million decoded pixels, and 1,000 OCR regions per image. These bound demo parser inputs; they do not establish production sandboxing.

Structured ingestion whitelists seven tables and matching business keys, persists a typed row under server-assigned tenant/source IDs, rereads its fields, then renders canonical index text. Invoice overdue status is computed from due date, unpaid status, and the row's explicit `status_as_of` snapshot—not the wall clock. Seed JSON is never the final database origin story.

## Query

1. Verify Auth and resolve the requested local demo context server-side.
2. Embed once; retrieve once with the caller/broker token through invoker RPC/RLS.
3. Issue canonical passage IDs only for located, returned evidence, with a 16,000-character content budget.
4. If no usable authorized passages exist, return `INSUFFICIENT_EVIDENCE` without generation.
5. Gemini selects `evidence_ids` only. Model-supplied text and quotes are rejected.
6. Resolve every selected ID to backend-owned excerpts and page/row/region citations. Reject unknown/mixed IDs, missing references, and bounded paid/unpaid conflicts for the same record or explicit invoice ID across modalities.
7. Stream the final validated result and persist actor-scoped history. Persistence failure is visible and does not invalidate an otherwise valid answer.

`CITATION_VALIDATED` means accepted extractive provenance. It does not prove source truth, general contradiction detection, relevance, or semantic entailment. Partial validation displays only accepted excerpts. Retrieved documents are untrusted data; the model has no execution tools. Live injection resilience remains unverified.

## Provider and evaluation

Generation: configurable Gemini 3.8 Flash primary and 3.7 Flash fallback; embeddings: Gemini Embedding 2 / 1536 dimensions. One fallback is allowed for transport/timeouts and transient 500/502/503/504. HTTP 429 and malformed responses stop. No second embedding/retrieval is performed for fallback.

[Official 3.8 Flash documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) and [structured-output documentation](https://ai.google.dev/gemini-api/docs/structured-output) were inspected. Model inventory is verified, but the current generation attempt failed with HTTP 503; no fastest-working model or successful latency benchmark is established.

Evaluation reports hit rate@12 (any expected source), MRR, checked forbidden hits, citation-location presence, modality observations, and measured retrieval latency. It does not compute conventional recall or score semantic answers. Reads label saved results as recorded; refresh never claims a rerun. Full result access and runs require the CEO local context.
