# Review Needed

Status snapshot: 2026-10-08. This file distinguishes repository facts,
historical run evidence, and current blockers. It is not a security certificate.

## Current Phase 1 state

- Docker and the local Supabase containers are running. Both repository migrations
  are applied. The earlier socket error was a sandbox restriction, not evidence
  that Docker was stopped. The restored repository CLI is version 2.120.0.
- API/web have been rebuilt and restarted from this checkout. The live Security
  page now says RLS status was not checked by that endpoint and unauthorized
  evidence is not independently measured. It does not show an unmeasured zero.
- Fresh pgTAP: 24/24. Fresh five-role local manifest allow/deny, stored-vector RPC,
  allowed/forbidden source lookup, forged CEO context, and CEO identity/context
  preservation checks passed. Stored-vector smoke checks are not fresh query
  embedding or a representative retrieval benchmark.
- The controlled real Gemini attempt embedded the question and retrieved
  authorized evidence, but generation returned HTTP 503 after the fallback path.
  No generated answer/source-inspection success or HR refusal is claimed.
- Fresh schema-2 retrieval evaluation: hit rate@12 0.75, MRR 0.625, zero
  forbidden hits in the checked cases, 47/47 citation-location presence. The
  structured-finance query missed its expected source; this is not a full pass.
- Hosted Supabase remains unverified. No hosted migration or credentials were used.
- See `PHASE1_VERIFICATION.md` and ignored `data/local/security-verification.json`
  for the fresh evidence, separate from prior recorded runs.

## Historical local verification (do not present as current runtime proof)

Previous recorded sessions reported: local migration applied; 24 pgTAP
assertions passed for grants/RLS/RPC, five-role allow/deny, forged context,
cross-organization isolation, and unauthorized source lookup; local schema lint
passed; 36 API tests and Ruff passed; six synthetic evaluation cases reported
hit rate@12 1.0 (previously mislabeled Recall@12), MRR 0.775, zero
forbidden-source hits in the checked cases, and 39 retrieved citation ID/location
presence checks (previously overstated as provenance checks). Prior browser checks covered all six routes,
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
Do not call it semantic grounding. A fresh Gemini request failed with HTTP 503 during generation. No fresh answer
or live injection outcome is claimed.

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
dimension checks with a 16,000,000-pixel cap. Current unit tests verify the
header guard; decoded-image behavior remains an open review item. Prior local PDF/OCR/structured flows passed.

Hosted file storage, admin key lifecycle, transaction rollback, deletion and
re-index behavior, request/rate limiting, and production background ingestion
need review before deployment.

## Required next evidence

1. Restore reliable Gemini generation, then run `run_local_demo.py` without
   `--skip-generation` to complete the grounded answer/source inspection and HR
   refusal checks. Do not loop on 429 or substitute mock success.
2. Run an adversarial semantic-support and document-injection evaluation. The
   fixed quote bypass and bounded paid/unpaid guard do not prove general entailment.
3. Complete broader responsive UI and ingestion lifecycle verification before
   submission; Phase 1 browser checks focus on the changed Security/Evaluation states.
4. Hosted allow/deny verification requires separate project access; local results
   do not establish hosted policies.
