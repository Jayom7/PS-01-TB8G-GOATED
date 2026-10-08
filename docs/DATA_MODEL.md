# Data Model

The schema is a planned relational model. UUID primary keys are used for
application entities; natural business identifiers remain separate fields.

## Identity and policy

- `profiles(user_id PK/FK auth.users, display_name, active, created_at)`
- `organizations(id, name, created_at)`
- `organization_memberships(organization_id, user_id, status)` with a unique
  `(organization_id, user_id)` key.
- `roles(id, key UNIQUE, label)` and `permissions(id, key UNIQUE)`.
- `role_permissions(role_id, permission_id)` and
  `user_roles(user_id, organization_id, role_id)` with composite uniqueness.
- `documents(id, organization_id, title, source_name, source_uri, media_type,
  classification, created_by, created_at)`.
- `document_acl(document_id, subject_type, subject_id, permission)` where
  subject type is user or role and permission is allow/read. Organization
  membership is still mandatory; ACL does not cross tenant boundaries.
- `structured_records(id, organization_id, table_name, row_key, record_type,
  classification, fields JSONB, source_name, created_at)` with unique
  `(organization_id, table_name, row_key)`.
- `record_acl(record_id, subject_type, subject_id, permission)` for row-level
  grants where table-level role policy is insufficient.

## Provenance and unified index

- `document_versions(id, document_id, storage_key, checksum, version, created_at)`
- `knowledge_chunks(id, organization_id, source_type, document_id NULL,
  record_id NULL, source_version_id NULL, source_name, source_title,
  page_number NULL, image_id NULL, region JSONB NULL, row_key NULL, ordinal,
  content, metadata JSONB, classification, embedding vector(1536),
  search_vector tsvector, created_at)`.

Constraints require exactly one canonical parent (`document_id` or
`record_id`) compatible with `source_type`; document-derived image OCR may
reference a document version and an image asset. Stable `knowledge_chunks.id`
is the citation/evidence identifier. `metadata` may contain only information
authorized with the parent resource. File paths are opaque storage keys, not
public URLs.

Every item preserves provenance sufficient for a precise citation: PDF page
and chunk ordinal; image identity and OCR bounding region; or structured table
and row key. Original source bytes are stored separately and referenced by
version/checksum. Typed source details can live in the parent records rather
than duplicating every business field in chunks.

## Business demo records

Use minimal synthetic domain tables: `customers`, `invoices`, `payments`,
`employees`, `projects`, and `orders`, each with `organization_id`, stable
primary key, timestamps, and only the fields needed for the demo. A source row
is indexed into `knowledge_chunks` with a deterministic textual rendering and
a foreign key to its source row. Sensitive HR and finance records receive
distinct role grants. Demo relationships use foreign keys and synthetic IDs.

## Audit

`audit_logs(id, request_id, user_id, organization_id, action, answer_state,
model_id, authorized_retrieval_count, source_ids JSONB, elapsed_ms, created_at)`.
Store no raw query by default and no source content. Audit reads have a separate
administrative policy; a judge-facing trace is derived from safe per-request
events and never includes denied resource details.

## Indexing and constraints

- B-tree indexes on organization, parent IDs, row keys, source type, and ACL
  subject lookups based on observed query plans.
- GIN index for `search_vector`.
- HNSW on `embedding vector_cosine_ops`, initially, with a migration/config
  that matches the chosen dimensionality.
- Composite constraints enforce tenant consistency between chunk and parent.
- Foreign keys prevent orphaned provenance; deletion/versioning policy must
  avoid stale citations.
- RLS is enabled on all exposed tables. Policy behavior must be tested as the
  actual authenticated database role, not only as an owner.

## Authorization inheritance

Document-derived chunks inherit organization, classification, and document
ACL from their canonical parent through database policy predicates. Structured
record chunks inherit row-level policy from their record. If policy is
materialized on each chunk for query performance, writes must be transactional
and consistency tests must prove grants and revocations stay synchronized.
The first implementation should prefer deriving policy from the parent until
benchmarks justify materialization.
