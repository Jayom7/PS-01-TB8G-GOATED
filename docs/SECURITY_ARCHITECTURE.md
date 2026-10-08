# Security Architecture

## Assets and trust boundaries

Assets include source documents and rows, names and metadata, embeddings,
authorization policies, user identity, prompt context, citations, audit data,
and provider credentials. Trust boundaries are the browser/API boundary, the
API/database boundary, normal-user versus administrative database access, and
the API/provider boundary. Uploaded documents and model output are untrusted.

## Identity and policy

Supabase Auth is the planned identity provider. FastAPI validates JWT signature,
issuer, audience, and expiry using the trusted project configuration. User ID,
organization membership, roles, and grants are resolved from trusted claims or
database records, never from request fields. Demo role switching must select a
real seeded demo identity/session rather than overwrite a role label in client
state.

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

The ingestion path is separate, server-only, and least-privileged for its
write duties. Any future privileged database function requires a narrow
contract, non-exposed schema where possible, pinned empty `search_path`, fully
qualified objects, explicit execute grants, and dedicated abuse tests. Avoid
security-definer functions unless the measured design requires one.

## Metadata and side-channel handling

Unauthorized resources must be indistinguishable from absent resources in
query responses, source lookup, citation resolution, counts, debug output, and
error shape. Search candidate counts are computed only over the authorized
result set. Logs and user-visible traces may report safe stages and authorized
counts only; they never contain denied names, IDs, snippets, embeddings, or
raw document contents. Sensitive source preview requires the same policy check
as retrieval.

## Generation and citation controls

Only the immutable authorized context is sent to the model. Document text is
treated as untrusted data, not instructions. The generation schema contains
answer claims plus references to supplied evidence IDs; model-generated IDs
are merely proposals. A deterministic validator checks that each factual
claim has one or more retrieved, authorized context entries and a precise
location. Invalid or unsupported claims are removed; if nothing supported
remains, return insufficient evidence. Provider failure, malformed output,
and timeout also fail closed without expanding context.

## Secrets and operational controls

Secrets are read at runtime from environment/secret storage. Gemini and
Supabase service-role credentials remain server-side; the browser receives
only the public Supabase URL and anon key. Do not log tokens, secrets, raw
prompts, or protected source text. Upload validation, file-size/type limits,
rate limits, request IDs, and bounded provider timeouts are implementation
requirements.

## Verification gate

Before describing the prototype as enforcing retrieval-time authorization,
tests must capture the exact objects passed to the model and assert that every
one is authorized. Database tests must cover cross-role and cross-organization
denials, denied metadata/source lookup, manipulated IDs/claims, and the normal
authorized path. No such implementation or test currently exists.
