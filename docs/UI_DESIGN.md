# Clearframe UI Direction

## Product identity

Clearframe is a restrained security-oriented enterprise knowledge workspace.
The application surface contains no university, hackathon, judge, or preview
branding. Synthetic records are not presented as connected production data.

## Concept

- [Clearframe Ask workspace](design/workspace-clearframe.png)
- Earlier PS-01 concepts remain in `docs/design/` as historical references;
  they contain branding and sample details that should not be copied.

The Clearframe concept sets a white canvas, deep navy type, one blue accent,
pale cool-gray separators, a slim top bar, a left navigation rail, an open
question workspace, and a right evidence inspector. Product UI, citations,
controls, and text are implemented in code rather than shipped as a screenshot.

## Current implemented surface

- Supabase sign-in form and a server-side authenticated route gate.
- Six workspace destinations: Overview, Ask, Knowledge, Ingestion, Security,
  and Evaluation.
- Live query and source lookup controls are connected to the FastAPI contract.
- Empty/setup states identify database, ingestion, policy-validation, and
  evaluation work that is not yet connected.

The demo identity switch remains absent until it can switch to actual seeded
Supabase sessions. A client-side role selector would not establish identity or
authorization.
