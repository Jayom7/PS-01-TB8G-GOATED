# Final product quality pass

Completed 10 October 2026, starting from clean `main` at `0380fd7681fab49ceb3092992aa5e7604f5c74c5`. No pre-existing changes were present, and the earlier Phase B and Ask reports were preserved.

## Already present and preserved

The authenticated SSE endpoint already emitted real authorization, retrieval, evidence-selection and validation milestones. It buffered generation and released only the final checked result. Current-RLS evidence rereads, actor/organization/role boundaries, bounded provider retries/cooldowns, evidence manifests, canonical citations, source deletion and history reauthorization remain in place. Small talk, right-aligned questions, retry, duplicate-result prevention and the existing dismissible evidence inspector were retained. Verified fallback was already honestly labeled; partial and saved responses already avoided the fully validated AI label. No numerical confidence or relevance score was added.

## Implemented

- **Readable records:** question-scoped business sentences replace raw serialization for purchase orders and the other typed-record families. Purchase-order summaries show approval date, formatted total and supplier when present. Exact questions show the requested detail; internal supplier/project IDs appear only when explicitly requested. The approver is not inferred from the supplier. Project names are not invented from project IDs or joined without authorized evidence. Canonical citations still point to the original record and its fields.
- **Money and dates:** familiar business dates and exact decimal formatting use the existing two-decimal rules for USD, INR, EUR and GBP. Unknown currencies, missing currency information, invalid amount types and negative amounts cannot inherit a guessed scale. Invoice rendering also avoids floating-point precision loss. The payments/opportunities schema has no currency field; those records cannot support a formatted amount by themselves. Invoice/order totals are not treated as revenue. Singular ambiguity continues to request clarification, and collection requests retain the existing bounded record-selection behavior.
- **Document composition:** the trusted prompt now supplies the exact complete sentence units the validator will accept and asks for supported substantive coverage. A narrowly defined metadata-only contract masthead can be removed from composed prose; arbitrary narrative prefixes, conditions and qualifiers cannot. Original evidence IDs, canonical excerpts and prior full-source compositions remain valid. Changed/revoked evidence and altered values still fail closed. Contract payment-obligation answers are marked partial if they omit an available timing rule or reference requirement. No second validation-model call was introduced.
- **Truthful streaming:** real backend stages have friendly labels and the existing reduced-motion-aware activity indicator. Unknown delta events never become user-facing content. SSE parsing handles CRLF and split frames; incomplete/malformed streams preserve the question. Stop cancels the request, including a stalled authentication wait, and offers retry with the original question. Duplicate terminal events remain harmless. After server validation, approved claims reveal in a short sequence; history and reduced-motion presentations are immediate. This is approved-claim presentation, not raw model token streaming.
- **Evidence and copy:** citation buttons remain beside their claims and use the existing reauthorizing inspector. Collapsed details distinguish cited sources from retrieved sources supplied with a retry failure. Revenue and invoice insufficient-evidence copy is specific to the question and remains distinct from provider failure, denial and validation failure.
- **Compact Ask/history:** the composer is 84px at its default height, retains multiline/IME behavior and vertical resizing, and omits the redundant keyboard hint. The empty state is smaller and access context remains visible. Overview links to `/history`, which lists only the existing API's current actor/role conversations, with loading/error/empty states. `/ask/[conversationId]` safely reopens and revalidates a saved conversation. Runtime route params are read inside Suspense, as required by the installed Next.js version. No additional backend history architecture was added.

## Focused verification

- **34 distinct backend cases passed:** initial targeted pass of 33 cases, then the existing invoice-snapshot regression after the decimal-formatting adjustment. Changed formatter/precision cases were rechecked after their final edits. Checks covered structured prose and provenance, exact questions, currency/precision limits, masthead cleanup, complete/partial composition, qualifier/value rejection, saved model replay, scoped history, revoked citations, stream release ordering and forged-role denial. These are mock/unit checks, not fresh provider proof.
- **13 frontend state cases passed:** split/CRLF streams, unknown deltas, malformed/incomplete terminal frames, duplicate results, safe states/labels, source grouping, specific insufficient-evidence copy and cancellation during an unfinished auth operation.
- TypeScript, scoped ESLint, scoped Ruff and `git diff --check` passed. Existing Python asyncio deprecation and Node module-type warnings remain outside this change.
- One browser session at the current **319 × 738** viewport verified the Overview history link, loaded dedicated history page, safe reopening, restored purchase-order business wording, question-specific revenue abstention, closed source details, exact canonical purchase-order inspection, Escape/focus restoration and an **84px composer with no horizontal overflow**. The new route's initial Suspense warning was corrected. No broad viewport/browser matrix, production build or full suite ran. Cancellation and stream failures were checked through targeted tests rather than additional live provider requests.

## Live generation boundary

Exactly one new normal browser Ask submission was attempted:

> Explain the payment obligations in Acme's contract.

Before submission, read-only checks confirmed all 19 local sources matched fictional fixture hashes. The interface showed the real preparation state and Stop control. The browser then redirected to `/login?reason=session-expired`; no newly released answer was observed or stored. A read-only authorized check found the latest matching saved result was still the **earlier** `8ee676e6-ec0a-4134-83e6-6bdf4369ac63` partial result from `2026-10-10T07:03:32.167498+00:00`. The running application's `provider_check` was null. The protected manifest table refused direct actor access; its permissions were not bypassed.

Signing in again restored Overview/history/source access. No second Ask or provider-success chase followed. No fresh fully validated natural LLM answer was demonstrated in this pass. The observed blocker was the expired browser session; the available evidence does not establish a provider outage. Historical provider success is not presented as fresh success.

General paraphrase, causal inference and arbitrary semantic entailment remain outside this bounded source-faithful composition contract. The targeted tests demonstrate safely accepted complete compositions, but live natural-answer quality is still unverified. All-role exhaustive testing, hosted behavior and complete submission readiness are not claimed.

## Intentional changed files

1. `apps/api/src/ps01_api/records.py`
2. `apps/api/src/ps01_api/rag.py`
3. `apps/api/tests/test_product_quality.py`
4. `apps/web/src/lib/chat-state.ts`
5. `apps/web/src/components/workspace.tsx`
6. `apps/web/src/components/authenticated-workspace.tsx`
7. `apps/web/src/app/atelier.css`
8. `apps/web/src/app/history/page.tsx`
9. `apps/web/src/app/ask/[conversationId]/page.tsx`
10. `apps/web/tests/chat-state.test.mjs`
11. `docs/FINAL_PRODUCT_QUALITY_REPORT.md`

No dependencies, providers, framework, environment values, seed data, migrations, hosted Supabase configuration or unrelated routes were changed. No `CODEX_STATE.md` exists; none was created. Private local proof artifacts are ignored: `data/local/product-quality-ask.png` and `data/local/product-quality-prior-result.json` (explicitly historical evidence). Commit and remote verification are reported after execution.
