# Demo Plan

Clearframe demonstrates one authenticated knowledge workspace spanning PDF,
OCR-image, and structured records, with retrieval constrained by role grants.
Use only synthetic seeded records.

## Current readiness

Repository implementation exists, but this checkout cannot currently start
local Supabase because the Docker socket returns permission denied and the
repo-local CLI executable is missing. Gemini previously returned 429. Restore
both local runtime and provider access before presenting a live answer; never
replace it with a scripted or mock answer. If quota is still exhausted, present
the actual insufficient/unavailable state and identify the historical live
answer as a prior result, not a current demo.

## Runtime sequence

Follow the exact commands in `README.md`. Login with the local seeded CEO demo
identity; the local generated credentials are in the ignored owner-readable
`.local-demo-credentials.json`. Keep the authenticated identity visible while
switching the active demo context from the profile menu. Use only the five
existing roles.

## Suggested data and checks

- Allowed query: “What amount is shown on Acme's scanned invoice?” (Finance or
  CEO); open the citation and show the OCR excerpt and image region.
- Denied query: same question as HR; show insufficient authorized evidence.
- Optional cross-modal query: “Is Acme overdue and what payment terms does its
  contract specify?” (only when a successful live answer has been checked).
- Security: show identity/context, effective scope, local/historical test
  boundaries, and the exact authorized retrieval flow. Unauthorized evidence
  is not independently counted by the current trace.
- Evaluation: describe the six-case historical local synthetic run (Recall@12
  1.0, MRR 0.775, zero measured authorization violations, 39 provenance
  checks) as a smoke test only. Re-run on the current local runtime before
  calling the numbers current.
- Ingestion: explain PDF text/scanned OCR, image OCR, and structured row paths;
  show an indexed source only if local database state is available.

See `DEMO_SCRIPT.md` and `SCREEN_RECORDING_SCRIPT.md` for exact flow. Hosted
Supabase security and production readiness are not demo claims.
