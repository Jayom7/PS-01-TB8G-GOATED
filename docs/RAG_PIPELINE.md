# RAG Pipeline

## Ingestion

1. Authenticate the ingestion actor and validate source type, size, and media
   type. Compute checksum and retain original bytes in private object storage.
2. PDF adapter extracts page text with PyMuPDF; scanned pages may pass through
   the OCR adapter. Image adapter runs local OCR and preserves page/image ID,
   bounding boxes, confidence where available, and original asset reference.
3. Structured adapter reads allowlisted demo tables and preserves table name,
   stable row key, typed fields, and row ACL metadata. Render a deterministic
   searchable text form; never replace typed provenance with prose alone.
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
   authorization selectivity. Keep this as an open review item until SQL,
   `EXPLAIN`, recall, and deny tests exist.

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
- `Generator.generate(question, authorized_evidence, schema)` returns typed
  candidate claims and references. It cannot retrieve or call tools.
- Model IDs, dimensions, limits, and timeouts come from configuration. Provider
  errors and malformed responses are bounded failures, not reasons to widen
  retrieval or retry indefinitely.

## Evaluation

Track retrieval relevance/recall on a versioned synthetic set, source-type
coverage, cross-modal hit rate, citation validity, grounded-answer rate,
authorized context violations (must be zero in tests), latency, and query
plans. Publish only results produced by executable evaluation runs, with set
version and configuration. No benchmark results exist yet.
