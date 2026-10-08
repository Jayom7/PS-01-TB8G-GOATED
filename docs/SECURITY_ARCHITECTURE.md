# Security Architecture

## Implemented boundaries

- Supabase Auth supplies identity. The API validates the bearer token before
  protected workspace/query operations. Request bodies reject caller-supplied
  user, role, organization, ACL, or evidence fields.
- Normal query retrieval and source preview use the validated session with the
  database invoker RPC / RLS path; they do not use `SUPABASE_SECRET_KEY`.
- The CEO-only local demo switch broker resolves one of the five seeded role
  users server-side. The browser's signed-in identity remains separate from the
  active demo authorization context. The local feature is gated to loopback
  Supabase and the ignored credential file; it must not be enabled against a
  hosted project.
- Local CEO-gated ingestion is a separate server-side write path and uses a
  privileged key. It stores originals in private local storage.
- Retrieved evidence is bounded before generation. The model prompt treats
  evidence as untrusted data. Citation IDs and source locations are rebuilt
  from the retrieved context. Current claim validation additionally checks
  supplied exact excerpts and lexical overlap, but cannot establish semantic
  entailment.

## Evidence and status semantics

The code can assert that a query sends only the exact bounded result from the
authorized retrieval RPC; API tests capture that prompt context. The endpoint
does not independently measure a count of unauthorized evidence supplied to
the model, so Security and per-query traces must not display a numeric zero.
Local RLS/pgTAP results recorded in `REVIEW_NEEDED.md` establish only the state
tested at that earlier local run. The current local Docker API is inaccessible,
and hosted Supabase policy state has not been verified. Do not label either
state as currently verified.

The Security screen describes the architecture and displays recent in-process
retrieval events; it is not a live policy auditor, hosted RLS probe, production
security certification, or security score. Events clear when the API process
restarts. The Dashboard's Gemini value means configured/not configured only;
availability is not probed by that request.

## Preserve these invariants

1. The client cannot promote itself to CEO or forge a user/organization.
2. Normal retrieval never uses an elevated Supabase key.
3. Unauthorized evidence must not enter the exact model context.
4. Source preview repeats authorization under the current session.
5. Local role brokering and privileged ingestion remain local-only.
6. Provider output and uploaded content remain untrusted.

Changes to the RLS RPC, grants, role broker, service key boundaries, document
grant inheritance, or evidence-context construction require a focused security
review and database-backed authorization tests. Hosted security, representative
filtered-HNSW recall, semantic support, and production controls are open items
in `REVIEW_NEEDED.md`.
