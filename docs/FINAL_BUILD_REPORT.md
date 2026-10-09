# Clearframe final implementation and acceptance report — 2026-10-09

This is the earlier end-to-end report. The [latest Final Engineering Phase 1 section](MASTER_ACCEPTANCE_CHECKLIST.md) supersedes its test/count/runtime claims: 138 API tests and 24 controlled-outage integration checks; current preserved corpus 18/44/6 with the purchase-order seed absent. It records the actual starting/source-ending Git HEAD, exact provider 429→configured fallback 200 observation and remaining work.

Real Gemini primary and configured fallback answers now work. The browser produced the correct scanned USD 48,000 amount and contract terms with `gemini-3.8-flash`; the normal API produced fresh PDF/database answers with `gemini-3.7-flash`. A real API integration produced all three modalities through the fallback, verified exact previews and independently captured outbound evidence IDs against Finance RLS. Its primary transport deadline was deliberately interrupted; external dependencies and the fallback response were real.

All independently achievable implementation and verification is finished. Submission reliability still depends on intermittent Gemini availability. Some normal cross-modal requests and the latest full verifier returned 503/timeouts. Fresh OCR-specific generation, real Google completion, password update and timed expiry checks remain explicitly unfinished below.

## Repository and delivery

Original entry: clean `main` at `8305326`; preserved origin `git@github.com:Jayom7/PS-01-TB8G-GOATED.git`. Implementation milestone `20b0b36` was retained; resume implementation is committed as `b44ba79`. No reset, force push, hosted Supabase operation, credential/billing change or extra provider. The final response gives the exact final HEAD and synchronized Git state after push. Delivery evidence is appended after execution.

## Exact implementation changes

| Files / functions | Result |
|---|---|
| `apps/api/src/ps01_api/main.py`: `_identity`, `_context_token`, `revalidate_evidence`, `_run_query` | Assigned roles required; actor/org/role-bound local context cache and current target checks; current source reauthorization before every generation attempt; HR refusal without model context. |
| `integrations.py`: `generation_models`, `generate_claims`, `_generate_bounded`, `provider_failure`, `model_scoped_quota`; `config.py` | Verified configured models, credential-scoped inventory, trusted system field, error-aware two-model fallback, supported low thinking, 20s attempt/45s total default, safe per-attempt diagnostics and retry guidance. Embedding-2/1536 unchanged. |
| `rag.py`: `relevant_passage`, `prepare_generation_context`, `render_business_answer`, `validate_generation` | Multiple requested business intents, eligible passage flags, current visible single-invoice sibling identity, ambiguous/foreign sibling rejection, concise contract sentences and canonical-only facts. Poison/forgery/invoice-conflict guards retained. |
| `20261009000300_exact_identifier_retrieval.sql` | Existing SECURITY INVOKER RPC now restricts explicit invoice queries to matching authorized documents; unknown IDs never substitute similar invoices. Zero keyword matches no longer receive arbitrary rank bonuses. |
| `main.py`: `conversation`, `_save_history`, `_history_rows` | Reused PostgreSQL threads with actor/org/context ownership. Replay reauthorizes citation rows and current visible siblings; never trusts stored answer text or trace. Actual generated reload/restart and deleted-source invalidation verified. |
| `main.py`: `delete_source`, `cleanup_source_original`, `drain_cleanup_jobs`, `_store_ingested`; lifecycle migration | Named authorized deletion, transactional chunks/grants/typed-origin/audit/cleanup intent, contained private-file cleanup, safe dependent-record conflict and correct upload title. Embedding failures compensate and retain precise causes. |
| `main.py`: workspace/security/audit functions | Actual counts/history/index activity, measured provider status, durable actor/org/context metadata events; no confidential bodies. |
| `apps/web/src/lib/session.ts`, `workspace.tsx`, Supabase proxy | Bounded refresh/one401 retry, explicit signed-out and outage states, correct profile/history errors. Actual rejected refresh led to public sign-in; logout/login/recovery work. |
| `workspace.tsx`, `globals.css` | Composer clearing/retry/duplicate lock, real SSE stage, inline evidence, source controls/mobile delete, short sidebar, mobile navigation, native accessible modal/focus and restrained themes. |
| Auth pages/callback/settings, redirect helper and local Supabase config | Google initiation/config detection/PKCE, recovery email and usable reset form, safe redirects, closed signup and no automatic privileges. Google remains truthfully unconfigured. |
| `next.config.ts`, `configure_local_web.py` | Opt-in native local same-origin API forwarding with server-side bearer/RLS checks preserved. |
| Evaluation/verifier/product scripts and tests | Explicit three-modality evaluation case, independent HR refusal, fresh synthetic assets and real lifecycle verification; tenant/provider/grounding/session/replay/SQL regressions. |
| `scripts/dev` | Existing-data launcher retained; web process uses exec so launcher termination cleans both API and web. Actual start→SIGTERM→both listeners gone→restart verified. |

