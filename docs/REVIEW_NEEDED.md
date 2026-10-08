# Review Needed

This file records questions that require implementation evidence or deeper
review. It does not certify the system as secure.

## R-001 — RLS-aware vector retrieval

- **Implemented:** draft invoker RPC and RLS policies in the first migration.
- **Uncertainty:** exact Supabase/PostgreSQL request identity propagation,
  policy behavior inside vector queries, and whether policy joins preserve
  least privilege and useful plans. Policy composition has not been reviewed
  against a live PostgreSQL instance.
- **Evidence:** SQL is drafted but has not been applied or tested. Current
  Supabase guidance says HNSW scans can return fewer rows after selective
  filters and pgvector 0.8.0+ supports iterative scans; there are no local
  authorization tests or measurements.
- **Deeper review:** inspect actual migrations/function privileges and test
  queries as authenticated identities, including tenant and row ACL cases.
- **Safer temporary behavior:** deny-by-default; do not ship privileged
  retrieval or pass any unverified evidence to generation.

## R-002 — Filtered HNSW recall and query-plan behavior

- **Implemented:** draft HNSW and full-text indexes with hybrid candidate query.
- **Uncertainty:** candidate recall under selective ACLs, installed extension
  version, iterative scan support/settings, and when exact search is needed.
- **Evidence:** official docs describe the tradeoff; no local migration run,
  authorization tests, measurements, or query plans exist.
- **Deeper review:** benchmark authorized result recall/latency and inspect
  `EXPLAIN (ANALYZE, BUFFERS)` under representative roles/selectivity.
- **Safer temporary behavior:** do not report retrieval quality or metrics;
  prefer an exact authorized query if approximate filtering is not validated.

## R-003 — Demo identity switching

- **Implemented:** no authentication flow exists.
- **Uncertainty:** competition-friendly demo switching must not create a
  production role-escalation path or trust a client-set role.
- **Evidence:** interface contract requires a server-verified demo identity;
  no session mechanism is implemented.
- **Deeper review:** verify demo-only gating and seeded identity credentials.
- **Safer temporary behavior:** keep demo switching disabled outside explicit
  demo mode; never simulate role changes solely in UI state.
