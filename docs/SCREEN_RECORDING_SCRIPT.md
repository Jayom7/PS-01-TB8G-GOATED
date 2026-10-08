# Screen Recording Script

## Capture setup

- Start Docker/Supabase, API, and web using `README.md`; capture only after
  health, authentication, source list, and local evaluation are confirmed.
- Use a 1440×900 desktop viewport for the main recording; record a short
  responsive check at 390×844 only if the browser is live and content loads.
- Use synthetic records and the local seeded CEO login. Retrieve credentials
  locally from the ignored owner-only `.local-demo-credentials.json`; do not
  show its contents, terminals containing environment values, or browser
  credential autofill.
- Check Gemini once. If it is rate-limited/unavailable, do not fake a successful
  answer; pause the answer segment and narrate that the live provider is
  unavailable. Resume recording after quota/access is restored for a complete
  live Ask flow.

## Exact screen sequence

1. **Login:** show Clearframe sign-in, enter the seeded CEO credentials off
   screen, and land on Dashboard.
2. **Dashboard:** hold on authenticated identity, CEO context, source/chunk/
   structured record totals, and the system status labels.
3. **Ask (Finance):** choose Finance Manager in the account/profile menu; keep
   the identity label visible. Ask “What amount is shown on Acme's scanned
   invoice?” Wait for a real answer. Show inline citation, open its source, and
   hold on excerpt plus OCR location.
4. **Ask (HR denial):** close the source drawer, switch only the active context
   to HR Manager, repeat the exact question, and show the insufficient evidence
   message. Keep the same authenticated CEO identity visible.
5. **Security:** show scope and the retrieval boundary. Keep “not independently
   measured in this trace” visible; do not crop it out.
6. **Evaluation:** show the local/synthetic/not-production-benchmark label and
   metrics. Use a current run if local Supabase is active; otherwise identify
   the values as historical recorded metrics.
7. **Ingest:** show source types and the honest “Indexing source…” status text.
   Do not imply separate upload/processing/embedding stages are reported.
8. **Sources:** search and open an authorized source preview; do not show
   unauthorized source metadata.
9. **Optional mobile:** at 390×844, show mobile navigation and source drawer
   only after checking no horizontal overflow or hidden content.

## Voiceover guardrails

Describe local test evidence as local and historical when not rerun. The
security trace does not count unauthorized evidence; pgTAP evidence does not
prove hosted policies. Canonical evidence-ID selection does not establish general semantic
entailment. Never call the app production-ready.
