# Final Luna 6 Functionality Pass

**Scope:** audit and continuation of `FINAL LUNA 6 HIGH — LIMITED USAGE /
FUNCTIONALITY PASS`, from the existing implementation onward. This records
verified behavior and remaining blockers; it is not a production-readiness
claim.

## Outcome

The majority of the requested functional pass was already implemented in the
existing commits. This continuation corrected the chat model order to match the
prompt (Gemini 3.8 primary, Gemini 3.7 fallback), refreshed stale ingestion and
provider findings, and fixed the browser file input so a successfully uploaded
file can be selected again. The pass is **not fully complete**: current Gemini
chat requests are rate-limited, hosted Supabase remains unverified, and a second
image upload through the browser UI could not be completed in this pass.

## Requirements and evidence

| Prompt area | Status and evidence |
| --- | --- |
| Demo identity and authorization | Implemented and verified locally. Authenticated identity is separate from the five controlled CEO, Finance, HR, Sales, and Engineer contexts. API tests and local pgTAP cases cover allowed/denied access, forged role/org claims, cross-organization isolation, and unauthorized citation lookup. Browser role changes preserved the signed-in identity and showed context-specific source counts. |
| Account menu | Implemented. Bottom-left account menu shows authenticated identity, active demo context, role switcher, theme control, and “Log out”; there is no duplicate user control in the top header. Verified in browser. |
| Ask and provider reliability | Pipeline reports auth, embedding, retrieval+database ranking, generation, citation validation, and total timings. It avoids returning fabricated answers and distinguishes insufficient evidence and provider failures. A prior live answer with an OCR citation succeeded using Gemini 3.6. Current 3.8/3.7 probes both returned HTTP 429, so a current successful live Ask is blocked. |
| Ask interaction | Implemented: conversation flow, compact clickable citations, on-demand source preview, state-preserving source panel, duplicate-submit prevention, Enter submission, loading feedback, and readable errors. Previously verified in browser. Current provider quota prevented a fresh answer in this pass. |
| Dashboard | Implemented with live identity/context, authorized source/chunk/record counts, system status, recent query, evaluation/security state, and shortcuts. Browser-rendered against local data. |
| Sources | Implemented and browser-verified for search, type filters, authorized-only listing, source opening, and excerpts. Finance/HR role checks showed restricted records were absent from unauthorized results. |
| Ingestion | PDF UI upload succeeded and showed “Indexed” with one chunk; direct API checks indexed a synthetic PDF, an OCR image, and a structured record. All test rows/files/artifacts were removed. CEO/admin gating and validation are implemented. Exact per-stage server progress is not implemented. A same-file selection reset was added after success; a second browser image selection could not be completed. |
| Security | Implemented with authenticated identity/context, effective scope, local RLS state, unauthorized-evidence count, recent retrieval decisions, and security checks. No numeric security score is claimed. A fresh live retrieval trace was empty after restarting the API because no current Gemini Ask succeeded. |
| Evaluation | Implemented with retrieval metrics, authorization checks, citation provenance, and latency separated conceptually. Latest local synthetic suite: Recall@12 1.000, MRR 0.775, zero authorization violations, and 39 citation provenance checks. It explicitly does not measure semantic answer quality. |
| Responsive/sidebar | Browser verified at 1440×900, 900×900, and 390×844. Sidebar remained viewport-height with independent main scrolling; mobile navigation opened within the viewport. |
| Light/dark theme | Both themes toggled and remained readable in browser; selected navigation and semantic states remained visible. Palette is recorded in `REVIEW_NEEDED.md` for the next visual phase. |
| Routes | `/dashboard`, `/ask`, `/sources`, `/ingest`, `/security`, and `/evaluation` rendered on direct navigation and refresh. |
| RLS/security tests | Local migration and 24 pgTAP assertions passed. These demonstrate local state only; hosted project policies were not checked. |
| Git | Existing pass commit was already pushed. This continuation’s changes are intended to be committed and pushed after final checks. |

## Measured Ask latency

These were real requests against the local app and current provider key. They
ended in provider errors, so they are latency measurements for failed attempts,
not answer-generation performance or an improvement claim.

| Attempt | Auth/session | Embedding | Retrieval + DB ranking | Gemini | Citation validation | Total | Outcome |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Gemini 3.8 attempt | 132.8 ms | 715.3 ms | 21.6 ms | 757.6 ms | 0.0 ms | 1,649.2 ms | Provider error (429/503 path); no answer |
| Gemini 3.7 then 3.8 fallback | 39.5 ms | 1,074.8 ms | 17.5 ms | 2,365.5 ms | 0.0 ms | 3,505.8 ms | HTTP 429; no answer |
| Gemini 3.7 then 2.5 compatibility probe | 69.8 ms | 779.0 ms | 22.0 ms | 15,803.1 ms | 0.0 ms | 16,705.5 ms | HTTP 404; no answer; 2.5 removed from config |

The pipeline records database retrieval and ranking together; a separate
ranking-only duration was unavailable. The final configuration is
`gemini-3.8-flash` primary and `gemini-3.7-flash` fallback, as requested.
Embedding remains `gemini-embedding-2` at 1536 dimensions. The supplied AI
Studio screenshot showed the 3.8 daily request count above its displayed cap;
live 3.8 and 3.7 requests returned 429. Do not increase timeouts or select a
weaker model to mask this quota condition.

## Verification recorded

- API suite: 36 passed.
- Ruff: passed.
- Web lint, TypeScript check, and production build: passed in the preceding
  verification pass; no frontend source changed there except the file-input
  reset in this continuation, so these checks are rerun for this commit.
- Local Supabase database tests: 24 pgTAP assertions passed; local schema lint
  reported no errors in the preceding pass. No schema changed in this
  continuation.
- Local PDF, image/OCR, and structured ingestion checks passed; temporary
  synthetic test data was cleaned up.
- `git diff --check` and clean/pushed status are checked at final handoff.

## Remaining work / Sol 6 or Plus handoff

1. After quota reset or billing/access change in Google AI Studio, run one
   controlled Ask with 3.8 and confirm a current answer, citations, and source
   preview; then measure successful end-to-end latency. Current Gemini chat is
   not usable under the observed quota state.
2. Authenticate Supabase CLI, identify the intended hosted project, inspect
   migration history and data, and then repeat migration/RLS allow-deny checks
   against hosted state. No hosted changes were made.
3. Recheck repeat image/PDF selection in the browser with the input-reset fix;
   add server-driven ingestion stage progress if needed.
4. Sol 6/Plus: apply the premium brand/typography/spacing direction; deepen
   semantic claim-entailment and adversarial prompt-injection evaluation; test
   ANN recall/query plans at representative scale; conduct the deeper hosted
   RLS review. The existing concise palette and scope notes are in
   `docs/REVIEW_NEEDED.md`.

The app is a locally verified demo slice. Hosted security, current live Gemini
answering, representative-scale retrieval, and semantic entailment remain
unverified or incomplete.
