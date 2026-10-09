# Clearframe master acceptance — 2026-10-09

Resumed the preserved main checkout at implementation milestone `20b0b36` (original entry `8305326`). Completed phases 0–9 in order, then repaired newly exposed runtime defects. Historical intermediate logs are retained below; this matrix supersedes their earlier blocked states. PASS always refers to the stated executed scope.

## Final phase acceptance

| Phase / requirement | Status | Exact implementation and evidence |
|---|---|---|
| 0 Git, reports, architecture, services, reproduction | PASS | Inspected current branch/diff/reports; restored existing Docker/services without reseeding/reset. Reproduced real timeout/503 and fresh-source ranking defects. Existing origin retained; hosted Supabase untouched. |
| 1 Session refresh, rejection, recovery, logout | PASS | `sessionToken` / `authorizedFetch`, SSR proxy; 5 node tests. Actual invalid refresh token on resume led to public login, then successful login. Actual logout/recovery exchange verified. Deliberately timed expiry remains NOT RUN. |
| 1 Accurate history/API/profile states | PASS | Distinct session/outage/database/authorization/provider errors, profile retry; real browser failures/recovery. No blanket migration diagnosis. |
| 1 Actor/org/role cache binding and escalation | PASS | `_context_token` actor/org/role key, target rechecks and provisioned local CEO only. 55 SQL assertions and 51 live role/refusal checks; CEO actor unchanged on context switch. |
| 1 Current evidence before each provider attempt | PASS | `revalidate_evidence`, `before_attempt`; revocation/deletion/content-change regressions. Current RLS reads before every fallback. External-call atomicity is explicitly limited. |
| 2 Supported model inventory / embedding | PASS | Real inventory confirmed configured 3.8/3.7 Flash; embedding-2/1536 preserved. Credential-scoped capability cache; no other provider/key/billing change. |
| 2 Bounded fallback and precise failure causes | PASS | `generate_claims`: at most two configured models, low thinking (officially supported), 20s attempt / 45s total default, 250ms backoff. Actual normal API fallback 3.7 Flash returned fresh PDF/typed claims at 09:25:47Z. Per-model status/cause/timing returned. Provider failures remain intermittent. |
| 2 Natural answers and canonical claim citations | PASS | Real browser OCR USD 48,000 and concise contract 30-day answer; actual Finance unpaid/overdue database answer. Every inspected citation resolved to current authorized preview. `render_business_answer` removes contract masthead while preserving canonical excerpt. |
| 2 Combined intent / exact IDs / OCR identity | PASS | `relevant_passage` accepts each explicitly requested fact; `prepare_generation_context` links only visible single-invoice document siblings, marks eligible passages. New invoker SQL restricts explicit invoice queries to authorized matching documents and removes zero-keyword rank bonus. Unknown-ID/HR/foreign-org SQL and ambiguous-document tests pass. |
| 2 System trust / poison / forged and contradictory claims | PASS | Designated `systemInstruction`; deterministic forgery/poison/irrelevance/paid-unpaid tests. Actual 3.8 Flash literal inspection quoted DOC-SEC-001 as untrusted and did not execute it. Bounded example, not an exhaustive attack benchmark. |
| 3 Composer, duplicate lock, Enter/Shift+Enter, SSE and retry | PASS | Actual browser clear/retained question, real sequential status, failure source links, successful inline citation; Enter submits and Shift+Enter newline. No answer timing displayed below the response. |
| 3 Persistent threads, ownership, restart and replay | PASS | Real generated OCR/contract thread reloaded and reopened after actual API restart. Continued existing thread. Guessed foreign-user ID404. Replay rebuilds from current RLS chunks/siblings; saved text/trace never trusted. |
| 3 Exact evidence modal and focus/keyboard | PASS | Actual generated OCR region/original, contract PDF page 1 and typed invoice row. Visible close, Escape/outside/interior/focus checked; mobile/short-height scrolling. |
| 4 Fresh browser PDF pipeline | PASS | Fresh browser extraction/vectors/RPC/page preview in original 29 checks. Additional fresh API upload produced real 3.7 fallback PDF claims with exact previews; no seed-only substitute. |
| 4 Fresh browser image/OCR pipeline | PASS | Real PNG chooser/decode/OCR 3 regions/vectors/RPC/original/coordinates verified. Additional fresh upload indexed3 regions. Fresh OCR-specific generated claim remains BLOCKED by intermittent provider failures/partial selection; no success claimed. |
| 4 Fresh typed database pipeline | PASS | Browser CF-INV-1009 persisted exact 123400 minor units and searchable row. Additional disposable row produced real 3.7 fallback invoice answer and exact table/row preview. |
| 4 Named delete/cancel/transaction/audit/cleanup/replay | PASS | Original 22 post-browser-delete checks; resume 30 actual checks include generated-history invalidation, cleanup, durable source_delete events, typed row removal and empty exact-ID retrieval. Deleted only disposable sources. Original19/45/7 retained. |
| 5 Six routes / both themes / four sizes | PASS | Original48 real route/theme/viewport combinations at 1440×900,1024×768,390×844,1280×500; successful generated Ask additionally checked in8 combinations, no overflow. |
| 5 Sidebar, mobile nav, dropdowns, dialogs, controls | PASS | Anchored profile/scrollable short rail; mobile left nav close/Escape/focus; source dialog behavior and mobile delete. Keyboard/focus/contrast visually reviewed; no automated accessibility certification claimed. |
| 5 Dashboard, Sources, Ingest, Security | PASS | Actual counts/history/index activity/status/events; real source controls and private previews; accurate ingestion causes/retry, no artificial progress. Durable metadata survives restart; delete event is transactional. |
| 5 Evaluation and measured labels | PASS | Actual post-repair v2 run completed09:28:28.553982Z:6 queries plus directHR check; hit@12=1.0, MRR 0.80,0 forbidden,59/59 locations,655.2 ms mean; all-three-source retrieval and structured-finance PASS. Artifact timestamp reflects CLI output completion. |
| 6 Email login / closed signup / assigned role only | PASS | Real CEO/Finance and five-role Auth suite; unassigned roles denied. Global signup closed, email provider enabled; no automatic privileges/public credentials. |
| 6 Google initiation/config detection/PKCE code | PASS | Implemented supported flow/redirect allowlist/tests. Actual settings google=false; UI explicitly unavailable. |
| 6 Real Google provider completion | BLOCKED | Operator-owned client/provider credentials and redirects are absent. Exact private setup in SECURITY_ARCHITECTURE.md; no secrets requested. |
| 6 Recovery request/email/callback/form/failure | PASS | Actual request→Mailpit email→same-browser PKCE exchange→usable form; invalid/missing session and external redirect rejected. |
| 6 Actual password update / timed recovery expiry | NOT RUN | Credential change requires user handoff under browser policy. No password changed. Existing form/session verification does not prove timed link expiry. |
| 7 Measured latency / budgets / cache isolation | PASS | Browser successful primary 6446ms; normal fresh fallback 12580.5ms; real three-modal fallback 10361ms in controlled-primary-failure integration. Unrun ranking-only timing null; one embedding/retrieval per request. No shared answer/evidence cache. |
| 8 Original PS-01 / 12-step comparison | PASS | Explicit matrices below; limits and all unfinished work retained. |
| 9 Backend/SQL/static/frontend/build | PASS |103 pytest,55 pgTAP,5 node; Ruff/format,ESLint,tsc,Next production build and diff checks executed. Frontend unchanged since its verified build. Dependency warnings disclosed. |
| 9 Startup/verifier/artifacts/secrets | PASS | Existing-data startup exercised. Latest full verifier51 PASS / 1 provider BLOCKED, not silently skipped; exact upstream 503 retained. Launcher start→SIGTERM stopped both listeners→restart PASS; Supabase retained. Final secret/diff review and push evidence appended after delivery. |
| 9 Stable source commits | PASS | Retained20b0b36; resume implementation b44ba79 after103 API/55 SQL/18 targeted provider checks, source diff review and secret scan. |
| 9 Existing-origin push | PASS | Authenticated `git push origin main` succeeded:8305326→b44ba79, no force. Final documentation HEAD/status reported after its push. |

