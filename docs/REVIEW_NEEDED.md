# Review Needed

This file tracks open issues that require external state, database evidence,
or deeper review. It does not certify the system as secure.

## R-001 — RLS-aware retrieval

- **Implemented:** the API verifies the authenticated Supabase identity. For a
  local CEO demo account, an explicitly selected role context is validated on
  the server and resolved to that role's own Supabase session; that session is
  held only in API memory and forwarded to the invoker retrieval RPC. Other
  identities can only use roles assigned to them. Query code does not use the
  secret key. The migration enables RLS on every app table, removes default
  API-role table privileges before regranting required reads, and restricts
  retrieval RPC execution to authenticated users.
- **Verified locally:** migration applied to local Supabase; 24 pgTAP assertions
  pass for RLS, grants, RPC execution, CEO breadth, Finance/HR/Sales/Engineer
  allow/deny, unauthorized citation lookup, forged organization claims, and
  cross-organization isolation. The API rejects client-supplied user, role,
  organization, ACL, and evidence fields. Local schema lint passed earlier;
  rerun after any schema change.
- **Unverified on hosted project:** Supabase CLI authentication is missing, so
  hosted migration, request identity propagation, policies, and grants have
  not been checked there.
- **Next review:** authenticate Supabase CLI, link the existing project, apply
  the migration, then run the allow/deny suite against hosted state.
- **Boundary:** local allow/deny results do not verify the hosted project.
  Role switching is enabled only in the loopback local demo.

## R-002 — Filtered HNSW recall and query plans

- **Implemented locally:** HNSW and full-text indexes plus an invoker hybrid
  retrieval RPC are applied and exercised against local Supabase.
- **Verified locally:** latest six-case evaluation reports Recall@12 1.0 and
  MRR 0.775 over five retrieval queries plus one direct RLS check, zero
  authorization violations, and OCR, structured, and cross-modal retrieval
  coverage. It is a small synthetic smoke suite, not production evidence.
- **Unverified:** this sample is too small for production conclusions;
  filtered candidate recall, iterative scan settings, `EXPLAIN` plans, and
  representative latency have not been measured.
- **Next review:** benchmark authorized filtered queries and inspect query
  plans under representative ACL selectivity. Consider an exact authorized
  fallback if approximate retrieval underfills.

## R-003 — Demo identity lifecycle

- **Implemented:** real Supabase password sign-in, server route gate, and
  authenticated API calls. Role context is separate from the signed-in
  identity; the browser never receives the role account's access token. The
  client cannot submit user, organization, ACL, or evidence fields in a query.
- **Verified locally:** five NovaCore auth users, profiles, and role records
  exist in local Supabase. API tests verify CEO-to-role session resolution and
  deny a Finance identity's forged CEO context. Browser switching to all five
  roles changes authorized-source counts while preserving the CEO identity;
  RLS filtering hides the Acme invoice from HR. Local credentials remain in a
  git-ignored owner-only file. No hosted users were created.
- **Boundary:** switching is only enabled when both local Supabase and the
  ignored demo credential file are present. Do not enable this broker for a
  hosted project.

## R-004 — Ingestion and source storage

- **Implemented locally:** bounded PDF extraction, scanned-page/image OCR,
  structured-row normalization, Gemini embeddings, CEO-gated local upload and
  structured ingestion routes, private original-file storage, and role grants.
  PaddleOCR was exercised on the synthetic invoice scan.
- **Verified locally:** the seed pipeline indexed 19 sources, 45 chunks, and
  7 structured records; browser browsing and an authorized structured-source
  excerpt work against the production build. The production UI accepted a
  synthetic PDF and reported one indexed chunk. Direct local API checks also
  indexed a synthetic PDF, OCR image, and structured record; temporary rows,
  private files, and synthetic artifacts were removed after verification.
- **Not implemented:** background ingestion jobs. The local upload and
  service-key persistence paths have not been reviewed for hosted deployment.
- **Current runtime check:** Docker Desktop and local Supabase are running, and
  the API reports ingestion ready. Browser PDF upload succeeded. The upload
  control now clears its native file input after success so the same file can
  be selected again; the browser file chooser did not permit a second image
  selection during this pass. Image OCR and structured ingestion passed via
  the local API. No hosted admin credential was sent to the local database.
- **Progress detail:** the UI reports Ready, an in-progress combined upload /
  processing / embedding state, Indexed, and Failed. It does not yet receive
  exact server-side per-stage progress events.
