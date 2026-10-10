# Final Ask experience and guarded document composition

Completed 10 October 2026, starting from clean `main` at `69d3fe023a10b646355465d5ff517fc420042f28`. The existing Phase B report and prior invoice-generation evidence were inspected and preserved. No unrelated work was present at the start.

## Implemented behavior

- Exact invoice IDs, amounts, dates, payment status and structured facts retain the evidence-selection/server-rendering path. A successful selector call alone is now classified as `source_answer`, rather than model-written prose.
- The existing structured Gemini response permits optional claim `text` for PDF/OCR explanations. The release guard accepts only complete canonical source sentences, in a model-chosen reading order, with a small set of neutral transitions. It checks the entire proposition rather than accepting matching numbers or shared vocabulary. Every reference must resolve to authorized current evidence and contribute to the released text. Altered numbers, dates, identifiers, negation, qualifiers, invented references and unsupported paraphrases are rejected. Text is limited to 1,200 characters and six sentences per claim; existing claim/context/provider bounds remain unchanged.
- All displayed titles, excerpts, source locations and quotations still originate from the server's canonical passages. The existing actor/organization/role checks and current-RLS rereads remain in place before provider attempts and final release. No additional validation-provider calls were introduced.
- Saved model compositions are checked again against current authorized passages. Changed or revoked sources cannot preserve unchecked saved wording. An originally partial explanation keeps its partial warning on replay; surviving valid claims do not establish completeness of the original response.
- Deterministic small talk remains efficient, with its visible implementation label removed. Verified fallback is labeled **Verified source answer** and explicitly says that no AI wording was used. **AI-generated explanation** appears only when actual model composition, complete citation validation, model identity and per-claim composition markers all agree. Legacy selector responses and partial/history responses do not get that label.
- Successful answers and provider-failure states use the same optional **Source details** control, collapsed by default. It groups PDF/OCR passages by canonical document and structured evidence by canonical record. Three distinct sources are shown initially after expansion; additional sources and passages require their own disclosure. Distinct sources with identical titles are not merged.
- Provider timeout copy preserves the question and the existing retry action. If evidence disappears or becomes irrelevant during final revalidation, the response instead abstains with insufficient information and no stale citations. A provider timeout with relevant sources and no safe invoice fallback remains a friendly retry failure.
- Added finite spelling repairs for ordinary policy/explanation wording. Document follow-ups such as “Explain that policy” use a freshly authorized source identity, enforce that source focus, then run normal fresh retrieval. Ambiguous or revoked referents ask for clarification. Exact business identifiers remain unchanged.

These are focused Ask/RAG changes. No agent framework, provider, dependency, environment value, seed data, migration, hosted Supabase configuration, or six-route design system was changed.

## Focused checks

- **28 distinct backend cases passed**: the new composition/pipeline/history cases plus four existing regressions for structured-fact protection, canonical contract text, revoked history and trusted provider/schema fallback. Initial pass: 27 cases; changed follow-up logic and the four final replay cases were checked afterward. Provider and identity results in these tests are mocked; they are not live integration proof.
- **8 frontend state cases passed**, including truthful generation labels, legacy/partial/fallback states, canonical source grouping, distinct records and duplicate SSE protection.
- **TypeScript and scoped ESLint passed** for the affected frontend; scoped Ruff and `git diff --check` passed. Existing Python asyncio deprecation and Node module-type warnings remain outside this change.
- **One focused desktop browser session** verified the real deterministic greeting, default-collapsed source details, one canonical contract source entry, exact passage inspection, Escape/focus return, and saved partial-answer replay under current access. No browser matrix, production build or full suite was run. Timeout, changed-source, ambiguity and rejection cases were checked through targeted tests, rather than additional live generation failures.
- Private local artifacts: `data/local/final-ask-natural-result.json` and `data/local/final-ask.png`. They are ignored and contain no credentials. No source deletion, reseeding or migration was performed.

## Actual live generation outcome

After read-only provenance checks confirmed the local documents matched fictional fixture hashes, one new authenticated browser question was submitted through the running app's normal streaming Ask endpoint:

> Explain the payment obligations in Acme's contract.

The earlier live invoice test was not repeated. No provider interception or mocked success was used for this question.

- Request: `8ee676e6-ec0a-4134-83e6-6bdf4369ac63`.
- Conversation: `66d715ae-2c4e-4e42-be70-c897fb78b743`.
- Recorded at: `2026-10-10T07:03:32.167498+00:00`.
- Genuine provider: **`gemini-3.8-flash`, primary project, HTTP 200, one attempt, 4,642.9 ms**.
- Total application time: 5,984.2 ms. No provider fallback or provider failure occurred.
- Released state: **`PARTIALLY_CITATION_VALIDATED`**. The model supplied the accepted text, but other proposed claims failed the release guard.
- Released sentence: **Payments must reference the invoice identifier shown on the invoice.**
- Citation: `acme-contract-ACM-MSA-2026-07.pdf`, page 1; evidence ID `6900ae9e-1411-4ac7-9c62-0f2eeaa338f3:2`.
- The authenticated source endpoint returned the exact same canonical excerpt. The UI displayed **Source-backed answer** and the partial-answer warning, rather than claiming a fully validated AI explanation.

No further model request was made. A genuine provider response and one released source-faithful sentence were obtained; a fully validated natural paragraph was **not** demonstrated. Rejected prose is not retained in history, and its exact contents were not inspected. This report does not infer why each rejected claim failed.

## Limitations and delivery

There was no external provider-availability blocker in this single live request. General paraphrasing, causal inference, recommendations and broad semantic entailment remain outside the guarded composition contract. This restriction is deliberate: canonical citation existence alone cannot establish support for arbitrary generated prose. The live partial outcome is a real quality limitation, not complete natural-generation acceptance.

The UI wording and source grouping preserve existing tokens and layout. Hosted behavior, all-role exhaustive verification, full accessibility certification and submission readiness are not claimed. No `CODEX_STATE.md` exists in this checkout; none was created. The Impeccable context launcher was unavailable because its engine was not installed; existing project guidance was used without installing tools.

Intentional changed files: `apps/api/src/ps01_api/integrations.py`, `apps/api/src/ps01_api/main.py`, `apps/api/src/ps01_api/rag.py`, `apps/api/tests/test_natural_generation.py`, `apps/web/src/components/workspace.tsx`, `apps/web/src/lib/chat-state.ts`, `apps/web/tests/chat-state.test.mjs`, and this report. Commit and GitHub delivery are reported after execution. Provider request fields were checked against [Google's generateContent API reference](https://ai.google.dev/api/generate-content#v1beta.GenerationConfig); its existing schema field remains supported but deprecated, and no unrelated API migration was made.