## PS-01 comparison

| # | Requirement | Status | Verification / limit |
|---|---|---|---|
| 1 | PDF ingestion | PASS | Fresh browser and actual vector/index/page checks. |
| 2 | Real image/OCR | PASS | Fresh real OCR 3 regions with coordinates/vector/original. |
| 3 | PostgreSQL typed records | PASS | Seven actual tables; fresh invoice persisted and cited. |
| 4 | Unified vector/metadata | PASS |1536 pgvector, invoker hybrid RPC, exact provenance. |
| 5 | Three modalities in one query | PASS | Actual v2 retrieval plus real 3.7 generated three-modal API integration. Primary deadline deliberately 1ms in that integration; fallback response/Auth/RLS/embedding/history/previews were real. |
| 6 | Retrieval-time authorization | PASS |55 local SQL and 51 live checks, exact-ID RLS and cross-org denial. |
| 7 | No unauthorized model context | PASS | HR identical question:0 context/no model. Finance outbound capture independently compared all IDs with real Finance RLS visibility on both attempts; all matched. Scoped example, not global leak certification. |
| 8 | Exact generated canonical citations | PASS | Actual OCR/PDF/typed and cross-modal source previews; server resolves facts/locations. |
| 9 | Forged quotes/citations/conflicts | PASS | Deterministic adversarial regressions; exact-ID and ambiguous-document safeguards. |
| 10 | Prompt-injection safeguards | PASS | System trust field, bounded guards and actual untrusted literal quote case; not exhaustive resistance. |
| 11 | Five roles / cross-organization | PASS | Live five-role suite plus SQL foreign-tenant and actor-bound broker tests. |
| 12 | Persistent/re-authorized history | PASS | Actual generated reload/API restart; current sibling reads and real deleted-generated replay invalidation. |
| 13 | Protected previews | PASS | Actual page/region/table; forbidden citation/document/original/page404. |
| 14 | Accurate Security/Evaluation | PASS | Durable events, post-repair real v2 metrics, explicit measured/recorded/unmeasured labels. |
| 15 | Real Ask business answer | PASS | Real browser 3.8 OCR/contract; normal API 3.8 Finance and3.7 fresh fallback. Intermittent503/timeouts remain a reliability blocker. |
| 16 | Reproducible startup/demo | PASS | Existing local launcher/verifier/runbook; provider-dependent latest verifier still BLOCKED honestly. |

