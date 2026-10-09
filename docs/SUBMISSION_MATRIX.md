# PS-01 Submission Matrix — 2026-10-09 acceptance pass

Code snapshot: `f825075`. IMPLEMENTED describes inspected code; VERIFIED describes checks executed in this pass. BLOCKED identifies an attempted dependency failure or an explicitly skipped dependent check. Hosted behavior is unverified. Historical reports do not override this matrix.

| Official requirement | Actual implementation and fresh evidence | Verified status / remaining boundary |
|---|---|---|
| PDF ingestion | Real parser/seed persisted PDF chunks; protected contract page inspected; bounded page rendering and source-denial regression tests | Local extraction, embedding, persistence and source preview VERIFIED. Fresh browser upload completion not exercised. |
| Image + OCR ingestion | Real PaddleOCR seed, persisted OCR regions and private original; live mobile image/region inspector | Local extraction, embedding, persistence and preview VERIFIED. Fresh browser upload completion not exercised. |
| Structured DB records | Seven typed tables, business PKs, current-row origin view; repaired jsonb field-order seed defect; actual invoice fields inspected | Seven persisted rows and stale-row/tenant constraints VERIFIED by local DB and API checks. |
| Unified vector + metadata index | 19 sources / 45 embedded chunks; invoker hybrid RPC; fresh five-query retrieval evaluation; explicit overdue/terms query returned PDF, row and OCR among top four | Local multimodal index/retrieval VERIFIED. Filtered ANN recall at representative scale unmeasured. |
| Natural-language answering | ID-only generation, backend canonical excerpts and real SSE; provider returned 503, then raw diagnostic 429 | Implementation/unit contracts VERIFIED; fresh successful live answer BLOCKED. |
| Retrieval-time row/document ACL | Actual five Auth contexts, invoker RPC and RLS; 43/43 pgTAP and 50 live authorization/source checks | Local role filtering, forged-context denial and forbidden lookups VERIFIED. Hosted unverified. |
| Unauthorized evidence never enters context | Caller/broker session retrieval; exact bounded context captured by unit tests; actual RLS denies forbidden evidence | Context construction and local retrieval boundary VERIFIED. No independent live outbound prompt capture or successful generation proof this pass. |
| Exact source citations | Canonical IDs/title/location/excerpts; protected PDF page, OCR region and invoice row resolve correctly; forged citation tests pass | Source lookup/provenance contracts VERIFIED. Every citation from a fresh generated answer remains BLOCKED. |
| Hallucination/grounding demonstration | Canonical extractive rendering, fabricated quote/ID and bounded invoice-conflict tests | Bounded provenance regressions VERIFIED. Live document injection outcome BLOCKED; general entailment/relevance unverified. |
| Architecture demonstration | Existing Auth/FastAPI/invoker RLS/pgvector/typed-origin architecture; real Security UI and local stack | Source/schema/local architecture VERIFIED. Populated real-answer trace BLOCKED; hosted unverified. |

## Live acceptance flows

| Flow | Current result |
|---|---|
| CEO scanned-invoice amount | OCR source/region and retrieval work; live generation BLOCKED. |
| PDF contract terms | Protected actual contract page and excerpt work; generated answer BLOCKED. |
| Database invoice status | Persisted `invoices / ACM-INV-2048` and fields work; generated answer BLOCKED. |
| Cross-modal overdue + terms | Explicit live query retrieves all three modalities, including contract and invoice row; generated answer BLOCKED. |
| HR same finance question | Real retrieval/direct metadata denies finance; generated refusal BLOCKED. |
| Forbidden source preview | Citation, document, original and rendered-page requests return 404 in unauthorized contexts; VERIFIED. |
| Prompt injection | Unit boundary tests pass; successful poisoned-source model outcome BLOCKED. |

## Supporting product checks

Actual local CEO login/logout and all five role controls worked. Role-visible source counts were CEO 19, Finance 13, HR 3, Sales 3 and Engineer 5. All six routes were audited in both themes at desktop/tablet/mobile sizes. Source filters/sort, close buttons, Escape, exposed backdrop closing, focus return/trap, mobile navigation, account theme/closing, empty history and draft reset were checked. Populated conversation persistence/reopen across restart was not verified; the current history contains zero turns.

Latest local security report: `data/local/security-verification.json`, completed `2026-10-09T04:02:54.285391+00:00`, code `f825075`: 50 passed / 2 generation checks blocked, exit 2. Full API suite: 79 passed; local SQL suite: 43 passed; frontend lint/types/build passed. No frontend automated interaction-test script exists; browser checks were manual automation against the real app.

Fresh synthetic retrieval evaluation: hit rate@12 1.000, MRR 0.550, checked forbidden hits 0, 47/47 retrieved locations present, mean 707.6 ms. Five questions and one direct HR check are a small smoke set, not a semantic-answer benchmark. Its narrow OCR-amount `cross_modal_retrieval` flag is false; the separate explicit overdue/terms query retrieved PDF, structured row and OCR. Do not conflate those query definitions.

See [runbook](DEMO_RUNBOOK.md), [current report](FINAL_BUILD_REPORT.md), [visual audit](UI_DESIGN.md) and [remaining review](REVIEW_NEEDED.md).
