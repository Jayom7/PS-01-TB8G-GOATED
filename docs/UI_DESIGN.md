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
- A coherent light/dark token set, focus states, mobile navigation, table
  overflow, and reduced-motion behavior are implemented. Production browser
  checks covered 320px mobile and 1440px desktop; tablet and broader device
  coverage remain unverified.
- The interface reports live data and safe request failures. Gemini generation
  was intermittent during the latest browser run; see `REVIEW_NEEDED.md`.

The controlled local demo identity switch uses real seeded Supabase sessions.
