# RAG Pipeline

## Ingestion

- PDF text is extracted by page; scanned pages are rendered and sent through
  the local OCR adapter with page/image/region provenance.
- PNG/JPEG upload validates signature and header dimensions before OCR; the
  image pixel-area cap is 16 million pixels. This protects the local OCR path
  from oversized rasters; it does not validate all image-decoder behaviors.
- Structured records serialize deterministically into source chunks with table
  and row provenance.
- All source types persist through the common `documents`, `knowledge_chunks`,
  and `access_grants` model. CEO-only local upload uses a separate server-side
  privileged writer. Originals are private local files. There is no background
  ingestion-job progress API.
- Prior local PDF, scanned-page OCR, image OCR, structured ingestion, and source
  preview checks are recorded in `REVIEW_NEEDED.md`; the OCR engine has not been rerun in Phase 1. The running local database and
  five-role authorization boundaries have been freshly checked.

## Query and retrieval

1. Validate the Supabase bearer session; derive identity from trusted Auth
   results. Demo role context is separately resolved by the local server-side
   broker and restricted to the five seeded roles.
2. Embed with configurable Gemini Embedding 2 (default 1536 dimensions).
3. Call the `SECURITY INVOKER` hybrid retrieval RPC with the caller's session.
   PostgreSQL applies RLS/ACL during candidate selection; SQL combines vector
   and full-text ranks. No privileged broad fetch followed by Python filtering
   is used by the ordinary query path.
4. If no authorized chunks return, respond `INSUFFICIENT_EVIDENCE` without
   calling generation. Otherwise bound the exact evidence context to 32,000
   characters. The database RPC performs ranking; API timing combines retrieval
   and ranking because no separate rank duration is exposed.
5. Pass only that bounded authorized context to the generation adapter.

The database has HNSW and GIN indexes. Historical local evaluations are small
synthetic smoke tests. Selective-filter recall, exact fallback behavior,
representative query plans, hosted RLS, and production performance remain
unverified; see `REVIEW_NEEDED.md`.

## Generation and citation validation

The prompt treats retrieved text as untrusted data. The model must return a
claim, citation IDs, and an exact short supporting quote for each cited
passage. The deterministic validator checks IDs against the exact context,
every quote's inclusion after whitespace normalization with word boundaries,
a bounded paid/unpaid contradiction guard, a 0.35 token-overlap threshold
after stop-word removal, and the existence of source-specific citation
locations. The public response contains only claim text and citations rebuilt
from retrieved rows.

These checks can reject forged IDs, missing quotes, unrelated quote/claim
pairs, and missing provenance. They can also reject reasonable paraphrases.
They do not prove entailment, detect all contradictions, or replace a semantic
grounding evaluation. `CITATION_VALIDATED` now means the implemented
deterministic checks passed, not that semantic truth is verified.

## Provider behavior

- Generation defaults: Gemini 3.8 Flash primary, 3.7 Flash fallback; settings
  remain configurable. Embedding defaults to Gemini Embedding 2 at 1536 dims.
- Timeout/transport/transient 5xx may try the configured fallback once. HTTP
  429 does not retry another model. Safe errors carry a provider code; secrets,
  prompts, and source content are not returned in user-facing error messages.
- The Dashboard reports whether Gemini is configured, not whether it is
  available. Historical live generation attempts returned 429; do not claim a
  fresh successful response until one is checked after quota/access recovers.

## Evaluation

The local suite measures positive-query hit rate, rank, source modality, checked forbidden
source hits, retrieved citation-location presence, and latency; it
does not score semantic answer quality. Previous six-case local results
(hit rate@12 1.0, MRR 0.775, zero forbidden hits in the checked cases,
39 retrieved rows with citation ID/location present) are historical, small, and synthetic—not a representative
benchmark. Legacy result labels are corrected on read without modifying saved files or
claiming a rerun. Fresh runs use schema version 2; location presence does not
prove generated-answer provenance or entailment. The fresh security suite is
separate from these small retrieval metrics.
