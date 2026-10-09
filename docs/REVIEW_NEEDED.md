# Review Needed — current acceptance boundary, 2026-10-09

## Verified now

79 backend tests; Ruff; frontend lint/types/production build; all three local migrations; 43/43 pgTAP; 50 live authorization/source checks; local launcher restart and actual CEO Auth. Real persisted corpus: 19 sources, 45 embedded chunks, 7 typed rows, five Auth contexts. PDF/OCR/record previews and six real routes in both themes at desktop/tablet/mobile work. Fresh retrieval smoke set and explicit three-modality overdue/terms retrieval were executed. See [matrix](SUBMISSION_MATRIX.md) for precise scope.

## Must fix before submission

Gemini generation is unavailable. Full verification reached 503 after fallback; a bounded direct raw diagnostic subsequently returned 429 RESOURCE_EXHAUSTED for the 20-request free-tier generation limit, with a reported 22h 48m 46s retry interval. Embeddings work. Do not loop failing calls, fabricate answers or change billing/credentials to bypass this boundary.

When generation is available, run `./scripts/verify_demo` and all seven [runbook acceptance flows](DEMO_RUNBOOK.md). Verify exact citations from each successful answer, inspect live authorized evidence/trace, exercise the poisoned source only when it is actually retrieved, and save/reopen a real conversation across restart. Current empty history is not persistence/replay proof. Browser upload success has not been exercised in this pass.

## Other important boundaries

- Docker's socket disappeared once during the final restart; supported CLI recovery and repeat local checks succeeded, but the shutdown cause is unknown. Recheck readiness before recording.
- Hosted Supabase was untouched and unverified. Only local additive migrations and tests ran; no reset.
- Exact context construction and local RLS are tested; no independent capture of a successful live outbound generation prompt occurred.
- Extractive provenance does not establish relevance, source truth, general entailment or exhaustive injection resistance. The invoice conflict guard is bounded.
- Synthetic retrieval metrics are a small smoke set. The narrow OCR query's cross-modal flag is false; a separately tested overdue/terms query retrieves all three modalities. Neither proves a successful cross-modal answer.
- Typed rows inherit document grants; each demo structured source holds one row. Chunk-only grants do not expose the origin row.
- Ingestion uses compensating multi-request writes, local private originals and bounded parsers. Production isolation, concurrency/retry lifecycle, hosted original storage and automated reindex remain unverified.
- History is bounded to 200 recent turns and does not implicitly reuse prior conversation evidence. Filtered HNSW recall/query plans at representative scale remain unmeasured.
- Visual audit found no remaining page-level overflow at checked sizes. Internal Evaluation table scrolling is retained. Populated chat/history/trace states, full automated accessibility/contrast and reduced-motion emulation were not audited live in this pass.

Older `PHASE1_VERIFICATION.md`, `FINAL_LUNA6_FUNCTIONALITY_REPORT.md`, prior fixture screenshots and earlier provider answers remain historical, not current acceptance evidence.
