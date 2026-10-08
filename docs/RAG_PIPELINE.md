# RAG Pipeline

## Ingestion

1. **Implemented:** PDF and image parsers validate file signatures
   and size. PDF text extraction records page provenance; blank scanned pages
   and images can use local PaddleOCR with bounded rendering and region
   provenance. Structured records serialize deterministically and retain table
   and row provenance. OCR/PDF and structured-record unit tests pass; PaddleOCR
   was also run on the synthetic invoice scan.
2. **Implemented locally:** authenticated CEO-gated ingestion, checksums,
   private local originals, role grants, and persistence of chunks/vectors.
   Background jobs and transactional rollback remain unimplemented.
4. Normalize outputs to `KnowledgeUnit(content, source_type, source_id,
   organization_id, classification, provenance, metadata, access_policy)`.
5. Chunk with source-aware boundaries and stable source locations. Validate
   content, provenance, policy, and source type before embedding.
6. Embed through `EmbeddingProvider`; validate count, dimension, finiteness,
   and source-unit alignment. Upsert chunks and search vectors transactionally
   where possible. Report partial failures explicitly and idempotently.

## Query and retrieval

1. Verify identity from the bearer token; derive tenant/roles from trusted
   identity state.
2. Embed the query with the configured model/dimension.
3. Execute semantic and PostgreSQL full-text retrieval against the same
   `knowledge_chunks` abstraction, with tenant and resource ACL enforced by
   RLS/database predicates during candidate access.
4. Combine ranked lists with a documented reciprocal-rank-fusion baseline.
   Optional reranking is deferred until measured benefit and latency are known.
5. Bound by configured top-k and token budget only after authorization. Record
   the exact selected evidence IDs and safe retrieval trace.
6. If no adequate authorized evidence exists, return insufficient evidence
   without calling the generator.

HNSW is the initial approximate index candidate. Selective filters can reduce
   returned neighbors; validate pgvector iterative scans and exact-search
fallback against the installed extension version and representative
authorization selectivity. The migration has been applied to local Supabase;
24 pgTAP authorization/schema checks pass. The hosted project has not been
migrated or verified.

## Grounded generation

The model receives only evidence records produced by the retrieval operation.
The prompt labels source text as untrusted reference material and asks for a
structured response containing claims and proposed evidence IDs. A
deterministic citation validator checks that IDs are present in the exact
prompt evidence and tied to a precise page, row, or region. This checks
citation membership and provenance; it does not prove semantic entailment.
The API therefore reports `CITATION_VALIDATED`, not a claim that semantic
grounding is verified. Entailment validation and a measured grounded-answer
evaluation remain required before making that claim. No general model
knowledge is intentionally invited to fill gaps, but prompt wording is not
proof that it did not do so.

## Provider contracts

- `EmbeddingProvider.embed(texts, task)` returns one finite vector per input,
  with configured dimensions and model identity.
- Gemini Embedding 2 query inputs use the `task: search result | query:` form;
  corpus text uses `title: ... | text: ...`. Keep these paired formats
  consistent when indexing and querying.
- `Generator.generate(question, authorized_evidence, schema)` returns typed
  candidate claims and references. It cannot retrieve or call tools.
- Model IDs, dimensions, limits, and timeouts come from configuration. Provider
  errors and malformed responses are bounded failures, not reasons to widen
  retrieval or retry indefinitely.

## Evaluation

Track retrieval relevance/recall on a versioned synthetic set, source-type
coverage, cross-modal hit rate, citation validity, grounded-answer rate,
authorized context violations (must be zero in tests), latency, and query
plans. `apps/api/scripts/evaluate_local_retrieval.py` executes five query cases
plus a direct RLS check against the local seeded corpus and reports Recall@12,
MRR, latency, and forbidden-source hits. The current run measured Recall@12
1.0, MRR 0.775, and zero authorization violations on this small synthetic
set. Treat it as a smoke evaluation, not a representative benchmark.
