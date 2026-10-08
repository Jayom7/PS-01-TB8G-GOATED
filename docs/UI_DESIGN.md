# Clearframe UI Direction

## Product identity

Clearframe is a restrained security-oriented enterprise knowledge workspace.
The application surface contains no university, hackathon, judge, or preview
branding. Synthetic records are not presented as connected production data.

## Concept

- [Clearframe Ask workspace](design/workspace-clearframe.png)
- Earlier PS-01 concepts remain in `docs/design/` as historical references;
  they contain branding and sample details that should not be copied.

The Clearframe system uses a light or dark canvas, deep ink type, a restrained
blue accent, cool separators, a slim top bar, a six-destination navigation
rail, and a full-width Ask workspace. Citations are inline; source evidence
opens in a temporary drawer rather than occupying a permanent column. Product
UI, citations, controls, and text are implemented in code rather than shipped
as a screenshot.

## Current implemented surface

- Supabase sign-in form and a server-side authenticated route gate.
- Six direct routes: Dashboard, Ask, Sources, Ingest, Security, and Evaluation.
- The account area at the bottom of the sidebar holds controlled local demo
  role switching, theme selection, and Log out.
- The Ask route shows inline citations and opens authorized source excerpts in
  a responsive evidence drawer.
- Dashboard, Ask, Sources, Ingest, Security, and Evaluation are real API-backed
  views behind the authenticated workspace. Sources supports authorized text
  search and source-type filters; rows show date, type, and available chunk
  count.
- Light/dark colors now resolve through a shared token set in
  `apps/web/src/app/globals.css`. The themes use neutral surfaces, shared text,
  border, accent, focus, status, overlay, and shadow tokens. Routes share a
  full-height sidebar and independently scrolling main column; mobile nav and
  the source drawer have narrow-screen layouts.
- CSS and production build pass in the current pass. Prior browser checks
  covered desktop/tablet/mobile and theme states; they are historical and were
  not repeated because local Supabase is currently inaccessible. See
  `REVIEW_NEEDED.md` for exact current verification boundaries.
- Gemini errors are readable and retryable; quota availability remains
  unverified. Security/Evaluation labels distinguish architecture and local
  smoke measurements from hosted or production proof.

The controlled local demo identity switch uses real seeded Supabase sessions.
