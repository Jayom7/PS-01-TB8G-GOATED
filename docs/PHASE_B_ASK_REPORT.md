# Clearframe Phase B — Ask implementation

Completed 10 October 2026. Existing authentication/integration work was preserved. No dependencies, providers, seed records, migrations, commits, or hosted configuration changes were introduced.

## Behavior and checklist

| Item | Existing behavior retained | Missing behavior implemented |
| --- | --- | --- |
| 1. Small talk and mixed intent | Deterministic greetings, thanks, capabilities; no embeddings/generation for exact helper inputs | Shorter helper replies, additional ordinary small talk, and social-preface removal only before a clear business request. Mixed questions still retrieve company evidence. |
| 2. Concise substantive answers | Evidence-ID-only model schema; server-owned content and citations | Prompt selects direct facts first. Invoice totals identify the invoice; due/invoice dates and status use actual canonical fields. Status includes its recorded date. Project status and opportunity stage have bounded field-based sentences. Individual passages produce separately cited claims; the UI reads them as a compact paragraph. |
| 3. Contextual follow-ups | Prior citations are reread under current RLS; previous prose never supplies facts; retrieval runs again | “What about the due date?”, “When is it due?”, short amount/status/terms follow-ups. Ambiguous invoice/typed-record requests clarify safely. Malformed invoice identifiers remain unchanged and request correction. |
| 4. Citation/source inspection | Current-session source reads, PDF-page preview, OCR overlay and typed fields | Inspector requests the canonical evidence ID and resolves the exact passage after RLS. Passage references in the same PDF chunk remain distinct. Loading inspection does not display an old source title/location before authorization. Supporting source lists are collapsed by default. |
| 5. Insufficient evidence and safe refusal | Permission-safe 403/404 messages; no unauthorized source material | Failed citations and bounded invoice contradictions have distinct states instead of being labelled insufficient evidence. Contradictions stop before generation. History removes unavailable sources and labels recorded failures without claiming current conflict facts. |
| 6. Timeout and verified fallback | Bounded models/projects, cooldowns, final access checks, conservative extraction | Due/invoice-date extraction, concise dated answers, explicit “Composed without a language model” label and friendly outage explanation. No provider configuration defect was established; provider retry logic was retained. |
| 7. Composer, history, retry, duplicates | Right-aligned questions/left-aligned responses, Enter/Shift+Enter/IME handling, in-flight submission guard, duplicate-result guard, retained failed question and retry, new-thread reset | History opening shares the in-flight guard; stale error/retry context clears when switching/new conversation. History has a reload action. Validation failure retains the question and offers retry. Composer focus returns after completion. |
| 8. Keyboard, focus, responsive dialogs | Existing tokens/themes, responsive composer, native trace dialog, evidence close/Escape/focus restoration | Outside-click dismissal for the temporary evidence panel; accessible citation names include source/location. Compact empty-state copy and answer measure/spacing. No permanent source sidebar or route redesign. |

The finite wording repairs remain conservative rather than general fuzzy entity matching. Unrecognized or unsupported business facts still abstain; deterministic fallback remains a bounded invoice extractor. The model can select evidence, but cannot supply unchecked factual prose, source titles, locations, quotes, or arbitrary identifiers.

The supplied references informed permission-bound company knowledge and citation inspection ([Glean information access](https://docs.glean.com/user-guide/assistant/how-glean-accesses-info), [Glean Chat](https://docs.glean.com/user-guide/assistant/glean-chat)), starter prompts and source/history interactions ([Amazon Q features](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/features.html), [Amazon Q workflow](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/how-it-works.html)), and grounding context ([Copilot grounding](https://support.microsoft.com/en-us/microsoft-365-copilot/what-information-does-copilot-use-to-answer-my-prompt)). No competitor connectors or additional agent layers were added.

## Verification actually performed

- **129 targeted backend tests passed**: `test_rag.py`, `test_verified_evidence.py`, `test_evidence_workflows.py`. These include mocked provider/identity cases and distinguish them from live integration. New cases cover mixed intent, dated fallback, fresh follow-up retrieval, exact inspector passages, forged references, safe denials, ordinary small talk, and contradiction-before-generation.
- **6 frontend state tests passed**: `node --experimental-strip-types --test tests/chat-state.test.mjs`. This covers safe failure text/titles, duplicate SSE results, and distinct passage references.
- **TypeScript, scoped ESLint, scoped Ruff and `git diff --check` passed.** Dependency deprecation/module-type warnings remain; no production build or broad SQL/backend suite was run.
- **9 local integration checks passed** using real local Auth, RLS, Gemini embeddings, database retrieval, source reads and history persistence. Generation requests were intercepted locally and returned HTTP 503; no successful model response was fabricated and no live chat-generation request was transmitted. The two substantive questions were the mixed Acme invoice amount request and its due-date follow-up. HR received a plain 404 for the Finance citation. The authorized source listing was unchanged before/after. Only ordinary chat history/audit events were written. Machine-readable evidence: `data/local/phase-b-checks.json` (ignored local artifact).
- **Bounded real-browser check**: live helper response, current-access history reopening, invoice total and due-date replay, exact OCR excerpt/region and typed record inspector, Escape/focus return and outside-click/composer focus. Desktop 1280×720 dark and mobile 390×844 dark/light layouts had no page overflow and a visible composer. Original theme and viewport were restored. Saved view: `docs/design/phase-b-ask.png`.

Provider-error/retry and duplicate submission regressions were covered by scoped tests and retained implementation inspection; this pass did not induce a browser-side live provider failure. Source deletion was not performed. Hosted authorization, complete accessibility certification and general semantic entailment were not evaluated.

## Generation and remaining limitations

**No genuine LLM answer was obtained or attempted through the live provider in this phase.** New substantive integration responses used `VERIFIED_EVIDENCE` under a deliberately intercepted outage. The browser then rebuilt those saved answers from currently authorized evidence. Genuine generation availability and live model selection/answer quality remain unverified; the previously reported provider outage was not re-probed. Citation existence and deterministic field checks do not establish general semantic entailment.

## Exact files changed by this phase

Application code:

- `apps/api/src/ps01_api/rag.py`
- `apps/api/src/ps01_api/main.py` — only Ask, passage inspection and history hunks; prior embedding-authorization edits retained.
- `apps/api/src/ps01_api/records.py`
- `apps/web/src/components/workspace.tsx` — Ask/history/source inspection portions of the existing shared component.
- `apps/web/src/components/drawer.tsx` — evidence-panel outside dismissal only.
- `apps/web/src/lib/chat-state.ts`
- `apps/web/src/app/globals.css` — Ask answer/source-detail styles only.

Focused tests and handoff artifacts:

- `apps/api/tests/test_rag.py`
- `apps/api/tests/test_verified_evidence.py`
- `apps/api/tests/test_evidence_workflows.py`
- `apps/web/tests/chat-state.test.mjs`
- `docs/PHASE_B_ASK_REPORT.md`
- `docs/design/phase-b-ask.png`
- `data/local/phase-b-checks.json` — ignored local integration result.

No `CODEX_STATE.md` exists in this checkout; none was created. Existing unrelated dirty files remain untouched.
