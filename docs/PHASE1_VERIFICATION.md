# Phase 1 verification — 2026-10-08

Historical record of local submission hardening on the existing Clearframe
checkout, based on `b0292dc`. The test and evaluation results below were
recorded on 2026-10-08 against the then-current 19-source corpus. On
2026-10-09, the local demo corpus was curated to six sources; the older
evaluation numbers and PDF/OCR modality result do not describe that current
corpus. No presentation, recording, optional winning feature, hosted migration,
or security-control change was performed.

## Changes

- Every supporting quote must match its own authorized, bounded evidence with
  word boundaries. A fabricated additional quote rejects the claim. Mixed
  authorized/unauthorized references also reject the entire claim. Existing
  lexical overlap and source-location checks remain enforced. A bounded
  paid/unpaid/explicit-negation check rejects the reproduced contradiction;
  this does not implement general semantic entailment.
- Rebuilt and restarted local API and production web from this checkout. The
  Security page visibly reports unmeasured evidence and endpoint-unchecked RLS
  status, rather than the older runtime's unsupported zero/active claims.
- Replaced the outdated demo runner with a running-checkout verification suite.
  It checks five-role manifest boundaries, real stored-vector retrieval,
  authorized and forbidden source access, forged contexts, CEO identity
  preservation, and honest Security labels. Real provider checks are separate,
  refuse hosted URLs, and require file-hash-bound synthetic documents first.
- Evaluation uses hit rate@12, MRR, checked forbidden hits, and retrieved
  citation-location presence. Legacy results are relabeled as historical on
  read without rewriting their saved values. New runs archive the old result.
  The Dashboard reports review if any recorded retrieval case failed.
- Restored the missing `supabase` package/CLI target via lockfile-pinned `npm ci`.
  CLI version 2.120.0 and local status verified. The API launcher now uses an
  absolute app directory, so the documented root-directory command works.
- Confirmed the configured SSH remote `Jayom7/PS-01-TB8G-GOATED` resolves to
  `b0292dc`; the supplied spelling `PS-1-TB8G-GOATED` was not accessible.
  Kept the verified remote and documented the canonical URL.

## Files changed

| File | Purpose |
| --- | --- |
| `apps/api/src/ps01_api/rag.py` | Quote, reference, and payment-status validation |
| `apps/api/src/ps01_api/main.py` | Accurate evaluation labels, history, overall status |
| `apps/api/scripts/run_local_demo.py` | Fresh local security/provider verification suite |
| `apps/api/scripts/evaluate_local_retrieval.py` | Correct metric names and definitions |
| `apps/api/scripts/run_local_api.py` | Root-directory launcher fix |
| `apps/api/scripts/seed_local_demo.py` | Prunes superseded, explicitly tagged synthetic demo sources on local reseed |
| `apps/web/src/components/workspace.tsx` | Evaluation terminology and recorded/fresh labels |
| `apps/api/tests/test_rag.py` | Nine security regression tests |
| `apps/api/tests/test_evaluation.py` | Four metric/history/status tests |
| `apps/api/tests/test_local_startup.py` | Two launcher/hosted-refusal tests |
| `README.md` | Verified runtime, canonical remote, startup and check commands |
| `apps/api/README.md` | Verification runner and metric contracts |
| `docs/RAG_PIPELINE.md` | Current validation and metric limits |
| `docs/REVIEW_NEEDED.md` | Replace stale runtime blockers and record open evidence |
| `docs/PHASE1_VERIFICATION.md` | This handoff |

## Tests added

Nine RAG tests cover paid/unpaid contradictions in both directions and explicit
negation; fabricated and contradictory second quotes; paid as a substring of
unpaid; valid and fabricated multiple-source support; mixed authorized and
unauthorized references; a valid grounded answer; conflicting verified payment
statuses. Four evaluation tests check positive-query hit rate, location metadata
presence, forbidden-hit counting, immutable historical relabeling, recorded
versus fresh status, and a retrieval failure despite zero forbidden hits.
Two startup tests cover the absolute app path and rejecting hosted databases.

## Fresh results

- Backend: **57 passed**; 78 dependency/deprecation warnings, no failed tests.
- Ruff lint and format check: passed across source, scripts, and tests.
- Web ESLint and TypeScript: passed. Next.js production build: passed with all
  six authenticated workspace routes and Proxy included.
- Local database pgTAP: **24/24 passed** in rolled-back test fixtures.
- Local security runner: **41 passed, zero failed, two provider-dependent checks
  blocked**. Stored-vector tests execute real authenticated local RPCs, using
  existing authorized embeddings rather than fresh query embeddings.
- Fresh retrieval evaluation completed at **22:23:53 IST on 2026-10-08**:
  positive-query hit rate@12 **0.75**, MRR **0.625**, zero forbidden hits in the
  checked cases, and **47/47** retrieved citation ID/location presence checks.
  Invoice PDF/OCR and cross-modal retrieval passed. The structured-finance
  query **missed its expected source**. These are small synthetic results,
  not production quality, semantic grounding, or a global security guarantee.
- Browser: current Security labels verified; Evaluation labels checked against
  the freshly recorded result. Broader responsive/interaction QA is not claimed.

## Provider and remaining blockers

The controlled real Ask request successfully embedded the query and retrieved
authorized evidence. Generation returned **HTTP 503** after the configured
fallback path. It therefore produced no verified grounded answer or successful
answer-source inspection. HR refusal remains unverified. No output was mocked
or substituted, and no repeat generation calls were made after that failure.

Automatic review initially rejected a provider run because its payload boundary
was not explicit. Local-only verification then proved every visible document
was a marked synthetic fixture with a matching file hash. The bounded provider
run was subsequently approved and executed; automatic review is no longer the
blocker. Hosted Supabase was not accessed or verified.

The structured-finance retrieval miss must be diagnosed before claiming full
retrieval acceptance. The paid/unpaid guard remains deliberately narrow;
general entailment and adversarial document-injection evaluation remain open.

## Saved evidence and rerun

Ignored, owner-readable evidence:

- `data/local/security-verification.json`: final local-only run, explicitly
  incomplete for generation/HR refusal.
- `data/local/security-verification-2026-10-08T16-48-45.170835+00-00.json`:
  actual provider attempt and its blocked outcome.
- `data/local/evaluation.json`: fresh schema-2 retrieval result.
- `data/local/evaluation-history-*.json`: unchanged historical result.
- `data/local/phase1-security.png`, `data/local/phase1-evaluation.png`:
  browser proof of the changed labels.

From the repository root, with the documented local API/web running:

```sh
.venv/bin/python apps/api/scripts/run_local_demo.py
```

Exit 0 means complete pass; 1 means failed checks; 2 means incomplete/blocked.
`--skip-generation` deliberately leaves the two provider-dependent checks
blocked. It does not claim a complete end-to-end pass.

## Exact next recommended phase

**Phase 1B — close the remaining submission acceptance gates:** diagnose the
structured-finance top-12 miss without weakening RLS; restore reliable Gemini
generation; run one real grounded finance answer with authorized source
inspection and HR refusal; then repeat targeted authorization and browser
acceptance checks. After these gates pass, move to Section C's semantic-support
and retrieved-document injection evaluation. Presentation and optional winning
features remain deferred.
