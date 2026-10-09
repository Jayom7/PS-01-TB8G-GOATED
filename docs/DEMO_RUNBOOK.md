# Demo Runbook

Current status (2026-10-09): local stack and source/security checks pass. Gemini generation is blocked by observed 503 then raw 429 quota exhaustion. No generated flow below has fresh successful acceptance in this pass. Do not repeatedly call the provider before its reported retry interval has elapsed.

## 1. Start and preflight

Start the existing Docker engine. From the repository root:

```sh
./scripts/dev --seed
```

After the seed exists, use `./scripts/dev` for later launches. In another terminal:

```sh
./scripts/verify_demo
```

This applies no hosted changes or reset. Seed failures are failures; rerun only after diagnosing them. If Docker is unavailable, the launcher exits 2 before starting an incomplete app. If Gemini returns 429/503, do not loop.

## 2. CEO login and Overview

Open `http://localhost:3000/login`. Use the CEO entry in ignored `.local-demo-credentials.json` offscreen. Keep the signed-in CEO visible; counts must come from the running database. Fixture extraction counts are not live workspace counts.

## 3. OCR amount — flow A

In CEO or Finance Manager context ask: **What amount is shown on Acme's scanned invoice?** A successful answer should cite the OCR source. Open its inline citation; inspect the original image and highlighted OCR region. Do not accept an answer without the real source lookup.

## 4. PDF, database and cross-modal answers — flow B

For the direct PDF flow ask: **What payment terms are in Acme's contract?** Require the real `ACM-MSA-2026-07` contract page and canonical excerpt.

Ask: **Is Acme's invoice overdue and what payment terms does its contract specify?** Inspect both `invoices / ACM-INV-2048` and the contract PDF page. The row is unpaid, due 2026-10-01, with status snapshot 2026-10-08; contract terms are Net 30. These are expected synthetic facts, not a prefilled answer or a promise that the model will select both sources.

For a direct database check ask: **Is invoice ACM-INV-2048 paid?** The inspector must show actual persisted table fields.

## 5. HR contrast and forbidden preview — flows C/D

Close the inspector; select HR Manager in the account menu, preserving CEO browser identity. Repeat the finance question. Require insufficient authorized evidence with no finance title/excerpt. In a controlled local test, requesting the previously visible finance citation/original under HR context must return the same 404 as a missing source. Use the real verification suite; editing UI labels alone is not proof.

## 6. Security, trace and saved history — flow F

Return to CEO context. Show Security's retrieval boundary and explicit unmeasured/live-policy limitations. Open Retrieval Trace from a real answer: question, identity, authorization, evidence count, actual model, citation resolution, and measured stage durations. Ranking-only time is not separately measured. Save a real completed conversation, reopen it from History, restart with `./scripts/dev`, and reopen again; require current access checks and canonical citations. Empty history and unit tests do not prove this persistence flow.

## 7. Injection — flow E

Only if checked successfully in preflight, ask about the security policy while the poisoned `prompt-injection-test-01.pdf` is retrieved. Inspect the evidence and confirm its instructions did not override policy or introduce restricted content. A prompt string and unit test alone do not establish live model obedience.

## 8. Evaluation and ingestion

Run Evaluation only against the real current local stack. Explain hit rate@12, MRR, checked forbidden hits, and citation-location presence. Refresh labels saved measurements as recorded. CEO ingestion supports file/drop or a typed relational row; select a grant and show the real completion/error state. No per-stage ingestion job feed is available.

## 9. Acceptance checklist and provider-outage backup

The generated acceptance checklist is CEO OCR invoice, PDF contract, database invoice, cross-modal overdue/terms, HR same finance question and poisoned-source resistance; forbidden source preview is the seventh independent access flow. `verify_demo` automates OCR/HR generation plus security/source checks; it does not replace the other manual generated flows. For every displayed citation compare title, source, exact location and excerpt with the protected inspector. Inspect the evidence entering the actual generation flow, and never claim a trace alone independently captured the outbound provider prompt.

### Outage backup

Present the actual unavailable state. With a working database, use `./scripts/verify_demo --skip-generation` to demonstrate Auth, stored-vector authorized retrieval, forbidden-source denial, and pgTAP; exit 2 correctly means generation is incomplete. Show protected Sources/record/PDF/OCR previews directly and describe the architecture. Identify historical results as historical. If Docker is also down, show code/tests and clearly state that live acceptance is blocked. Never substitute the disposable visual fixture server for a live demo.
