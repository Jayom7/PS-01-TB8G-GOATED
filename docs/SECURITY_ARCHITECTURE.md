# Security Architecture

## Boundaries

- Supabase Auth verifies identity; API schemas reject caller-supplied role, organization, ACL, and evidence fields.
- Ordinary retrieval/source paths forward user/broker JWTs to invoker RPC and RLS. No service-role broad read enters model context.
- Local CEO context switching resolves one of exactly five seeded role sessions while preserving the signed-in actor. Non-CEO context escalation is denied.
- CEO ingestion authenticates before reading/writing uploads, uses a separate privileged writer, and compensates failed writes by deleting the newly created source. PostgREST writes are separate operations, not one database transaction.
- Composite source/org foreign keys and restrictive live-record comparison protect structured origin and stale-index lifecycle.
- Provider output is untrusted. Only known canonical evidence IDs can produce excerpts; model text/quotes and bounded payment contradictions are rejected.
- Source bytes are local-only, path-contained, no-store, and authorized again by document RLS. Missing and forbidden source lookups share 404 responses.
- History is actor/org/context scoped; replay reauthorizes current chunks and reconstructs every claim. Directly written stored text cannot become an answer.
- Activity is session/context scoped and clears on process restart. No shared answer/evidence cache is introduced.

## Proof boundaries

76 local backend tests pass, including exact prompt construction, forged context, evidence regressions, protected preview, history replay with current source reauthorization and discarded client-written trace metadata, and SSE release ordering. A 43-assertion pgTAP suite is prepared for all roles, cross-org isolation, typed rows, stale/deleted records, revocation, and chunk-only grants. It could not execute: localhost Postgres refused connections.

Security describes architecture and real request events. It does not probe live policies or independently count unauthorized model evidence; no unmeasured numeric zero is shown. Evaluation's checked forbidden-hit count is restricted to its actual synthetic cases and is separate from model-context claims.

Hosted RLS, clean current database migration/seed, live role flows, and live prompt-injection outcomes remain unverified or blocked. General entailment, exhaustive injection resistance, filtered ANN recall, concurrency, production file storage, parser isolation, rate limiting, and transactional ingestion remain review items. See [review status](REVIEW_NEEDED.md).
