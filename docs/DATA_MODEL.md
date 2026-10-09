# Data Model

Five additive migrations define 17 public application tables and are applied/tested locally (55 pgTAP assertions). Hosted deployment remains unverified.

| Boundary | Tables / relationships |
|---|---|
| Identity | organizations, profiles, roles, user_roles |
| Unified evidence | documents, knowledge_chunks, access_grants |
| Relational origin | customers, invoices, payments, purchase_orders, projects, employees, opportunities |
| History | query_history: actor, org, active_role, conversation UUID, query, response, timestamps, deleted_at |
| Audit and deletion | security_events (server-written actor/org/context metadata); source_cleanup_jobs (server-only private-file cleanup intent) |

Business primary keys combine organization and business ID. Composite foreign keys bind sources to the same organization; invoices reference customers, payments reference invoices/customers, and purchase orders reference projects. Money uses nonnegative integer minor units; invoice status is paid/unpaid; dates use PostgreSQL date columns.

All tables enable RLS. Typed rows inherit document grants; in this demo each structured source contains one business row. The `structured_records` union view uses `security_invoker=true`. Structured chunks additionally require an existing authorized origin row with identical canonical fields. Row edits/deletion therefore hide stale index representations until explicitly reindexed. There is no automatic reindex worker.

Knowledge chunks preserve PDF page, structured table/row, or image/OCR region. PDF/OCR chunks support individual chunk grants as well as document grants. Structured typed evidence currently requires its origin document grant; chunk-only structured grants are intentionally insufficient for origin-row visibility. Originals always require document access.

`match_knowledge_chunks` retains invoker security, pinned search path, HNSW cosine index, GIN full-text index, and hybrid ranking. The API performs no broad privileged retrieval followed by filtering.

History RLS requires Auth ownership and profile organization. The API additionally scopes active role. Response updates and hard delete are not granted to authenticated users; only `deleted_at` can be updated. Reopen independently reauthorizes evidence and reconstructs excerpts, including legacy/client-written rows.

The service-only SECURITY INVOKER delete_local_source RPC validates real CEO organization membership and locks the source. Cascades remove chunks, grants and typed rows; referenced relational parents abort the transaction rather than orphan children. Audit and cleanup intent are committed together. The API deletes only paths contained within data/private/ingest and marks jobs complete; seed fixtures are retained but protected by the now-absent source grant. Audit clients have SELECT only, with actor/organization RLS; the API additionally scopes context. No source content, keys or request bodies are stored in security_events.

`20261009000300_exact_identifier_retrieval.sql` replaces the existing invoker RPC without changing permissions, tables or stored data. Exact invoice queries search authorized matching documents; nonmatching full-text rows receive no keyword rank bonus.
