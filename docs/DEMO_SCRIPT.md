# Judge Demo Script (3–5 minutes)

## Preflight

Use `README.md` to start local Supabase/API/web. Sign in with the seeded local
CEO identity; the ignored owner-only `.local-demo-credentials.json` contains
the current demo passwords. Confirm workspace data loads. Make one readiness
check of Gemini; if it returns HTTP 429, do not keep retrying and do not
substitute a mock answer. The live Ask portion requires quota/access.

## Walkthrough

1. **Introduce (20 sec).** “Clearframe answers across documents, OCR images,
   and structured business records while keeping the caller's authorization
   context attached to retrieval.”
2. **Unified knowledge space (20 sec).** Open Dashboard, point out identity,
   active context, authorized source/chunk/record counts, and system status.
   Say Gemini is configured only; its availability is not implied.
3. **Finance answer (45 sec).** In Ask, enter “What amount is shown on Acme's
   scanned invoice?” as Finance Manager. Open the citation and source drawer;
   show the authorized excerpt and OCR location. Explain that the server resolves selected evidence IDs to canonical excerpts;
   semantic entailment and relevance are not independently verified.
4. **Authorization denial (35 sec).** Keep the signed-in CEO identity
   unchanged, switch active context to HR Manager, and ask the same finance
   question. Show `INSUFFICIENT_EVIDENCE`; explain the role session is used by
   database retrieval. Do not claim an independently measured unauthorized
   evidence count.
5. **Security (35 sec).** Open Security. Show identity, active context, scope,
   recent authorized retrieval count, and the flow Identity → Authorization →
   Secure retrieval → Authorized evidence → Generation. Distinguish design,
   historical local pgTAP evidence, and unverified hosted state.
6. **Evaluation (35 sec).** Open Evaluation. State that the recorded metrics
   cover a small synthetic local smoke set, not production retrieval quality
   or semantic answer quality. Re-run only if local Supabase is available.
7. **Multimodal ingestion (30 sec).** Open Ingest. Describe PDF text/scanned
   page OCR, PNG/JPEG OCR, and structured-row normalization. Point to
   per-stage progress being unavailable; the UI reports one honest indexing
   state. Demonstrate only if the local writer and database are active.

## If provider/runtime is blocked

Do not present a generated answer or successful retrieval as current. Show the
clear provider-unavailable UI if appropriate, explain prior 429 observations,
and continue with repository screenshots or evaluation only when those are
truthfully labeled as previously recorded. The recording script covers exact
states and fallback framing.