- **Next review:** recheck same-file selection in the browser after the input
  reset fix. Review source provenance, write rollback, and access inheritance
  before any hosted ingestion deployment.

## R-005 — Live provider and database connectivity

- **Verified:** local Supabase Auth and API health/workspace/source requests
  work. Live Gemini embedding produced 1536 dimensions. Earlier, the production
  browser returned a CEO invoice answer with an OCR citation using 3.6 Flash,
  and opening the citation returned the authorized excerpt. Current chat config
  follows the requested `gemini-3.8-flash` primary and `gemini-3.7-flash`
  conditional fallback. Live probes reached Gemini after successful embedding
  and authorized retrieval, but both 3.8 and 3.7 returned HTTP 429; a 2.5
  compatibility probe returned HTTP 404 and was removed from configuration.
  The supplied AI Studio screenshot shows 3.8 and 3.6 above the displayed daily
  cap and only one daily 3.7 request remaining. Generation is blocked by
  current provider quota/access; do not describe a live answer as verified.
- **Blocked:** hosted database migration and schema checks require Supabase CLI
  authentication or direct database credentials. Current API keys alone do
  not provide the CLI project token or database password.

## R-008 — Live Gemini answer reliability

- **Implemented:** `gemini-3.8-flash` primary generation, one conditional
  `gemini-3.7-flash` fallback attempt for transient failures, explicit fallback
  tracing, citation membership validation, and
  distinct safe messages for timeout, unavailable provider, and invalid model
  output.
- **Observed:** an earlier browser answer succeeded using 3.6 Flash. In the
  latest checks, embedding/retrieval succeeded but 3.8 and its 3.7 fallback
  returned HTTP 429. The supplied AI Studio screenshot showed 3.8 and 3.6 above
  their displayed daily caps and 3.7 with one request remaining. A 2.5 probe
  returned HTTP 404 for this key and is not configured. Exact quota/access can
  change independently.
- **Next review:** after Gemini quota resets or billing is enabled in AI Studio,
  verify one controlled live Ask and repeat the four exact demo prompts and both
  injection cases; preserve safe diagnostics server-side without exposing keys.

## R-006 — Exact model-context authorization proof

- **Verified locally:** API tests confirm the model receives exactly the RPC
  result, pgTAP confirms finance/HR/cross-organization database boundaries,
  and retrieval evaluation reports zero forbidden-source hits.
- **Unverified on hosted project:** repeat these checks after applying the
  migration to the connected hosted project.

## R-007 — Semantic claim support

- **Implemented:** generated citation IDs must belong to the exact bounded
  model context and citations need a precise source location. The response
  state is `CITATION_VALIDATED` to describe that boundary accurately.
- **Missing:** the service does not establish that a cited passage entails the
  model's claim. Prompt instructions and citation membership alone do not
  prove grounding.
- **Next review:** define and measure claim-level support checks, including
  adversarial and prompt-injection cases, before labeling answers grounded.

## R-009 — Hosted environment and GitHub CLI

- **Blocked:** `supabase projects list` reports that no Supabase CLI access
  token is configured. No hosted project could be identified or safely linked;
  no hosted migrations, seeds, identities, or ACL changes were attempted.
- **Required:** authenticate the Supabase CLI and identify the intended project;
  then review its migration history and existing data before applying anything.
- **GitHub CLI:** the `gh` executable is not installed. Git remote points to the
  expected origin; commit/push status must be read from Git and is not inferred
  from local state.

## Plus / Sol 6 handoff

- Apply a premium visual direction with refined typography, spacing, and
  brand-specific details while retaining the current role/context model and
  accessible responsive behavior.
- Add server-driven ingestion progress events for Uploading, Processing,
  Embedding, Indexed, and Failed rather than the current combined in-progress
  status; test PDF, image, and structured uploads end to end.
- Measure ANN recall and SQL plans under representative role filters; keep the
  ranking stage timing limitation in mind because it is currently inside the
  database RPC duration.
- Research semantic claim entailment and adversarial retrieved-document prompt
  injection before claiming semantic grounding.
- Repeat deep RLS/security review and evaluate hosted policy behavior only after
  authenticating the Supabase CLI and identifying the intended project.
- Current palette to preserve or deliberately revise: light canvas `#f7f9fc`,
  white surfaces, navy text `#0b1b39`, blue action `#1459d4`; dark canvas
  `#0d131b`, dark surface `#151d27`, light text `#e8eef7`, blue action
  `#8cb6ff`; success, warning, and error states use green, amber, and red
  semantic tokens in both themes.