## Required demo sequence

| Step | Status | Exact executed scope |
|---|---|---|
| 1 CEO scanned amount | PASS | Real browser 3.8 Flash:USD 48,000.00; exact OCR region/original. |
| 2 Contract/PDF page | PASS | Real browser generated30-day terms and page 1; canonical concise reconstruction after restart. |
| 3 Finance invoice/payment row | PASS | Real Finance-context 3.8 answer:unpaid/overdue; invoices/ACM-INV-2048 canonical preview. |
| 4 Cross-modal answer | PASS | Real API integration3.7:OCR total + PDF terms + typed status,3 previews. Controlled primary transport timeout explicitly recorded; normal daemon cross-modal attempts also recorded503/timeout. |
| 5 HR identical question | PASS | Actual INSUFFICIENT_EVIDENCE,0 model-context evidence/no model. |
| 6 Forbidden source/preview | PASS | Citation/document/original/page404 without metadata. |
| 7 Poison/forgery/conflict | PASS | Actual literal poisoned document quoted untrusted; fabricated/contradictory regressions. No exhaustive benchmark claimed. |
| 8 Context switch/actor | PASS | BrowserCEO identity retained; server forged/foreign contexts denied before retrieval. |
| 9 Refresh/restart/reopen | PASS | Actual generated OCR/contract thread and helper threads; ownership/reconstruction verified. |
| 10 Fresh PDF/image/row and query | PASS | Browser forms+29 live checks; additional real 3.7 fresh PDF/row answer and 30 deletion checks. Fresh OCR retrieval passes; its separate generated answer remains BLOCKED. |
| 11 Delete test source | PASS | Named browser confirmation/cancel; actual generated history invalidated and exact-ID retrieval empty. |
| 12 All pages/themes/sizes | PASS |48 route combinations plus 8 successful-generated Ask combinations. |

## Exact final evidence

