# Data Model

This describes the SQL in `supabase/migrations/20261008000100_secure_knowledge_index.sql`
and `20261008000200_read_assigned_roles.sql`; it is not a claim that the
migration is currently applied to a reachable or hosted database.

## Tables and relationships

- `organizations`: tenant boundary.
- `profiles`: one row per Auth user, with organization and display name.
- `roles` and `user_roles`: organization-scoped role assignments.
- `documents`: source metadata, type, private storage path, content hash,
  creator, and timestamps.
- `knowledge_chunks`: document-derived text chunks with source type/name/id,
  PDF page, structured row ID, image ID/OCR region, chunk index, metadata,
  generated full-text vector, and 1536-dimensional embedding.
- `access_grants`: read grants at exactly one document or chunk scope, for a
  user, role, or organization principal.

The source types are `pdf`, `image_ocr`, and `structured`. Chunk citation IDs
are UUIDs. Structured citations use table metadata plus `row_id`; PDF citations
use `page_number`; image citations use `image_id` and optional `ocr_region`.

## Authorization and retrieval

RLS is enabled for all seven tables. The `match_knowledge_chunks` RPC is
`SECURITY INVOKER`, has a pinned empty search path, and returns hybrid semantic
and keyword results under caller RLS. Indexes include HNSW vector search,
GIN full-text, organization/source type, and access-grant lookup indexes. This
documents migration contents; local test results and current runtime status are
tracked separately in `REVIEW_NEEDED.md`.

## Deliberate limitations

The current migration uses a common document parent for all three source types;
structured fields are normalized into chunk text/metadata rather than a
separate business-table schema. Original bytes use private storage paths. ACL
inheritance and content writes are implemented by the local ingestion path and
must remain transactionally consistent. Production deletion/version lifecycle,
representative query plans, selective-filter ANN recall, and hosted RLS remain
review items. Do not add speculative schema or alter grant inheritance without
checking the migration, seed code, and authorization tests together.
