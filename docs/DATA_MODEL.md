# Data Model

The three migrations define 15 public application tables. The new `20261009000100_relational_evidence_history.sql` is additive and unapplied/unverified in this pass.

| Boundary | Tables / relationships |
|---|---|
| Identity | organizations, profiles, roles, user_roles |
| Unified evidence | documents, knowledge_chunks, access_grants |
| Relational origin | customers, invoices, payments, purchase_orders, projects, employees, opportunities |
| History | query_history: actor, org, active_role, conversation UUID, query, response, timestamps, deleted_at |

Business primary keys combine organization and business ID. Composite foreign keys bind sources to the same organization; invoices reference customers, payments reference invoices/customers, and purchase orders reference projects. Money uses nonnegative integer minor units; invoice status is paid/unpaid; dates use PostgreSQL date columns.

All tables enable RLS. Typed rows inherit document grants; in this demo each structured source contains one business row. The `structured_records` union view uses `security_invoker=true`. Structured chunks additionally require an existing authorized origin row with identical canonical fields. Row edits/deletion therefore hide stale index representations until explicitly reindexed. There is no automatic reindex worker.

Knowledge chunks preserve PDF page, structured table/row, or image/OCR region. PDF/OCR chunks support individual chunk grants as well as document grants. Structured typed evidence currently requires its origin document grant; chunk-only structured grants are intentionally insufficient for origin-row visibility. Originals always require document access.

`match_knowledge_chunks` retains invoker security, pinned search path, HNSW cosine index, GIN full-text index, and hybrid ranking. The API performs no broad privileged retrieval followed by filtering.

History RLS requires Auth ownership and profile organization. The API additionally scopes active role. Response updates and hard delete are not granted to authenticated users; only `deleted_at` can be updated. Reopen independently reauthorizes evidence and reconstructs excerpts, including legacy/client-written rows.
