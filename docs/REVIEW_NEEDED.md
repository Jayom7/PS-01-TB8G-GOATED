# Review Needed

This file tracks open issues that require external state, database evidence,
or deeper review. It does not certify the system as secure.

## R-001 — RLS-aware retrieval

- **Implemented:** the API verifies the Supabase bearer session and forwards
  that same token to the invoker retrieval RPC; query code does not use the
  secret key. The migration enables RLS on every app table, removes default
  API-role table privileges before regranting required reads, and restricts
  retrieval RPC execution to authenticated users.
- **Verified locally:** migration applied to local Supabase; 17 pgTAP assertions
  pass for RLS, grants, RPC execution, finance allow, HR denial, source
  visibility, and cross-organization isolation. Local schema lint passes.
- **Unverified on hosted project:** Supabase CLI authentication is missing, so
  hosted migration, request identity propagation, policies, and grants have
  not been checked there.
- **Next review:** authenticate Supabase CLI, link the existing project, apply
  the migration, then run the allow/deny suite against hosted state.
- **Boundary:** local allow/deny results do not verify the hosted project.
  Role switching is enabled only in the loopback local demo.

## R-002 — Filtered HNSW recall and query plans

- **Implemented locally:** HNSW and full-text indexes plus an invoker hybrid
  retrieval RPC are applied and exercised against local Supabase.
- **Verified locally:** synthetic evaluation reports Recall@12 1.0 and MRR
  0.775 over five retrieval cases, zero authorization violations, valid
  provenance for all 39 returned citations, and OCR, structured, and
  cross-modal retrieval coverage.
- **Unverified:** this sample is too small for production conclusions;
  filtered candidate recall, iterative scan settings, `EXPLAIN` plans, and
  representative latency have not been measured.
- **Next review:** benchmark authorized filtered queries and inspect query
  plans under representative ACL selectivity. Consider an exact authorized
  fallback if approximate retrieval underfills.

## R-003 — Demo identity lifecycle

- **Implemented:** real Supabase password sign-in, server route gate, and
  authenticated API calls. The client cannot submit role, user, organization,
  ACL, or evidence fields in a query.
- **Verified locally:** five NovaCore auth users, profiles, and role records
  were created in local Supabase. CEO-to-Finance and Finance-to-HR switching
  returned new Supabase sessions and updated the resolved API role. Local
  credentials are stored separately in a git-ignored owner-only file. No
  hosted users were created.
- **Boundary:** switching is only enabled when both local Supabase and the
  ignored demo credential file are present. Do not enable this broker for a
  hosted project.

## R-004 — Ingestion and source storage

- **Implemented locally:** bounded PDF extraction, scanned-page/image OCR,
  structured-row normalization, Gemini embeddings, CEO-gated local upload and
  structured ingestion routes, private original-file storage, and role grants.
  PaddleOCR was exercised on the synthetic invoice scan.
- **Not implemented:** background ingestion jobs. The local upload and
  service-key persistence paths have not been reviewed for hosted deployment.
- **Next review:** exercise uploaded file/structured flows end to end and
  review source provenance, write rollback, and access inheritance before any
  hosted ingestion deployment.

## R-005 — Live provider and database connectivity

- **Verified:** Supabase Auth settings and Gemini model/embedding checks
  returned HTTP 200; live embedding produced 1536 dimensions. A live Finance
  answer succeeded with Gemini 3.8 Flash and two citations. Later, Gemini
  generation returned 503 `UNAVAILABLE` and timed out on both configured
  models during an adversarial prompt run; the final live provider result is
  therefore incomplete.
- **Blocked:** hosted database migration and schema checks require Supabase CLI
  authentication or direct database credentials. Current API keys alone do
  not provide the CLI project token or database password.

## R-006 — Exact model-context authorization proof

- **Verified locally:** API tests confirm the model receives exactly the RPC
  result, pgTAP confirms finance/HR/cross-organization database boundaries,
  and retrieval evaluation reports zero forbidden-source hits.
- **Unverified on hosted project:** repeat these checks after applying the
  migration to the connected hosted project.

## R-007 — Semantic claim support

- **Implemented:** generated citation IDs must belong to the exact bounded
  model context and citations need a precise source location. The response
  state is `CITATION_VALIDATED` to describe that boundary accurately.
- **Missing:** the service does not establish that a cited passage entails the
  model's claim. Prompt instructions and citation membership alone do not
  prove grounding.
- **Next review:** define and measure claim-level support checks, including
  adversarial and prompt-injection cases, before labeling answers grounded.
