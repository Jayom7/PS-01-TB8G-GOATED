# Demo runbook — current implementation

Phase 2 supersedes the historical missing-seed and six-query-only status below. Reuse `./scripts/dev` without `--seed`: current corpus19sources/45chunks/7typed rows. CEO → Security → **Run security checks** executes the genuine local verifier (58passed; generation explicitly not run). CEO → Evaluation loads the persisted32-query run and separately labelled7controlled adversarial checks; Run again reruns real role Auth/RLS/embedding retrieval. Current hit@12=1.0/MRR0.815/0authorization violations; abstention/fact checks are deterministic, not generated-answer scores. Inspect the role/question matrix and exact citation-location counts. Manifest details are intentionally server-only; controlled-outage verification compares stored IDs/hashes with outbound requests. See MASTER_ACCEPTANCE_CHECKLIST.md for timestamps/tests and remaining provider/hosted boundaries.

Latest Phase1 closeout: reuse the running normal launcher (no --seed). The actual app Evaluation run is persisted at12:00:27Z with18 sources/44 chunks/6 typed rows, six synthetic queries plus direct HR check, hit@12=1.0/MRR0.80/zero forbidden hits. Refresh reloads; Run again executes the suite. CLI provenance, previous runs, unavailable/restricted and genuine empty states are distinct.

Current real Ask: one bounded observation returned429 from both configured generators and a correctly labelled canonical verified-evidence response. Do not describe this as fresh Gemini success. Cooldowns avoid repeated outage calls and permit bounded recovery probes. Use `hi there`, `What can you do?`, or `thanks` for helpers without lookup; after a cited invoice, `Is it paid?` retrieves facts anew; `What about the invoice?` asks which fact is wanted. Incorrect IDs are never fuzzy repaired. Retry retains the question; long source/activity lists scroll with keyboard and native gestures.

Reproduce closeout checks: `.venv/bin/pytest apps/api/tests -q`; `node --experimental-strip-types --test apps/web/tests/*.test.mjs`; `.venv/bin/python apps/api/scripts/verify_evidence_mode.py` (only generation HTTP503 injected; real dependencies, disposable OCR cleanup); `node_modules/.bin/supabase test db`. The DOM-only `apps/web/tests/chat-layout.browser.js` function can be evaluated in a rendered Ask page at desktop/mobile sizes. It verifies actual alignment, composer, duplicate turns, overflow and failure-source bounds; it is not integration/generation proof.

Full `./scripts/verify_demo` still stops on the already missing `structured/orders.json` seed. Decide whether that deletion was intentional before restoring only that original manifest source/grants/row/chunk; never reset or full reseed to pass. Provider quota and fresh OCR-generated answer remain blocked; Google setup and password/timed expiry handoff remain as documented below. The detailed final status is in MASTER_ACCEPTANCE_CHECKLIST.md.

Previous Phase 1 snapshot: `VERIFIED_EVIDENCE` is explicitly composed without a language model after transient generation failure. Demonstrate this reproducibly with `.venv/bin/python apps/api/scripts/verify_evidence_mode.py`: generation HTTP503 is deliberately injected; Auth/RLS/embedding/OCR/history/previews/deletion are real. The script creates/deletes only its disposable OCR upload. Reopen its three-source Finance history to inspect the label/citations. This is not a live Gemini outage or successful model generation. Current full wrapper stops on the already-absent purchase-order fixture; see MASTER_ACCEPTANCE_CHECKLIST before attempting restoration.

Earlier end-to-end runs verified real primary/fallback answers and observed intermittent503/timeouts. The Phase 1 bounded attempt observed primary429 then fallback200; full seed readiness currently stops on the missing purchase-order fixture. Do not substitute fixture answers or repeatedly cycle unavailable models. Exact runtime scope is in MASTER_ACCEPTANCE_CHECKLIST.md.
## Start and verify

```sh
./scripts/dev
./scripts/verify_demo --skip-generation
# One bounded real provider verification:
./scripts/verify_demo
```

