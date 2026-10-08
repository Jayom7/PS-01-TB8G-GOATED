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
| Model invents claim or citation | Current control validates citation IDs and provenance only; semantic support remains unverified | Invalid ID tests exist; entailment and prompt-injection evaluation remain |
| Unauthorized citation lookup | Re-authorize source endpoint under caller identity | Guessed source-ID tests |
| Service-role key reaches browser/logs | Server-only config and secret scanning | Build/env inspection and repository scan |
| Malicious upload/parser abuse | Type/size validation, isolated parser limits, bounded work | Invalid/oversize/corrupt fixture tests |
| Audit trace exposes source content | Minimize stored fields and scope audit access | Trace redaction tests |
| Provider outage or malformed response | Bounded timeout/retry; fail closed | Simulated timeout and invalid response tests |

## Residual risks

Controls are partial. Local tests cover prompt-context bounds and citation
membership, but not model obedience, semantic entailment, database RLS, or
live retrieval. RLS semantics for vector queries, policy
inheritance/revocation behavior, HNSW recall under selective ACL predicates,
and exact authorized-context capture remain review gates in
`REVIEW_NEEDED.md`.