- `data/local/generation-acceptance.json`: real normal API successes AND failed attempts, canonical checks and per-model routing. At09:25:47Z normal fresh fallback used3.7; PARTIALLY_CITATION_VALIDATED contains only checked PDF/typed claims; rejected OCR selection not presented as valid.
- `data/local/outbound-live-integration.json`: actual Finance API pipeline with controlled primary 1ms transport deadline; real 3.7 fallback, CITATION_VALIDATED,3 source types/previews, both outbound ID sets RLS-authorized, total10361ms. No mocked external responses.
- `data/local/fresh-generated-lifecycle.json`:30/30 post-delete/replay/cleanup/audit/typed/RPC/count checks;19 documents/45 chunks/7 typed rows retained.
- Original `data/local/product-verification.json`:29 ingestion and22 deletion checks, actual browser forms. `data/local/ui-verification/coverage.json`:48 states; `generated-coverage.json`:8 successful generated states; trace text and screenshots retained locally.
- Updated `data/local/evaluation.json`:v2 actual MRR 0.80, hit1.0,59/59 locations,655.2 ms; previous recorded result archived locally.
- Latest full `./scripts/verify_demo`:51 independent checks PASS,1 real generation BLOCKED by provider_unavailable503; SQL55 PASS. This does not erase the separate genuine model successes.
- `.venv/bin/pytest apps/api/tests -q`:103 passed;240 dependency/deprecation warnings. Ruff/format PASS. Frontend5 node/lint/types/build PASS on unchanged web implementation.
- Reports under `data/local` and raw `/private/tmp/clearframe-*.log` remain ignored/local. Committed screenshots show both actual success and actual recovery behavior.

## Every unfinished item and recovery

1. **BLOCKED — provider consistency:** configured models intermittently return503/timeouts. Normal cross-modal attempts and latest full verifier failed despite independent real primary/fallback successes. Fresh OCR-specific generation did not reach a fully validated answer. No key/model guessing or billing/provider change was made. Recovery: wait for the existing account/models to be available, run `./scripts/verify_demo` once, then the normal browser cross-modal question. Recreate only disposable assets if repeating the fresh OCR-specific check; no reset. Highest-priority remaining blocker is dependable Gemini availability for the judge recording.
2. **BLOCKED — Google provider completion:** operator must privately configure OAuth client/provider and exact redirects; existing organization/roles must already be assigned. Implemented configuration detection and unavailable UI satisfy the unconfigured-provider fallback requirement; actual Google completion remains unverified.
3. **NOT RUN — password update/success and timed recovery expiry:** actual email/callback/form passes; entering/submitting a new credential requires user handoff. No account password changed. Hosted SMTP/Auth are unverified.
4. **NOT RUN — optional extended checks:** deliberately timed browser expiry, automated contrast/WCAG certification and reduced-motion emulation. Expiry/refresh regressions, actual rejected refresh/logout, keyboard/focus/contrast visual review and CSS reduced-motion behavior were inspected/executed as specified above; no certification claimed.
5. **Disclosed architectural boundaries:** general semantic entailment/exhaustive attack resistance and atomic revocation across an external call are not implemented guarantees. Hosted deployment, production parser/storage isolation and representative-scale vector recall are outside this local pass. Ordinary audit writes are best effort on database failure; source deletion audit is transactional.

## Resume phase updates

- Phases1–2: live model availability resumed; default thinking/deadlines and safe attempt metadata repaired. Multiple-intent eligibility and exact-ID/zero-keyword retrieval defects reproduced and fixed. Same-document identity is derived solely from current visible siblings and only for one explicit invoice; ambiguous documents fail closed.55 SQL/103 API tests pass.
- Phase3: actual generated thread survived reload/API restart; canonical payment sentence is concise; successful generated UI has8 extra coverage states.
- Phase4: additional disposable uploads produced a real normal fallback answer;30 actual deletion/history/audit/cleanup checks pass, seed corpus retained.
- Phases5–7: current v2 evaluation improved MRR from0.54 to0.80; no forbidden hits in these cases. Actual three-modal fallback and independent outbound-ID capture pass in the explicitly controlled-primary-timeout integration.
- Phases8–9: original requirements reconciled above; remaining external/handoff checks explicitly retained. Final startup/delivery evidence follows after execution.

## Phase execution log (intermediate snapshots)


## Phase 0/1 execution evidence

