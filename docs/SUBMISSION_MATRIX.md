# PS-01 Submission Matrix — 2026-10-09

**IMPLEMENTED** means repository code/schema exists. **VERIFIED LOCALLY** identifies the specific executed unit, extraction, build, or browser check. **RECORDED BUT NOT FRESH** refers to older runtime artifacts. **UNVERIFIED** means no current evidence. **BLOCKED** identifies an attempted check prevented by a dependency. No status below certifies hosted security.

| Official requirement | Implementation / code location | Database mechanism | Test / fresh evidence | Demo evidence | Status |
|---|---|---|---|---|---|
| PDF ingestion | `ingestion.py:extract_pdf`, `main.py` file ingest | documents + page-located knowledge_chunks | Real extraction: 8 PDF chunks; parser/unit tests | Contract PDF and exact page | IMPLEMENTED; extraction VERIFIED LOCALLY; persistence BLOCKED |
| Image + OCR ingestion | `ingestion.py:extract_image_ocr`, decode/size guards | image_id + ocr_region in unified chunks | Real extraction: 30 OCR regions; malformed/oversize image tests | Scanned Acme invoice, original and region overlay | IMPLEMENTED; extraction VERIFIED LOCALLY; live indexing BLOCKED |
| Structured DB records | `records.py`, `seed_local_demo.py`, new relational migration | Seven typed tables, business PKs, tenant/source FKs, invoker origin view | Fixture/business-key/snapshot tests; live typed seed blocked | invoices / ACM-INV-2048 with persisted fields | IMPLEMENTED; unit checks VERIFIED LOCALLY; SQL/persistence BLOCKED |
| Unified vector + metadata index | `integrations.py:retrieve_chunks`, base migration | vector(1536), HNSW, GIN, hybrid invoker RPC | Context/retrieval adapter tests; 19 sources / 45 extraction candidates | Sources console, cross-modal evidence | IMPLEMENTED; live index BLOCKED |
| Natural-language answering | `main.py:_run_query`, `rag.py`, `integrations.py` | User-scoped retrieval provides model input | 76 backend tests; inventory HTTP 200; generation HTTP 503 | OCR amount and contract/row question | IMPLEMENTED; local adapters VERIFIED LOCALLY; successful live answer BLOCKED |
| Retrieval-time row/document ACL | Base policies + restrictive structured policy; role broker | RLS applies during RPC selection; chunk/document grants; same-org origin constraints | 43 pgTAP assertions prepared, cannot connect to 54322; API auth/escalation tests pass | Finance/HR contrast, forbidden citation/original lookup | IMPLEMENTED; API checks VERIFIED LOCALLY; current DB proof BLOCKED; earlier 24/24 RECORDED BUT NOT FRESH |
| Unauthorized evidence never enters context | `main.py`, `rag.py:prepare_generation_context` | Only caller/broker invoker results enter bounded context | Unit tests capture exact context, forged requests denied, no elevated query retrieval | Security boundary and trace | IMPLEMENTED; context construction VERIFIED LOCALLY; live RLS-dependent guarantee BLOCKED |
| Exact source citations | `rag.py:validate_generation`, protected source endpoints | Located chunk IDs, current typed fields, document policy | Unknown/mixed IDs, fabricated text/quotes, missing locations, payment conflicts, preview denial tests | Open canonical excerpt, PDF page, OCR region, row fields | IMPLEMENTED; validator VERIFIED LOCALLY; live generated citations BLOCKED |
| Hallucination/grounding demonstration | ID-only selection, backend extractive rendering, bounded invoice conflict guard | Canonical retrieved content and provenance | Valid/unsupported/cross-modal contradiction regressions pass | Inspector shows selected source text | Extractive provenance VERIFIED LOCALLY; general entailment/relevance UNVERIFIED; live injection outcome BLOCKED |
| Architecture demonstration | `ARCHITECTURE.md`, `DATA_MODEL.md`, Security and Trace UI | Auth, invoker RPC/RLS, pgvector/full text, typed origin | Source/schema inspection; tests; labeled UI fixture audit | Security → trace → evidence inspector | IMPLEMENTED; documentation/UI VERIFIED LOCALLY; deployed DB status BLOCKED; hosted UNVERIFIED |

## Supporting product and reproducibility checks

| Surface | Fresh verification | Remaining boundary |
|---|---|---|
| Login | Actual dev and production public page, desktop/mobile | Live credential login blocked by Auth runtime |
| Overview / Ask / Sources / Ingest / Security / Evaluation | All routes, light/dark, desktop/tablet/mobile via isolated labeled fixtures | Fixtures do not establish Auth/RLS/provider/persistence success |
| Evidence / trace / navigation / account | Escape, close button, outside click, focus trap/return, five role controls; source sorting/filtering | Real role brokering and revoked live source access require database |
| Conversation history | Ownership/context API tests, replay rebuilding, malformed/forged/revoked content tests; fixture replay/new controls | Actual persistence and restart verification blocked; recent 200-turn bound |
| Startup / verification | `scripts/dev`, `scripts/verify_demo`, `verify_services.py`; shell syntax and clear Docker-unavailable exit | Clean full-stack restart blocked; no OS/runtime changes made |
| Evaluation | Historical report displayed as recorded; failure state visible; metric semantics corrected | Fresh current retrieval benchmark blocked; no semantic-answer scoring |

The exact six acceptance flows and outage backup are in [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md). Current risks and historical boundaries are in [REVIEW_NEEDED.md](REVIEW_NEEDED.md).
