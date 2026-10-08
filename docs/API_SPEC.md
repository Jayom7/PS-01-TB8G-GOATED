# API Specification (Planned)

Base path: `/api/v1`. All user endpoints require a Supabase Auth bearer token.
Identity, organization, and role are derived server-side. Client-supplied
`user_id`, `role`, `organization_id`, ACL, or source authorization are never
proof of access.

## Errors

Return `{ "error": { "code": "...", "message": "...", "request_id": "..." } }`.
Use stable generic messages for inaccessible and nonexistent resources. Do not
return hidden titles, IDs, snippets, counts, or policy details. Validation
errors may identify invalid input fields but must not echo protected data.

## Endpoints

- `GET /health`: liveness/readiness metadata without secrets or database rows.
- `POST /chat/query`: `{query, conversation_id?}` → answer state, validated
  claims, citations, request ID, and safe retrieval trace. No client-supplied
  role or evidence. Responses support `answered` and `insufficient_evidence`.
- `GET /sources/{source_id}`: authorized exact source metadata and preview
  location only; inaccessible and absent IDs share the same response.
- `POST /ingestion/jobs`: administrative scope only; accepts an allowlisted
  source reference or upload and returns job ID/state. This path uses separate
  authorization and credential handling.
- `GET /ingestion/jobs/{job_id}`: caller may see only jobs they can administer.
- `GET /demo/identities`: list synthetic demo identities only in demo mode.
- `POST /demo/session`: select a seeded demo identity through a server-verified
  demo mechanism; disabled outside explicit demo configuration.
- `GET /security/trace/{request_id}`: safe trace for the requesting user or
  authorized reviewer; no denied-resource detail.
- `GET /evaluation/summary`: measured evaluation results and run/config IDs;
  no hardcoded percentages.

## Query contract

Response claims are `{text, citation_ids[]}`. Each citation includes stable
source ID, source type, display-safe title, exact location (page, row, or OCR
region), and a server-generated preview reference. The API emits only citations
validated against the retrieved authorized evidence context. Empty support
returns the fixed insufficient-evidence state.

## Operational behavior

Validate payload lengths, MIME types, and pagination bounds. Apply bounded
timeouts and provider error mapping. Query/source responses carry request IDs.
No raw model output is forwarded before schema and citation validation.