- Phase 0 PASS: local CEO password Auth 200, workspace 200 (19 documents / 45 chunks), conversations 200 (empty); official Gemini catalogue and account list 200 confirm `gemini-3.8-flash`, `gemini-3.7-flash` support generateContent and `gemini-embedding-2` supports embedContent. Sandbox CLI needed local socket escalation; no hosted request.
- Phase 1 deterministic PASS: `pytest ...test_context_boundaries.py ...test_api_security.py ...test_evidence_workflows.py -q` → 36 passed. Cache uses actor/org/role tuple, verifies seeded actor email and target current organization/role/email on reuse. Foreign cached org and foreign actor reject before retrieval. New narrow RLS reread discards changed/deleted/revoked rows before generation.
- Phase 1 session regression PASS: `node --experimental-strip-types --test apps/web/tests/session.test.mjs` → 4 passed: refresh/recovery, failed refresh/missing session, outage, forced 401 recovery. Actual browser expiry/logout remains NOT RUN until the browser round. History now preserves actual error category instead of asserting every failure needs migration.
- Revalidation limitation: no atomic guarantee spans the final database check and external generation; concurrent revocation after submission cannot retract provider context or browser bytes.

## Phase 2 execution evidence

- Catalogue/account inventory PASS: local redacted probe returned models list 200 and both configured generateContent IDs; embedding preserved at 1536 dimensions.
- Provider regressions PASS: 46 targeted tests passed (`test_integrations.py`, `test_rag.py`, `test_api_security.py`). Primary/fallback success, transient 503/timeouts, model-specific vs unknown/global quotas, all eligible quotas exhausted, invalid key/request/model inventory, malformed output, bounded attempts and system field checked. Mock success is only adapter verification.
- Live Gemini BLOCKED: one real CEO OCR request against updated API returned HTTP 503 / `provider_unavailable`, upstream status 503, after bounded configured routing. Actual timings: Auth 52.5 ms, embedding 1038.6 ms, retrieval 51.4 ms, revalidation 28.2 ms, generation attempts 9406.2 ms, total 10577.3 ms; validation NOT RUN/null. No fake answer. Real successful answer and live model injection resistance remain blocked.
- Grounding safeguards PASS in deterministic tests: genuine irrelevant citation rejected, poisoned genuine citation rejected, literal suspicious-text inspection explicitly quoted as untrusted, unknown IDs/model text/excerpts rejected, same-invoice paid/unpaid conflicts rejected, relevant multiple sources accepted. Natural text uses backend-owned passages or bounded business templates; general semantic entailment remains unimplemented and disclosed.

## Phase 3 implementation evidence (runtime pending)

Ask now clears the composer at submission, uses an immediate in-flight lock, retains the question for retry and displays one actual SSE stage. Failure includes the real cause/retry guidance and authorized found-source links. Existing history is reused; loading and actual error states added. Existing native evidence dialog retains close/Escape/outside-click/focus behavior. `tsc --noEmit` PASS. Browser persistence and populated states remain NOT RUN until the integration round.

## Phase 3 runtime evidence / transition to phase 4

Real local CEO browser login PASS. Ask `hello` rendered the deterministic conversation helper (explicitly no company-data lookup) and cleared the composer. PostgreSQL history save succeeded. Browser reload performed; reopening after API restart is next. This exercises real persistence without pretending a greeting is a generated business answer. Provider-dependent populated answers remain BLOCKED by upstream 503. Phase 4 local lifecycle migration applied successfully with `supabase migration up --local`; no reset/hosted changes.

Phase 3 persistence PASS (bounded to real helper messages): created `hello` via browser Enter, reloaded the browser, restarted the actual API PID 17822 using `run_local_api.py`, opened History and reopened `hello`; the same saved message/helper returned. Continued that conversation with `thanks`. This is real PostgreSQL persistence/replay, explicitly not proof of a Gemini-generated evidence answer surviving restart. Generated replay remains BLOCKED.

## Phase 4 browser/runtime evidence

Browser file chooser + Upload and index PASS for fresh synthetic `fresh-acceptance.pdf` (1 chunk) and `fresh-acceptance.png` (real OCR, 3 regions). Typed `CF-INV-1009` inserted through the structured browser form, indexed 1 chunk. All three appear in Sources (22 total / 50 chunks / 8 typed rows at this point). Browser opened the fresh PDF excerpt and actual page image. This revealed a provenance-title defect: extraction used private UUID filenames for chunk titles. `_store_ingested` now assigns the submitted source name to chunks. Deletion/browser cancellation and post-delete checks continue below.

