# Review Needed — 2026-10-09

This is the current verification boundary; earlier reports are historical.

## VERIFIED LOCALLY

- 76 backend tests; Ruff check and format; frontend ESLint, TypeScript, production build.
- Actual local PDF/OCR extraction across 19 synthetic sources: 45 candidates (8 PDF, 30 OCR, 7 structured fixture candidates). Database embedding/persistence is not implied.
- Public login renders in the real app, including the production server. A separate labeled visual fixture server validates six workspace routes, both themes, 1440×900 / 900×900 / 390×844 layouts, all five role controls, history replay/new conversation, filters, PDF/image/record previews, OCR overlay, native drawers, and mobile navigation. Fixture checks prove no live authorization or generation behavior.
- Configured 3.8 Flash and 3.7 Flash IDs appeared in a real Gemini inventory response (HTTP 200). One synthetic, bounded generation attempt returned HTTP 503 after the single fallback.

## BLOCKED

- Docker engine socket is absent/unavailable. Local Supabase API is unreachable; Postgres 127.0.0.1:54322 refuses connections. New migration application, 43 pgTAP assertions, real typed-row persistence, history persistence, and five-role database flows cannot be verified.
- Live grounded Gemini answer, cross-modal answer, HR refusal, and live injection outcome are incomplete. Do not spend repeated failing provider calls or substitute a fixture answer.
- `scripts/dev` and readiness checks stop with a clear blocked result; a clean full-stack restart is not verified.

## RECORDED BUT NOT FRESH

`PHASE1_VERIFICATION.md`, `FINAL_LUNA6_FUNCTIONALITY_REPORT.md`, and ignored historical evaluation files describe older code/runtime state. Prior pgTAP 24/24 and an earlier successful OCR answer do not verify this migration or today's provider. Saved metrics remain labeled recorded.

## UNVERIFIED / residual risks

- Hosted Supabase was neither modified nor verified.
- Extractive provenance is enforced; relevance, source truth, general entailment, and exhaustive contradiction/injection resistance are not solved. The payment guard is deliberately bounded to record/explicit invoice identifiers.
- Typed rows currently inherit a source-document grant; chunk-only structured grants do not expose their origin row. Each demo structured source holds one row.
- Ingestion uses bounded local parsers and compensating multi-request writes, not a transaction/job queue. Production isolation, rate limits, concurrent retry/lifecycle behavior, hosted original storage, and automated reindex need further review.
- History loads at most 200 recent turns; follow-up questions do not implicitly reuse previous conversational evidence. No rename/search platform was added.
- Filtered HNSW recall, real query plans, representative latency/scale, and performance under selective grants remain unmeasured.

## Next evidence

Start the existing Docker runtime, run `./scripts/dev --seed`, then `./scripts/verify_demo`. Resolve any migration/seed errors before recording. Run the real retrieval evaluation, inspect current evidence for the six acceptance flows, and stop after one bounded failed provider attempt. Hosted verification is a separate authorized task.
