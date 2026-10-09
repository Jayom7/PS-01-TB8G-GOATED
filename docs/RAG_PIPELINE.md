# RAG pipeline

Phase 1 update: after generation returns or exhausts transient failures, the API rechecks actor/org/role and current RLS chunks before final validation. Progress contains only a stage name. Current generation failure can produce `VERIFIED_EVIDENCE`: conservative deterministic extraction of one invoice's amount, terms/status, requiring every requested fact/modality and consistent canonical values. It uses the existing citation validator/exact previews, labels the answer as composed without a language model and preserves provider cause/attempts without claiming generation success. Unsupported, ambiguous, incomplete, poisoned or contradictory evidence abstains. Authentication/configuration/safety/malformed-output errors never trigger this mode. Embedding/retrieval still need configured services; this is not offline RAG.

Replay reconstructs from current evidence and states provider availability was not rerun. General entailment and atomic external-call revocation remain unimplemented guarantees. The latest Phase 1 acceptance section gives current tests/data counts; runtime observations below are from the earlier end-to-end pass.

PDF extraction preserves pages; scanned PDFs use local OCR. Images undergo signature/header/decode checks and retain OCR coordinates. Limits: 25 MB, 100 PDF pages, 16 million decoded pixels, 1,000 OCR regions. These are bounded demo parsers, not production process isolation. Structured ingestion whitelists seven typed tables, validates business fields, inserts under server-assigned tenant/source IDs, rereads the row and embeds its canonical text. Money is integer minor units; overdue status uses the row's explicit snapshot date.

1. Verify Auth and resolve the local actor/org/role-bound context.
2. Handle exact greeting/thanks helpers without lookup or model calls, clearly labeled.
3. Embed once; retrieve once via caller-scoped invoker RPC/RLS. Explicit invoice IDs restrict retrieval to matching authorized documents (including individually authorized sibling regions). Unknown IDs do not substitute similar invoices. Zero keyword matches receive no keyword-rank bonus.
4. Re-read selected chunks under current RLS and remove changed, deleted or revoked evidence. Canonical passage IDs carry exact page/row/region locations with a 16,000-character content budget. Single-invoice document identity may link currently visible OCR/PDF siblings; ambiguous documents do not inherit that identity. Every prompt entry has a bounded server-calculated eligibility flag; validation still rejects ineligible selections.
5. Refuse without generation when no relevant authorized evidence exists. Refusals reveal no restricted source names or metadata.
6. Use designated systemInstruction for application policy; send question and evidence as untrusted data. Before EACH model attempt, recheck the actor/context and current source state.
7. Accept structured evidence_ids only. Reject fabricated text/quotes/unknown IDs, genuine unrelated/poisoned selections and same-invoice paid/unpaid conflicts. Literal suspicious-text inspection is explicitly quoted as untrusted.
8. Render server-owned passages and bounded invoice/OCR business summaries. Stream only validated final content and save real actor/org/context history. Replay rebuilds from currently authorized citation chunks and independently RLS-visible siblings, preserving invoice identity without trusting saved metadata.

CITATION_VALIDATED is bounded canonical provenance, not general semantic entailment, source truth, exhaustive relevance/contradiction detection or proven model obedience. The UI states this boundary. No atomic guarantee spans final RLS checks and external generation.

## Routing and evidence

The account inventory returned both configured generateContent models (gemini-3.8-flash and gemini-3.7-flash); gemini-embedding-2 at 1536 dimensions remains unchanged. Capability inventory caches for five minutes by credential fingerprint. Only configured supported models are eligible. No additional provider or guessed model is introduced.

At most two distinct attempts, 20 seconds per attempt/connect 5, bounded 250 ms backoff and 45 seconds total by default (GENERATION_BUDGET_SECONDS, 1–60). Transient 503/network/timeout may switch once. A 429 switches only when all reported quota violations explicitly name a model; unknown/project/global quotas stop immediately. Retry guidance is preserved; malformed output, invalid key/request and safety blocks are terminal. One failed attempt does not repeat embedding/retrieval.

Actual generation now succeeds: browser 3.8 Flash OCR/contract, normal API 3.8 Finance and 3.7 fresh-source fallback. The normal fresh fallback returned checked PDF/typed claims (partial validation; an OCR selection was rejected). A controlled-primary-timeout real API integration returned three validated modalities using 3.7 Flash, with actual previews and independent outbound-ID/RLS checks. Some other normal requests and the latest full verifier still return 503/timeouts. These failures and successful-answer timings are both retained in the acceptance evidence.

Gemini 3 Flash uses the officially supported low thinking level for bounded evidence selection; other model families retain their supported default. System policy, provenance, RLS rechecks and contradiction checks remain mandatory. Safe per-model attempts include elapsed time, HTTP status and machine cause. [Official thinking configuration](https://ai.google.dev/gemini-api/docs/generate-content/thinking).
