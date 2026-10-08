# API Contract

Base path: `/api/v1`. User endpoints require a Supabase Auth bearer session.
The API validates the session through Supabase Auth and forwards the same
token to user-scoped database requests. Client-supplied user, role,
organization, ACL, and evidence values are never authorization proof.

## Implemented

- `GET /health`: liveness only; it does not validate providers or database.
- `POST /chat/query` (`/api/v1/chat/query`): accepts `{ "query": string }`;
  extra fields are rejected. Returns `request_id`, a citation-validation state, validated
  claims with server-built citations, and a minimal safe trace.
- `GET /sources/{citation_id}` (`/api/v1/sources/{source_id}`): resolves one
  chunk under the current user session. Missing and RLS-hidden rows share a
  404 response.

The query path uses the user's session for retrieval; it does not use
`SUPABASE_SECRET_KEY`. The migration and provider requests remain unverified in
the live project.

## Query result

`state` is `CITATION_VALIDATED`, `PARTIALLY_CITATION_VALIDATED`, or
`INSUFFICIENT_EVIDENCE`.
Claims contain text and citation objects built only from the exact bounded
evidence context sent to generation. Model-proposed IDs that were not in that
context are discarded. PDF citations need a page; structured citations need a
table and row; image citations need an image ID and include OCR region metadata
when available. Citation validation proves ID membership and source-location
shape; it does not prove that the cited passage semantically entails the claim.

The trace reports that the session was verified, that the database request
used that session, and how many evidence objects were passed to generation. It
does not report denied-resource details.

## Planned, not implemented

- `POST /ingestion/jobs` and `GET /ingestion/jobs/{job_id}`
- `GET /demo/identities` and `POST /demo/session`
- `GET /security/trace/{request_id}`
- `GET /evaluation/summary`

These routes require a validated authorization/data model before they are
exposed. No evaluation metrics or demo users are fabricated.
