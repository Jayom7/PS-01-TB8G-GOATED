# Security Architecture

## Assets and trust boundaries

Assets include source documents and rows, names and metadata, embeddings,
authorization policies, user identity, prompt context, citations, audit data,
and provider credentials. Trust boundaries are the browser/API boundary, the
API/database boundary, normal-user versus administrative database access, and
the API/provider boundary. Uploaded documents and model output are untrusted.

## Identity and policy

Supabase Auth is the identity provider. FastAPI asks the Auth user endpoint to
validate the bearer session before using it. User ID, organization membership,
roles, and grants must come from the validated session and database records,
never from request fields. The current query route does not accept identity or
role fields. Demo role switching must select a real seeded demo identity/session
rather than overwrite a role label in client state.

Authorization is default-deny and combines organization boundary, subject or
role grant, resource/source ACL, and classification. Document grants may flow
to derived chunks only through explicit, auditable inheritance. Structured
records carry row-level access policy. An explicit chunk override is allowed
only where a source requires finer restrictions.

## Retrieval boundary

All query and source-preview operations run under the requesting user's
database identity. Authorization predicates execute within the database
retrieval operation. The ordinary path cannot query broadly with an elevated
credential and then filter in the API. RLS is defense in depth and the
database tests must prove both authorized retrieval and absence of denied
rows in the exact evidence context passed to generation.

An ingestion path is not implemented. Any future privileged path must be
separate, server-only, and narrowly authorized for its write duties. Any future
privileged database function requires a narrow contract, non-exposed schema
where possible, pinned empty `search_path`, fully qualified objects, explicit
execute grants, and dedicated abuse tests. Avoid security-definer functions
unless the measured design requires one.

## Metadata and side-channel handling

Unauthorized resources must be indistinguishable from absent resources in
query responses, source lookup, citation resolution, counts, debug output, and
error shape. Search candidate counts are computed only over the authorized
result set. Logs and user-visible traces may report safe stages and authorized
counts only; they never contain denied names, IDs, snippets, embeddings, or
raw document contents. Sensitive source preview requires the same policy check
as retrieval.

## Generation and citation controls

Only the exact bounded retrieval response is sent to the model; database
authorization for that response remains unverified until RLS tests pass.
Document text is treated as untrusted data, not instructions. Model-generated
IDs are merely proposals. The current deterministic validator checks ID
membership and source-location shape; it does not verify that a cited passage
entails the claim. The API reports citation validation accordingly. Semantic
claim support, provider failure behavior, and prompt-injection resistance still
need explicit tests. No context expansion or automatic retry occurs.

## Secrets and operational controls

Secrets are read at runtime from environment/secret storage. Gemini and
`SUPABASE_SECRET_KEY` remain server-side; the browser receives only the public
Supabase URL and publishable key. The current user-query and source-lookup paths
do not use the secret key. Do not log tokens, secrets, raw prompts, or
protected source text. Upload validation, file-size/type limits, rate limits,
request IDs, and bounded provider timeouts remain requirements for the
unimplemented ingestion path.

## Verification gate

Before describing the prototype as enforcing retrieval-time authorization,
tests must capture the exact objects passed to the model and assert that every
one is authorized. Six local unit tests cover bounded model context and
citation filtering, but they do not exercise PostgreSQL or Supabase RLS.
Database tests must cover cross-role and cross-organization denials, denied
metadata/source lookup, manipulated IDs/claims, and the normal authorized path.
The draft migration has not been applied; it is not evidence that the system
currently enforces these controls.
