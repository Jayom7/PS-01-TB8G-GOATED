# Workspace reconciliation and genuine generation

Verified on 2026-10-10. This follow-up preserves the completed Phase B implementation and does not repeat its audit or acceptance checks.

## Git reconciliation before this follow-up

Branch: `main`, with upstream `origin/main`. Latest local commit was `05461a7cc3afd78b074f8653ea185c2faf03d6f8` (`refine(web): layer dark surfaces and remove redundant actions and copy`, 2026-10-10 01:01:38 +05:30). Remote: `git@github.com:Jayom7/PS-01-TB8G-GOATED.git`.

`git status --short` listed 17 modified tracked files and four untracked files. Nothing was staged; `git diff --cached --stat` was empty.

| Scope | Files | Insertions | Deletions |
| --- | ---: | ---: | ---: |
| Tracked working-tree diff | 17 | 1,114 | 120 |
| Untracked text: embedding authorization test | 1 | 221 | 0 |
| Untracked text: Supabase configuration test | 1 | 31 | 0 |
| Untracked text: Phase B report | 1 | 58 | 0 |
| All changed text files | 20 | 1,424 | 120 |
| Untracked binary screenshot | 1 | binary | binary |

The connected phone's 20 files (+1,424/-120) exactly match the entire text working tree. There were 21 changed paths including the screenshot. The desktop's 8 files (+317/-61) cannot represent this complete workspace snapshot. A narrower or earlier desktop change view is the likely explanation; Git alone cannot identify its exact UI filter or timestamp. No missing-work conclusion is supported by these different display totals.

These nine paths were already dirty when Phase B started:

- `.env.example`
- `apps/api/src/ps01_api/integrations.py`
- `apps/api/src/ps01_api/main.py`
- `apps/api/tests/test_integrations.py`
- `apps/api/tests/test_embedding_authorization.py`
- `apps/web/src/app/auth/settings/route.ts`
- `apps/web/src/app/login/page.tsx`
- `apps/web/src/lib/supabase/env.ts`
- `apps/web/tests/supabase-config.test.mjs`

They contain accumulated provider/embedding authorization and sign-in configuration work. Phase B added 12 newly changed paths and additional Ask/source/history hunks in the already-dirty `main.py`; its exact 13-file list remains in [the Phase B report](PHASE_B_ASK_REPORT.md). This follow-up changes no application or test code; its only new versioned file is this report. The user's final instruction explicitly authorizes committing and uploading all accumulated updates.

## Generation inspection and single live Ask

Inspected the existing generation adapter, trusted `GENERATION_POLICY`, canonical prompt preparation, response schema, model routing, and timeout/error handling. The configured models remain `gemini-3.8-flash` and `gemini-3.7-flash`, with the existing primary/secondary project configuration and a 45-second generation budget. Credentials were used only at runtime and were not printed. Circuit delays remain bounded to 30-120 seconds; the elapsed cooldown exceeded that limit.

The request uses `systemInstruction` for application policy and `responseSchema` with `application/json` for claims containing evidence IDs only. Gemini selects evidence; the server resolves authorized canonical assertions and citations. It does not accept model-written factual prose. The relevant fields remain documented in [Google's generateContent API reference](https://ai.google.dev/api/generate-content#v1beta.GenerationConfig), although `responseSchema` is now marked deprecated. Its deprecation alone was not treated as a request defect or a reason for an unrelated migration. The existing low thinking setting is described in [Google's thinking documentation](https://ai.google.dev/gemini-api/docs/thinking).

Automatic approval review initially rejected the live operation because of possible invoice-data egress. No Ask ran on that rejection. A read-only check then verified all 19 local documents against the repository's fictional fixture hashes, including the Acme invoice PDF and scan. Before submitting Ask, the request script also required all current typed rows to match the fictional fixtures exactly. With that evidence, review allowed the same single normal request.

One authenticated CEO request was sent over HTTP to the already-running app's `/api/v1/chat/query` endpoint. No ASGI/mock transport, provider interceptor, configuration change, circuit reset, or repeated Ask was used. Only existing automatic fallback bounds were available.

- Question: `What is the total amount on Acme invoice ACM-INV-2048?`
- Completed: `2026-10-10T06:22:37.684930+00:00`.
- Request: `8f85555a-3b8d-4e0e-ac2d-0d28a694e9a6`.
- Conversation: `05705553-96bc-4baa-9f3a-5b441ebe6389`.
- App HTTP status: **200**.
- Genuine generation: **`gemini-3.8-flash`, primary project, HTTP 200, success**.
- Generation attempts: **one**, 5,259 ms; no model/project fallback was needed.
- Total app timing: 6,604.5 ms.
- Released state: **`CITATION_VALIDATED`**, `response_mode=model_generated`, `provider_failure=null`, `fallback_used=false`.
- Released claim: **Invoice ACM-INV-2048 for Acme Manufacturing totals USD 48,000.00.**
- Citation: structured `invoices` table, row `ACM-INV-2048`, evidence ID `52d481a8-7492-4488-8eb0-272df662e660:0`.

An authenticated read of that exact citation's source endpoint returned HTTP 200. Its citation ID, evidence ID, source type, location, and excerpt exactly matched the released citation. The current canonical row contained `total_minor_units=4800000` and `currency=USD`. Ordinary conversation history was saved. No source data was changed.

The generation blocker did not recur in this request. No concrete code/configuration/request defect was demonstrated, so none was changed. This success does not establish the root cause of earlier timeouts or guarantee sustained provider availability. It verifies one genuine model-selected, canonically rendered answer; it does not establish general semantic entailment or hosted behavior.

## Verification and delivery scope

No suites, builds, browser matrices, migrations, reseeding, or unrelated UI changes were run. `git diff --check` passed, and the 21 previously changed files contained no matches for the actual runtime provider/server secrets or demo passwords, or the checked credential/private-key patterns. Private environment files, demo credentials, and local result artifacts remain ignored.

Machine-readable live response and source verification: `data/local/phase-b-live-generation-20261010.json` (ignored; contains no credentials). The earlier controlled-outage evidence remains unchanged and correctly labeled in the Phase B report.

The initial GitHub fetch failed because SSH port 22 timed out. GitHub documents [SSH on port 443](https://docs.github.com/en/authentication/troubleshooting-ssh/using-ssh-over-the-https-port); delivery can use a command-scoped override for `ssh.github.com`, keeping existing credentials, host-key verification, and the configured remote unchanged. Commit/upload results are reported separately after execution.
