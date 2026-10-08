# Review Needed

This file tracks open issues that require external state, database evidence,
or deeper review. It does not certify the system as secure.

## R-001 — RLS-aware retrieval

- **Implemented:** the API verifies the Supabase bearer session and forwards
  that same token to the invoker retrieval RPC; query code does not use the
  secret key. The draft migration now enables RLS on every app table, removes
  default API-role table privileges before regranting required reads, and
  explicitly restricts retrieval RPC execution to authenticated users.
- **Unverified:** the migration has not been applied; Supabase request identity
  propagation, policy behavior inside the RPC, and database roles/grants have
  not been tested against PostgreSQL.
- **Next review:** apply only after CLI/connectivity are available; test
  finance allow and HR/other-organization denial at retrieval, citation lookup,
  and exact model-context boundaries.
- **Temporary behavior:** do not describe a live RLS allow/deny result or
  enable demo role switching.

## R-002 — Filtered HNSW recall and query plans

- **Implemented:** HNSW and full-text indexes plus an invoker hybrid retrieval
  RPC are drafted.
- **Unverified:** installed pgvector version, filtered candidate recall,
  iterative scan settings, query plans, and latency have not been measured.
- **Next review:** benchmark authorized filtered queries and inspect query
  plans under representative ACL selectivity. Consider an exact authorized
  fallback if approximate retrieval underfills.

## R-003 — Demo identity lifecycle

- **Implemented:** real Supabase password sign-in, server route gate, and
  authenticated API calls. The client cannot submit role, user, organization,
  ACL, or evidence fields in a query.
- **Missing:** seeded NovaCore users and a server-verified demo identity
  switch. The UI does not offer a role selector.
- **Next review:** create five seeded identities and verify the session switch
  mechanism is demo-only and changes the actual auth session.

## R-004 — Ingestion and source storage

- **Missing:** PDF extraction, image OCR, structured-row normalization,
  private original-file storage, ingestion jobs, and transactional ACL/index
  writes. No privileged ingestion path has been added while the current RLS
  contract is unverified.
- **Next review:** define a narrowly authorized write path and test uploaded
  source provenance and access inheritance before exposing ingestion UI.

## R-005 — Live provider and database connectivity

- **Observed:** credential values are present in ignored local configuration;
  Supabase URL and publishable key match. The web env file now contains only
  the public Supabase pair and API base URL.
- **Blocked:** DNS resolution failed for the provider hosts; authenticated
  read-only requests returned a URL resolution error before receiving HTTP
  responses. Credentials were not accepted or rejected during these attempts.
- **Next review:** repeat provider checks once DNS/network is available. Do not
  print credentials or response bodies.

## R-006 — Exact model-context authorization proof

- **Implemented:** six local unit tests verify bounded prompt context,
  rejection of forged citation IDs, exact source locations, and fail-closed
  claim filtering.
- **Unverified:** tests do not exercise a live Supabase RLS policy or prove
  that unauthorized rows cannot be returned by the database. Python service
  dependencies could not be downloaded in this environment.
- **Next review:** add database-backed finance/HR/cross-organization tests and
  capture the actual evidence objects passed to the model.

## R-007 — Semantic claim support

- **Implemented:** generated citation IDs must belong to the exact bounded
  model context and citations need a precise source location. The response
  state is `CITATION_VALIDATED` to describe that boundary accurately.
- **Missing:** the service does not establish that a cited passage entails the
  model's claim. Prompt instructions and citation membership alone do not
  prove grounding.
- **Next review:** define and measure claim-level support checks, including
  adversarial and prompt-injection cases, before labeling answers grounded.