## Executed checks and actual evidence

| Check | Result |
|---|---|
| Backend | **103 pytest passed**, 240 dependency/deprecation warnings. |
| Database | **55 pgTAP assertions passed**; five additive local migrations. Exact-ID positive/unknown/HR/foreign-org tests included. |
| Frontend | **5 node tests passed**, ESLint, TypeScript and Next production build passed. Web source unchanged since that successful build. |
| Static/hygiene | Ruff/format, shell syntax and `git diff --check` passed. Secret review and delivery evidence appended below. |
| Full local verifier | **51 independent checks passed / 1 real generation blocked** by upstream 503. Not silently skipped or counted as success. |
| Fresh browser ingestion | PDF 1 chunk, actual image OCR 3 regions, typed invoice 1 chunk; **29 live checks passed**. |
| Source deletion | Original **22 checks passed**; resume **30 checks passed**, including real generated replay invalidation, cleanup/audit, typed row absence and empty exact-ID retrieval. Original **19 sources / 45 chunks / 7 typed rows** retained. |
| Conversation | Generated OCR/contract thread reopened after browser reload and actual API restart. Real Finance-owned cross-modal history reopened under Finance and its exact invoice fields opened. Foreign-user guessed conversation404. |
| UI | **48 route/theme/size combinations**, plus **8 populated Ask combinations**, no page overflow. Desktop 1440×900, tablet 1024×768, mobile 390×844 and short 1280×500. Modal/nav/focus/keyboard and controls verified. |
| Recovery | Real local request→Mailpit email→same-browser PKCE exchange→usable reset form; invalid/missing-session/external redirect states passed. No password changed. |
| Retrieval evaluation | Current `novacore-synthetic-v2`, completed09:28:28.553982Z: six queries plus directHR; **hit@12=1.0, MRR 0.80, 0 forbidden, 59/59 locations, 655.2 ms mean**. Actual all-three-modalities and structured-finance cases pass. Timestamp is CLI output completion. |

Successful browser OCR trace: Auth56ms, embedding640ms, retrieval42ms, generation5662ms, validation1ms, total6446ms. Normal fresh fallback total12580.5ms; only checked PDF/typed claims rendered, with an invalid OCR selection rejected (PARTIALLY_CITATION_VALIDATED). Three-modal real fallback integration: total10361ms, three exact previews, all outgoing IDs matched actual Finance RLS visibility on both attempts. Ranking-only time remains null because it is not independently measured.

Local evidence is ignored under `data/local`: `generation-acceptance.json`, `outbound-live-integration.json`, `fresh-generated-lifecycle.json`, `launcher-verification.json`, `security-verification.json`, `product-verification.json`, `evaluation.json`, and UI coverage/trace artifacts. Raw logs are `/private/tmp/clearframe-*.log`. No mocked provider success is used as live proof.

[Actual successful browser Ask](design/current-ask-success.png), [real generated cross-modal history reopened under Finance](design/current-cross-modal-history.png), [actual provider-failure recovery](design/current-ask-provider-failure.png).

## Every original requirement and unfinished item

The [master acceptance checklist](MASTER_ACCEPTANCE_CHECKLIST.md) maps every phase, all 16 PS-01 requirements and all 12 demo steps. Steps1–3,5–9,11–12 pass in their executed scopes. Step4 passes a real three-modal API integration with the explicitly controlled primary timeout and real fallback; normal daemon combined attempts also failed and are not called successful. Step10 passes browser ingestion/retrieval plus real fresh PDF/typed generation; a fully validated fresh OCR-generated answer remains blocked.

1. **Highest-priority blocker — dependable Gemini availability:** both configured models intermittently return503/timeouts. Latest full verifier and some normal combined requests failed despite genuine primary/normal-fallback successes. Fresh OCR-specific generated selection is incomplete. Recovery: wait for the existing account/models to be available, run `./scripts/verify_demo` once and the normal combined browser question. Recreate only disposable assets if repeating fresh OCR generation. Respect retry guidance; no key/provider/billing change or reset.
2. **Google completion BLOCKED:** operator-owned OAuth client/provider configuration and exact redirects are absent. Code, callback, detection, redirect tests and explicit unavailable state are implemented. Configure privately as documented in [SECURITY_ARCHITECTURE](SECURITY_ARCHITECTURE.md); no secrets in chat, no automatic org/roles.
3. **Password update/success and timed recovery expiry NOT RUN:** actual email/callback/form passed. Browser policy requires the user to enter and submit any new credential. No password changed. Hosted SMTP/Auth unverified.
4. **Optional extended checks NOT RUN:** deliberate wall-clock browser expiry, automated contrast/WCAG certification and reduced-motion emulation. Expiry/refresh regressions, real rejected refresh/logout, focus/keyboard and visual contrast review were executed; no certification claimed.
5. **Explicit boundaries:** general semantic entailment/exhaustive contradiction or injection resistance and atomic revocation spanning an external model call are not implemented guarantees. Hosted deployment, production parser/storage isolation and representative-scale vector recall remain outside this local pass. Ordinary audit writes are best effort on database failure; deletion audit is transactional.

