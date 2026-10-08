# Judge Demo Plan

## Product story

NovaCore Industries uses one secured knowledge workspace for contract PDFs,
scanned invoices, OCR regions, and structured finance/HR/sales/product rows.
The UI makes the active identity, allowed evidence, and exact citations
visible without exposing denied sources.

## Three-to-five-minute flow

1. Show the unified workspace and switch to Finance Manager.
2. Ask for an overdue customer amount and the payment terms in its contract.
   Show a structured invoice/payment row plus exact contract page citations.
3. Open a citation to show the exact row/page/region and provenance.
4. Switch to HR Manager and repeat the finance query. Show controlled
   insufficient evidence and a safe trace with zero finance evidence IDs.
5. Ask to ignore permissions and reveal finance data. Show that the user prompt
   cannot widen retrieval and no unauthorized evidence reaches generation.
6. Optionally show ingestion status and measured evaluation runs.

## Data requirements

Create synthetic, internally consistent customers, contracts, invoices,
payments, employees, policies, projects, orders, and a few scanned images. Use
fictional names, amounts, dates, IDs, and policy content. Ensure each source
has a corresponding ACL and citation location. Do not fabricate evaluation
results; render metrics only from real runs.

## Reliability requirements

Pre-seed only stable synthetic demo data. Show explicit loading and error
states. The role switch must switch authenticated identity, not merely alter a
front-end label. Keep one repeatable allowed query and one repeatable denial
query as acceptance paths. Demo script is not complete until these run against
the implemented database and tests.
