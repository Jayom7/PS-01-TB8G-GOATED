# Judge Demo Plan

## Product story

NovaCore Industries uses one secured knowledge workspace for contract PDFs,
scanned invoices, OCR regions, and structured finance/HR/sales/product rows.
The UI makes the active identity, allowed evidence, and exact citations
visible without exposing denied sources.

## Three-to-five-minute flow

1. Sign in with the local CEO account, then switch to Finance Manager from the
   sidebar account menu. The switch changes the Supabase Auth session.
2. Ask: “What amount is shown on Acme's scanned invoice?” Open the inline OCR
   citation and inspect its authorized excerpt and image provenance.
3. Ask: “What payment terms are specified in Acme's contract?” Then ask:
   “Is Acme overdue, and what payment terms does its contract specify?” The
   latter is the cross-modal PDF plus structured finance case.
4. Switch to HR Manager and repeat the finance query. Show controlled
   insufficient evidence and a safe trace with zero finance evidence IDs.
5. Ask to ignore permissions and reveal finance data. Show that the user prompt
   cannot widen retrieval and no unauthorized evidence reaches generation.
6. Open a source directly from Sources, then show the measured retrieval
   evaluation. An indexed-document prompt injection is a review test, not a
   stable live demo until Gemini generation is reliable.

## Data requirements

The local seeded corpus currently contains 19 sources, 45 chunks, and 7
structured records, including synthetic customer, finance, HR, sales, and
engineering material; PDFs; and OCR images. Use fictional names, amounts,
dates, IDs, and policy content. Sources have role grants and citation
locations. The latest six-case local retrieval/RLS run reports Recall@12 1.0,
MRR 0.775, and zero authorization leaks. Those figures describe a small local
retrieval set, not semantic answer quality or hosted behavior.

## Reliability requirements

Pre-seed only synthetic demo data. Show explicit loading and error states. The
latest browser run returned one real Gemini invoice answer with an OCR
citation, while separate contract, invoice-status, cross-modal, and indexed
prompt-injection attempts had timeout or malformed-provider failures. Treat
those paths as unstable. Keep one repeatable allowed query and one denial
query as acceptance paths; the browser-confirmed finance denial is stable.
