# Implementation Plan

This plan prioritizes a reliable vertical slice toward the stated ~70%
prototype milestone. Every phase has a clear proof boundary; no phase is
complete by documentation alone.

## 0. Foundation (current)

- Architecture/security/data/API/demo contracts and repository hygiene.
- Evidence: docs, `.gitignore`, safe `.env.example`, initial README/log.
- Remaining: local Git commit and GitHub setup.

## 1. App and database skeleton

- Create Next.js and FastAPI apps, local Supabase config, ordered migration,
  typed environment settings, health endpoint, and synthetic seed plan.
- Add dependency locks, basic lint/type checks, API unit test setup.
- Exit: clean install/build and migration application in a Docker-enabled env.

## 2. Identity and authorization base

- Supabase Auth session, profiles/roles/organizations, RLS policies, user-scoped
  API database access, role-specific demo identities.
- Exit: database allow and deny tests for finance/HR/organization boundaries.

## 3. Unified ingestion

- PDF parsing, image OCR, and structured-row adapters all emit `KnowledgeUnit`.
- Store originals privately; preserve provenance/ACL; make ingestion idempotent.
- Exit: fixtures of each source type pass validation and map to one index.

## 4. Embeddings and unified retrieval

- Gemini provider adapter with configurable model/dimension; pgvector and
  full-text search; one `SecureRetriever`; rank fusion.
- Exit: cross-modal authorized retrieval and filtered-search recall evidence.

## 5. Grounded generation and citations

- Gemini Flash adapter, typed output, immutable authorized context, citation
  validation, insufficient-evidence behavior, exact source lookup.
- Exit: evidence-context tests, citation tests, malformed/provider failure tests.

## 6. Judge UI and demo

- Use Superdesign to explore the new product UI before implementation; then
  build responsive accessible chat, source preview, trace, demo identity switch,
  and measured evaluation view against real API state.
- Exit: allowed and denied live demo flows with keyboard-friendly controls.

## 7. Evaluation and review

- Versioned retrieval set, latency/query-plan measurements, security tests,
  setup docs, attribution, development log, and bounded architecture review.
- Exit: report only executed evidence, document remaining review issues, tag
  the ~70% milestone only if every acceptance item is demonstrated.

## Deferred

Advanced reranking, performance tuning, production hardening, deployment,
complex policy exceptions, and final adversarial/RLS audit remain deferred to
measured need or deeper review. Do not mark the project competition-ready
without those reviews and observed test evidence.
