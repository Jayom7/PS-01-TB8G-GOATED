# Final Build Report — 2026-10-09

Code snapshot: `71100fa` (following backend `167ce78`, frontend `67508ba`, and verification `f55338c`). The final documentation commit follows this snapshot; use `git rev-parse HEAD` for the submission HEAD. All four code commits were pushed to the existing repository. This report describes local implementation, not a completed live demo or hosted deployment.

| # | Requested item | Result |
|---|---|---|
| 1 | CURRENT COMMIT | Code snapshot `71100fa`; final submission HEAD is recorded in the final handoff |
| 2 | GITHUB REMOTE | `git@github.com:Jayom7/PS-01-TB8G-GOATED.git`; retained, no force push |
| 3 | FILES CHANGED | API main/RAG/provider/config/ingestion/records; seed/corpus/verification scripts; API tests; additive SQL/pgTAP; workspace/drawer/CSS/public-login proxy; dev/verify launchers; documentation and labeled screenshots |
| 4 | DATABASE CHANGES | Seven typed business tables, invoker origin view, stale-row deny policy, composite source/org FKs, owner-scoped history; additive migration is BLOCKED/unapplied here |
| 5 | SECURITY CHANGES | Authenticate uploads before bytes; preserve user-session retrieval; reject forged context; protected originals; history ownership/context/current-citation rebuilding; no false security counters |
| 6 | RAG CHANGES | Backend canonical passage IDs and excerpts; no model-authored quotes/text; 16k content budget; bounded cross-modal invoice conflict rejection; one retrieval/embedding and one retryable fallback |
| 7 | INGESTION CHANGES | Actual typed-row write/readback before indexing; 19-source seed; decoded-image validation; bounded embedding concurrency; private originals and compensating source cleanup |
| 8 | FRONTEND/DESIGN CHANGES | Coherent grouped six-route shell, Overview label, shared light/dark tokens, responsive source actions, sortable/filterable rows, accessible overlays/navigation, visible failure states |
| 9 | CHAT/CONVERSATION CHANGES | Real operational SSE, validated final text only; new/recent/reopen/soft-hide conversations; actor/org/context persistence; no implicit conversational-memory prompt |
| 10 | SOURCE INSPECTOR CHANGES | Canonical excerpts, current access, record fields/currency, protected PDF page/image original, scaled OCR region, safe preview error, late-request race guard |
| 11 | RETRIEVAL TRACE CHANGES | Question/identity/context/evidence/model/citation stages; actual timings in drawer; replay discards untrusted stored metadata; ranking-only/unmeasured and entailment limitations explicit |
| 12 | TESTS ADDED | Canonical evidence forgery/quote/contradiction/multi-source cases; role/source/stream/history protections; business-key/snapshot/image guards; 43 pgTAP assertions prepared |
| 13 | TESTS PASSED | VERIFIED LOCALLY: 76 backend tests, Ruff check + format, ESLint, TypeScript, production build, launcher shell syntax, real extraction: 45 candidates across 19 sources |
| 14 | TESTS FAILED | None in final runnable checks. Earlier regression/lint failures were diagnosed and repaired; live dependency checks did not pass |
| 15 | TESTS BLOCKED | SQL migration application/pgTAP, current five-role RLS/runtime, real relational/history persistence, full-stack restart, six live acceptance flows |
| 16 | GEMINI MODEL ACTUALLY VERIFIED | Inventory HTTP 200 lists configured 3.8 Flash and 3.7 Flash. Model existence/access to inventory is verified; no generation model is confirmed working in this pass |
| 17 | GEMINI LIVE STATUS | One bounded synthetic request with one configured fallback ended HTTP 503; no fresh successful answer, injection outcome, or latency benchmark |
| 18 | SUPABASE LIVE STATUS | Hosted Supabase UNVERIFIED; no hosted changes performed |
| 19 | LOCAL SUPABASE STATUS | BLOCKED: Docker engine unavailable; API unreachable; 127.0.0.1:54322 connection refused. New migration and pgTAP were not executed |
| 20 | REMAINING RISKS | General entailment/relevance/injection resistance; SQL verification; filtered ANN recall/scale; nontransactional ingestion; typed origin requires document grant; local original storage; 200-turn history bound |
| 21 | EXACT DEMO FLOW | CEO login → OCR invoice amount → inspector → row/PDF overdue/terms → same finance query in HR context → insufficient evidence/forbidden preview → Security → retrieval trace → injection only after successful preflight |
| 22 | EXACT START COMMAND | `./scripts/dev --seed` initially; later `./scripts/dev`. Existing Docker engine and project dependencies required. Verify with `./scripts/verify_demo` |
| 23 | WORKING TREE CLEAN | Final clean-tree and origin synchronization checks are recorded in the final handoff after committing these docs |

## Browser evidence

Actual public login was inspected on the real app and production server. The six protected workspace routes were inspected on a separate explicitly labeled UI fixture server while Supabase was unavailable. Desktop/tablet/mobile, both themes, five role selectors, history replay/new, source filters/sort, PDF/image/record previews, OCR region, retrieval trace, account controls, and overlay close/focus contracts were checked. Recorded Evaluation data stayed labeled recorded and its failure state was tested. No browser fixture result is claimed as live retrieval, Auth, RLS, generation, upload completion, or history persistence.

Fresh screenshots: [desktop Ask fixture](design/final-desktop-ask-fixture.jpg), [mobile evidence fixture](design/final-mobile-evidence-fixture.jpg). Older reports/evaluation numbers are RECORDED BUT NOT FRESH. Current matrix: [SUBMISSION_MATRIX.md](SUBMISSION_MATRIX.md). Exact walkthrough and fallback: [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md).

## Final acceptance boundary

Implementation and bounded local verification are complete. Full live demo acceptance is **BLOCKED**, not passed: no current database or successful Gemini generation is available. Restore those dependencies and execute the runbook before recording a live submission. No optional drill, presentation slides, hosted deployment, or unrelated software/desktop changes were performed.
