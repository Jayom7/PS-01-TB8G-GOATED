# Final Acceptance Report — 2026-10-09

**Live demo acceptance remains BLOCKED by Gemini generation.** Local services, database authorization, source resolution and real UI verification are restored. This supersedes the dependency status in `cd37ea8`; it does not turn historical answers into fresh results.

## Actual repository state

At entry, `git status` was clean; main HEAD was `cd37ea8b566f83450d17946c295c582eee70e9f0`, synchronized with origin. `git show --stat cd37ea8` showed a documentation/report commit, not evidence of a successful live demo. Existing remote: `git@github.com:Jayom7/PS-01-TB8G-GOATED.git`.

Code changes are committed as `f825075637774409f59d58e69e3ca6d1641e50f1` (`fix: restore typed demo evidence and authorized source previews`). The following handoff commit updates these reports and real screenshots; use `git rev-parse HEAD` for the final HEAD.

## Fixes made

- `apps/api/scripts/seed_local_demo.py`: derive row identity from the table's canonical business key, independent of jsonb field order; repair stale tagged synthetic chunks against persisted typed rows. Real seed now contains 19 documents, 45 chunks and 7 rows.
- `apps/api/scripts/run_local_demo.py`: verify forbidden citation/document/original/rendered-page access and exact PDF bytes/location; future successful generated citations must match the authorized canonical chunk. The latter success path could not run while generation was unavailable.
- `apps/api/src/ps01_api/main.py`: authorize before rendering a bounded PDF page as PNG using existing PyMuPDF. Original bytes remain available. This fixes the blank browser PDF preview without weakening RLS.
- `apps/api/tests/test_demo_corpus.py`, `apps/api/tests/test_evidence_workflows.py`: business-key/order and protected two-page rendering/denial regressions.
- `supabase/tests/database/secure_knowledge_rls.test.sql`: give the tenant-FK probe a unique chunk index so the intended constraint is actually tested.
- `apps/web/src/components/workspace.tsx`, `apps/web/src/app/globals.css`: load Sources/Security/Evaluation with current account context; guard late role errors; render real PDF pages; keep tablet source actions visible; improve mobile target/identity layout, initial evaluation loading and invalid JSON copy. All six routes are preserved.

## Executed validation

| Check | Result |
|---|---|
| Backend pytest | 79 passed; 96 dependency/deprecation warnings. |
| Ruff check / format | Passed. |
| ESLint / TypeScript / Next production webpack build | Passed after final code edits. |
| Launcher shell syntax / git diff whitespace | Passed. |
| Local migrations | All three applied, including `20261009000100`; no hosted operation. |
| Local pgTAP | 43/43 passed, including after Docker recovery. |
| Full `./scripts/verify_demo` | Executed; generation reached actual provider 503 after fallback; exit 2. |
| Final `./scripts/verify_demo --skip-generation` | 50 live checks passed, 2 generation checks blocked; exit 2, completed 04:02:54 UTC. |
| Actual browser | Six routes × light/dark × 1440×900, 820×900, 390×844; source/role/profile/navigation/form checks passed within the limits below. |

Earlier seed/verifier failures exposed noncanonical structured IDs and an Engineer lookup failure; repaired by refreshing seven structured chunks from persisted rows. The first SQL run passed 42/43 because a duplicate-index constraint masked the intended tenant-FK probe; the corrected probe passed 43/43. A PDF test initially confused physical page units with rendered pixels; corrected to verify raster dimensions. These repaired failures are not current passing evidence until rerun; the suites above were rerun successfully.

## Services and provider truth

The installed Docker runtime initially lacked its engine socket. Supported `docker desktop start` restored it; `./scripts/dev --seed` started local Supabase, applied migrations, used real PaddleOCR and Gemini embeddings and launched API/web. During final restart Docker's socket disappeared again. The installed runtime was restarted and `./scripts/dev` restored the stack; repeat local readiness, seed counts, 43 SQL and 50 live checks passed. The cause of the daemon shutdown remains unknown. No unrelated app/OS setting or hosted database was changed.

Gemini embeddings worked for seeding and retrieval. Fresh generation is not verified: a full-flow request ended HTTP 503 after the configured primary/fallback. A later bounded raw diagnostic for `gemini-3.8-flash` returned HTTP 429 `RESOURCE_EXHAUSTED`, naming `generativelanguage.googleapis.com/generate_content_free_tier_requests`, limit 20 and retry interval 22h 48m 46.196578934s. That is the observed response, not a guaranteed reset time. No Retry-After header was present. The older 503 body's cause was not retained and is not inferred from the later 429. No further generation loop, billing/credential change or fixture substitution was performed.

## Evidence and visual acceptance

Real local Auth, five-role retrieval, row/document grants, protected source denial and current typed fields work. The explicit overdue/terms query retrieved invoice PDF, structured invoice, scanned invoice and contract PDF among its top four. The fresh five-question synthetic retrieval report measured hit rate@12 1.000, MRR 0.550, checked forbidden hits 0 and location presence 47/47; it does not score generated answers or semantic entailment. Its narrow OCR-query cross-modal flag remains false.

Real source drawers show canonical excerpts, exact PDF page, OCR region/original and structured row fields. X/Escape/backdrop and focus behavior, mobile navigation, account closing/theme/logout, five real role switches, search/type/sort, invalid JSON and empty history/draft reset were inspected. No page-level horizontal overflow was observed at the audited sizes. Evaluation retains an internal horizontal table scroller; Ask retains internal conversation scrolling. Populated answer/history/retrieval-trace states and successful browser upload completion were not exercised in this pass.

Fresh real images: [desktop overview](design/live-desktop-overview-light.png), [protected PDF page](design/live-desktop-pdf-dark.png), [mobile OCR original](design/live-mobile-ocr-dark.png). Earlier fixture images remain explicitly historical. Impeccable manual audit instructions were available, but its context-engine command was unavailable; project context was read directly. Taste was read, with its dense-app scope limitation respected. Awwwards Tipalti **nominee** and Carbon enterprise table guidance were inspected; no winning-site status or copied assets/layouts are claimed. See [visual audit](UI_DESIGN.md).

## Submission gate

No fresh successful CEO invoice/PDF/DB/cross-modal answer, generated HR denial, poisoned-document resistance, answer-citation audit or persisted conversation replay is claimed. Context unit tests and live RLS checks support the boundary; no independent live outbound prompt capture was performed. Hosted correctness, general entailment, selective ANN scale and Docker shutdown cause remain unverified.

After the provider permits generation, run `./scripts/verify_demo` once, then every explicit answer/injection flow in [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md). Open each displayed citation, inspect a real trace and save/reopen a conversation across a launcher restart. All must pass before recording a submission. The verifier alone covers OCR and HR generation, not every manual flow. [SUBMISSION_MATRIX.md](SUBMISSION_MATRIX.md) records each PS-01 requirement.
