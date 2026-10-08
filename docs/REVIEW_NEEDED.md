# Review Needed

Status snapshot: 2026-10-08. This file distinguishes repository facts,
historical run evidence, and current blockers. It is not a security certificate.

## Current runtime blockers

- **Docker:** `docker` client is installed, but `docker info` fails while
  connecting to `/Users/Jayom/.docker/run/docker.sock` with permission denied.
  The local Supabase server cannot be verified or started in this session.
- **Supabase CLI:** root manifest declares `supabase` as a dev dependency, but
  `node_modules/.bin/supabase` is absent/broken in this checkout. The dependency
  install flow has not been rerun. No remote-database fallback is appropriate.
- **API/web:** Python environment and web Next executable are present. This
  pass has not started either server; prior API/web/browser results below are
  historical, not live checks of the modified code.
- **Gemini:** earlier real attempts reached retrieval but Gemini returned 429.
  No new live call was made in this pass. Dashboard status means configured,
  not available. The code now stops after one request on 429 and returns a
  rate-limit-specific safe error.
- **Hosted Supabase:** hosted migration/policies remain unverified; no hosted
  credentials or CLI authorization were used.
- The ignored owner-only `.local-demo-credentials.json` and
  `data/local/evaluation.json` exist. Their contents were not disclosed or
  committed. The five passwords remain local in the ignored credentials file.

## Historical local verification (do not present as current runtime proof)

Previous recorded sessions reported: local migration applied; 24 pgTAP
assertions passed for grants/RLS/RPC, five-role allow/deny, forged context,
cross-organization isolation, and unauthorized source lookup; local schema lint
passed; 36 API tests and Ruff passed; six synthetic evaluation cases reported
Recall@12 1.0, MRR 0.775, zero forbidden-source hits/authorization violations,
and 39 citation provenance checks. Prior browser checks covered all six routes,
light/dark, role switching, and 1440x900 / 900x900 / 390x844. A prior real OCR
invoice answer with citation succeeded once using Gemini 3.6; subsequent 3.8
and 3.7 calls returned 429. These are historical notes and not a fresh
verification of this checkout's latest changes.

## Current repository invariants and open review

### Identity, roles, and retrieval

Implemented design: authenticated identity is distinct from active demo
authorization context. There are exactly five roles (CEO, Finance Manager, HR
Manager, Sales Manager, Engineer). Local switching brokers real seeded Auth
sessions server-side and is loopback/credential-file gated. Ordinary retrieval
uses the verified user or brokered role token and invoker RPC/RLS path; normal
query/source paths do not use the secret key. The CEO local ingestion writer is
a separate privileged path.

API tests have historically checked that the generator receives only the
retrieval RPC result, rejects client identity/evidence fields, and never calls
generation for empty authorized retrieval. This is not a proof of hosted RLS
or a separately measured runtime counter. The Security endpoint does not
independently measure unauthorized evidence supplied to the LLM; the UI now
labels it “not independently measured” instead of showing a false zero.

**Stronger-model review:** re-check migration grants/policies and the
`SECURITY INVOKER` RPC; verify all five role allow/deny cases, forged CEO/user/
organization, cross-tenant isolation, source lookup, and exact LLM context
against both local and hosted databases. Review demo token lifecycle, storage
path isolation, RLS side channels, revocation, and privileged ingestion.

### Provider, citations, and semantic support

Configured defaults: Gemini 3.8 Flash primary, Gemini 3.7 Flash fallback,
Gemini Embedding 2 at 1536 dimensions. Settings remain configurable. Fallback
is for timeout/transport/transient 5xx; 429 now stops immediately to avoid
spending a second quota-limited request. Provider access must be retested after
quota/access recovers.

Generation now requests exact supporting excerpts per cited claim. The
deterministic validator checks exact quote inclusion, coarse lexical overlap,
citation membership in the bounded context, and citation location. This may
reject paraphrases and does not prove entailment or detect every contradiction.
Do not call it semantic grounding. No fresh Gemini answer or injection test was
run in this pass.

**Stronger-model review:** design adversarial support/contradiction and prompt
injection evaluation, calibrate quote/lexical checks against real outputs, and
decide whether a separate verifier is justified. Do not claim entailment from
the current checks.

### Retrieval performance and data

Previous six-case synthetic local evaluation is too small for production
quality. Filtered HNSW recall, query plans, concurrency, representative latency,
and fallback behavior under sparse grants have not been measured. RPC time
combines vector/keyword retrieval and RRF ranking. Prior failed Ask timings
showed embedding roughly 0.7–1.1s, retrieval+ranking roughly 18–22ms, and
generation ranging from under one second to over 15s; these are historical
failed attempts, not a fresh benchmark.

**Stronger-model review:** build representative authorization-filtered
benchmarks, examine `EXPLAIN (ANALYZE, BUFFERS)`, validate ANN under selective
grants, and decide whether exact fallback or iterative scans are needed.

### Ingestion and operations

Repository implements page-aware PDF extraction, scanned-page and image OCR,
structured record normalization, embeddings, local private originals, and
role-grant writes. Upload progress is atomic from the UI perspective; there is
no verified per-stage server job status. This pass adds pre-OCR PNG/JPEG header
dimension checks with a 16,000,000-pixel cap. Unit tests must pass before
claiming that guard is verified. Prior local PDF/OCR/structured flows passed.

Hosted file storage, admin key lifecycle, transaction rollback, deletion and
re-index behavior, request/rate limiting, and production background ingestion
need review before deployment.

## Required next evidence

1. Restore access to the Docker socket and pinned repository CLI dependency;
   start local Supabase and confirm migration/seed state.
2. Run current backend tests/Ruff, web lint/typecheck/build, and browser QA on
   all routes and responsive breakpoints.
3. When Gemini quota returns, make one controlled finance query, inspect its
   citation and authorized source excerpt, then repeat as HR and confirm
   insufficient evidence. Do not retry 429 with the fallback model.
4. Repeat local database authorization tests; hosted verification requires
   separate hosted project access and review.