## Reproduce

```sh
./scripts/dev
./scripts/verify_demo
# Independent checks when deliberately omitting generation (incomplete, exit 2):
./scripts/verify_demo --skip-generation
.venv/bin/python apps/api/scripts/verify_product.py --prepare-assets
# Upload/insert only the disposable assets per DEMO_RUNBOOK, then:
.venv/bin/python apps/api/scripts/verify_product.py
# Delete only those disposable sources through Sources, then:
.venv/bin/python apps/api/scripts/verify_product.py --verify-deletion
.venv/bin/pytest apps/api/tests -q
node_modules/.bin/supabase test db
.venv/bin/ruff check apps/api
.venv/bin/ruff format --check apps/api
node --experimental-strip-types --test apps/web/tests/session.test.mjs
(cd apps/web && ./node_modules/.bin/eslint)
apps/web/node_modules/.bin/tsc --noEmit --incremental false -p apps/web/tsconfig.json
(cd apps/web && ./node_modules/.bin/next build --webpack)
git diff --check
```

The final local launcher is left running. Reuse http://localhost:3000; avoid starting a second copy on the same ports. Its shutdown stops API/web and leaves Supabase volumes running.

## Exact changed paths

- `README.md`
- `apps/api/scripts/configure_local_web.py`
- `apps/api/scripts/evaluate_local_retrieval.py`
- `apps/api/scripts/run_local_demo.py`
- `apps/api/scripts/verify_product.py`
- `apps/api/src/ps01_api/config.py`
- `apps/api/src/ps01_api/integrations.py`
- `apps/api/src/ps01_api/main.py`
- `apps/api/src/ps01_api/rag.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_api_security.py`
- `apps/api/tests/test_context_boundaries.py`
- `apps/api/tests/test_evaluation.py`
- `apps/api/tests/test_evidence_workflows.py`
- `apps/api/tests/test_integrations.py`
- `apps/api/tests/test_rag.py`
- `apps/web/.env.local.example`
- `apps/web/next.config.ts`
- `apps/web/src/app/auth/callback/route.ts`
- `apps/web/src/app/auth/settings/route.ts`
- `apps/web/src/app/forgot-password/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/src/app/login/page.tsx`
- `apps/web/src/app/reset-password/page.tsx`
- `apps/web/src/components/workspace.tsx`
- `apps/web/src/lib/auth-redirect.ts`
- `apps/web/src/lib/session.ts`
- `apps/web/src/lib/supabase/proxy.ts`
- `apps/web/tests/session.test.mjs`
- `docs/API_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/DEMO_RUNBOOK.md`
- `docs/FINAL_BUILD_REPORT.md`
- `docs/FINAL_LUNA6_FUNCTIONALITY_REPORT.md`
- `docs/MASTER_ACCEPTANCE_CHECKLIST.md`
- `docs/PHASE1_VERIFICATION.md`
- `docs/RAG_PIPELINE.md`
- `docs/REVIEW_NEEDED.md`
- `docs/SECURITY_ARCHITECTURE.md`
- `docs/SUBMISSION_MATRIX.md`
- `docs/THREAT_MODEL.md`
- `docs/UI_DESIGN.md`
- `docs/design/current-ask-provider-failure.png`
- `docs/design/current-ask-success.png`
- `docs/design/current-cross-modal-history.png`
- `scripts/dev`
- `supabase/config.toml`
- `supabase/migrations/20261009000200_source_lifecycle_security_events.sql`
- `supabase/migrations/20261009000300_exact_identifier_retrieval.sql`
- `supabase/tests/database/secure_knowledge_rls.test.sql`

## Final delivery evidence

- Source milestone: `b44ba79`, following retained `20b0b36`. Runtime-secret comparison across all 51 changed deliverable paths found0 matches; no `.env`, credentials or ignored local/private artifacts in delivery.
- Launcher actual start/SIGTERM cleanup/restart PASS.103 API tests and 55 SQL assertions PASS; last targeted provider suite18 PASS. No frontend code changed after its verified build.
- Authenticated source push PASS: existing origin/main advanced8305326→b44ba79 with no force. Final documentation commit/push synchronization is reported with exact HEAD in the final response.
