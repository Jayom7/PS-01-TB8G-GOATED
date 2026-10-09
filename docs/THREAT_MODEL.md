# Threat Model

## Scope and actors

Assets: protected document/row content and metadata, source existence, user
and organization identity, ACLs, embeddings, prompt context, citations, audit
records, and Gemini/Supabase credentials. Actors: authorized users, users with
other roles/tenants, malicious or compromised users, malicious document
authors, and external model/provider failures. Trust boundaries are browser to
API, API to database, normal query to privileged ingestion, and API to model.

## Threats and controls

| Threat | Primary control | Required evidence |
|---|---|---|
| Client forges user, role, tenant, or ACL | Verify JWT; resolve policy server-side | Tampered identity and arbitrary tenant tests |
| Retrieval fetches denied chunks then filters in app | User-scoped DB identity and RLS in retrieval query | Capture exact model context; assert denied IDs absent |
| Metadata/source-existence leak | Same policy on search, source lookup, counts, traces, errors | Denied title/ID/count/source-preview tests |
| HNSW filtered search misses allowed evidence | Measure filtered recall; iterative scan/exact fallback if needed | Query plan and recall by ACL selectivity |
| Malicious document prompt injection | Treat retrieved text as data; no tools; cite only evidence | Poisoned-document test and context inspection |
| Model invents claim or citation | Canonical evidence-ID selection renders source excerpts and rejects bounded payment conflicts; general semantic support remains unverified | Invalid ID tests exist; entailment and prompt-injection evaluation remain |
| Unauthorized citation lookup | Re-authorize source endpoint under caller identity | Guessed source-ID tests |
| Service-role key reaches browser/logs | Server-only config and secret scanning | Build/env inspection and repository scan |
| Malicious upload/parser abuse | Type/size validation, isolated parser limits, bounded work | Invalid/oversize/corrupt fixture tests |
| Audit trace exposes source content | Minimize stored fields and scope audit access | Trace redaction tests |
| Retrieval candidates misrepresented as outbound evidence | Capture exact serialized payload IDs/hash at each provider boundary; fail closed on initial audit failure | Recording transport + real local RLS manifest comparison; browser detail/write denial |
| Provider outage or malformed response | Bounded timeout/retry; fail closed | Simulated timeout and invalid response tests |

## Residual risks

Local deterministic adversarial/context tests, 55 SQL assertions and 51 live authorization/refusal checks pass. Real primary/fallback business answers and one explicitly untrusted literal poison inspection passed. A Finance integration independently captured outbound IDs and compared them with actual RLS visibility; both attempts matched. Its primary deadline was deliberately interrupted, while all external dependencies and fallback were real. This is bounded integration evidence, not exhaustive injection resistance, source truth or global leak certification. General entailment, representative-scale recall, hosted deployment and production parser/storage isolation remain unverified. No atomic revocation guarantee spans external generation. See MASTER_ACCEPTANCE_CHECKLIST.md for exact successes and intermittent provider failures.