Start the existing Docker runtime first. ./scripts/dev reuses local data, applies additive migrations, configures the ignored local browser/API environment and starts API/web. Use --seed only for first-time synthetic setup, not to repair an unexplained failure. No reset/hosted operation. Local private credentials remain in ignored .local-demo-credentials.json. Open http://localhost:3000/login; sign in as local CEO. The real browser actor stays CEO when its demo access context changes.

--skip-generation intentionally exits2 (51 pass,1skipped generation). This is incomplete acceptance, not a failed authorization suite. Full verification stops bounded generation and reports actual provider causes. Read saved ignored reports under data/local/.

## Required recording sequence

1. Ask the amount on Acme's scanned invoice. Real browser 3.8 Flash returned USD 48,000.00; open exact OCR region/original.
2. Ask Acme contract payment terms and open PDF page 1. Generated concise30-day answer verified.
3. Select Finance context; ask invoice payment status. Real 3.8 answer and invoices/ACM-INV-2048 preview verified.
4. Ask “What is the scanned Acme invoice total, what payment terms does the PDF contract state, and is the database invoice unpaid? Cite all three source types.” A real API integration returned all 3 through 3.7 fallback with exact previews; primary deadline deliberately interrupted. Normal daemon combined attempts also failed503/timeouts. Show that scope honestly.
5. Select HR and ask the identical scanned amount question: no authorized relevant evidence,0 context/no model.
6. Forbidden citation/document/original/page lookups return404; live suite passes.
7. Actual literal poisoned document inspection quotes untrusted text without executing it; run adversarial regressions for forgeries/conflicts.
8. Show authenticatedCEO vs activeHR/Finance context; non-CEO forgedCEO denied.
9. Generated OCR/contract conversation→refresh→History reopen→actual API restart→reopen verified. Finance-owned generated cross-modal history also reopens under the real Finance actor. Replay performs current RLS reconstruction; it does not rerun Gemini.
10. Follow the fresh workflow below. Browser ingestion/actual retrieval passes; normal 3.7 fallback answered fresh PDF/database facts. A separate fully validated fresh OCR answer remains blocked.
11. Cancel named deletion, then delete only disposable sources. Resume30 checks verify actual generated replay invalidation, cleanup/audit/typed/RPC absence.
12. Six routes×2 themes×4 sizes passed48 combinations; populated Ask passed8 extra states. Inspect modal/navigation close/Escape/focus.

## Reproduce fresh-source checks

```sh
.venv/bin/python apps/api/scripts/verify_product.py --prepare-assets
```

Through Ingest's real browser file chooser upload data/local/acceptance-assets/fresh-acceptance.pdf and .png, granting Finance (CEO retained). Insert one invoices row with source name “Disposable invoice CF-INV-1009”; use the existing Acme customer identity from Sources. Set invoice_id CF-INV-1009, total_minor_units123400, currencyUSD, payment_statusunpaid and valid invoice/due/status_as_of dates; the form enforces its complete schema. Then:

```sh
.venv/bin/python apps/api/scripts/verify_product.py
# Delete only these three disposable sources through Sources, then:
.venv/bin/python apps/api/scripts/verify_product.py --verify-deletion
```

The first command checks real persisted vectors/RPC/previews/HR denials/typed amount/history/audit. The deletion command uses saved disposable IDs to check documents/chunks/grants/RPC/previews/original cleanup and invoice removal. Do not reuse/delete immutable seeded demo sources. The final verified state retains19 sources/45 chunks/7typed rows.

## Auth and outage handling

Google is disabled with an explicit configuration message. Exact operator setup is in SECURITY_ARCHITECTURE.md. Forgot password delivered a local Mailpit email (http://127.0.0.1:54324), exchanged its PKCE code in the same browser and displayed the reset form. New password entry/change is a user handoff; no account password was altered.

For provider 503, retain the visible question, inspect authorized sources, and show the real failure/retry state. Never call a failed request a valid answer. For429respect the returned retry interval; only explicit model-specific quotas may switch once. For API/network errors use Retry after confirming local service readiness. See MASTER_ACCEPTANCE_CHECKLIST for all remaining acceptance gaps.