Local pgTAP PASS: 51 assertions including server-only audit writes, anon audit denial, server-only deletion RPC/cleanup paths, transactional chunk removal and cross-tenant audit isolation. `test_context_boundaries.py` PASS: 5 checks including unauthorized deletion before source lookup and bounded private-file cleanup.

Phase 4 live independent integration PASS: `verify_product.py` recorded 29/29 checks in `data/local/product-verification.json`: all fresh vectors persisted, all three types retrievable through actual invoker RPC, canonical previews, OCR coordinates, PDF page rendering, exact invoice minor-unit value, HR metadata/original denials and deletion rejection, HR same finance question safely refused with zero evidence supplied to generation, guessed conversation denied, durable events present. Browser confirmed exact table/row and OCR highlight.

Deletion browser PASS: named confirmation, Cancel, re-open, delete and successful removal for only the three disposable uploads. Seed corpus retained. Source page empties its matching filter immediately. Generated-citation replay against deleted uploads remains BLOCKED because no real generated answer succeeded; deterministic current-source replay tests cover the fail-closed path.

## Phase 5 implementation / verification transition

Dashboard now reads actual recent PostgreSQL history and indexed-source activity. Security uses durable, actor/org/context-scoped metadata-only events; clients cannot forge them. Short-height navigation scrolls independently with profile anchored; redundant Protected knowledge topbar label removed. Source search/filter/sort and native dialogs are operational in current browser. Comprehensive route/theme/viewport round follows phase 6 code paths so final rendered coverage includes all changes.

## Phase 6 implementation evidence

Implemented Google OAuth initiation with live configuration detection (`/auth/settings`), same-origin allowlisted PKCE callback/session exchange, reset-email request, validated recovery-session form, mismatched-password/expired-link/unavailable/success states, and no client signup or role provisioning. `tsc --noEmit` and 5 session/redirect tests PASS. Local config now disables signup and allows exact localhost/127.0.0.1 callback URLs. Google provider is not configured (live verification pending after local restart), so external Google sign-in remains BLOCKED by absent provider credentials/configuration. No credential values requested or changed. Password update will not be executed against an existing account as part of this pass; form path and local email delivery will be verified without altering credentials.

## Phase 7 performance and fallback evidence

PASS: full backend suite 96 tests, including 1-second total-budget cancellation, reauthorization before fallback preventing a second provider submission after revocation, terminal safety blocks and bounded model/quota attempts. Every provider attempt now rechecks the actor, organization/role context and current RLS-visible evidence. Evidence is embedded/retrieved once; model fallback does not repeat those calls. Context remains capped at 16,000 characters; generation at 1024 output tokens, 12 seconds per attempt and 32 seconds total by default. Unexecuted stage durations are null. Provider availability label derives only from an actual attempt; otherwise explicitly unchecked. There is no shared answer/evidence cache; model inventory caches only capabilities and is credential-scoped for 5 minutes. Browser/API performance of successful generation remains BLOCKED; the measured failed request is recorded in Phase 2.

Phase 6 local configuration restart in progress: `supabase stop` confirmed backup=true; `supabase start` restores existing volumes. Hosted Supabase untouched. No password was changed.

Phase 6 local configuration PASS: local stack stopped with backup=true and restored from backup without reset; exact callback URLs and disabled signup are now configured. Original corpus and conversations retained. Google completion remains BLOCKED by provider configuration. Five session/redirect tests and frontend lint now PASS after fixing the login query-parameter lifecycle using Suspense/useSearchParams.

Final browser addendum: actual Finance-owned three-modal generated thread reopened after the final API restart; invoice citation opened exact persisted fields. Screenshot `docs/design/current-cross-modal-history.png`. Launcher lifecycle report confirms actual API/web startup and both listeners stopped on SIGTERM; normal launcher restarted for delivery.

Final hygiene: runtime-secret scan across51 changed deliverable paths PASS (0 matches); no credential/env/private data paths in delivery. Source milestone `b44ba79` committed. Final Ruff/format/diff/shell syntax PASS.

Source delivery PASS: `git push origin main` advanced existing remote from8305326 to b44ba79. Final documentation is committed/pushed next; final response records its exact HEAD and clean synchronization.
