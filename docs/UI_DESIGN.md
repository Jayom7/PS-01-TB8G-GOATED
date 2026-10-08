# UI Design Direction

## Concept references

- [Primary finance workspace](design/workspace-desktop.png)
- [Insufficient-authorized-evidence state](design/workspace-denied.png)
- [Responsive mobile workspace and evidence sheet](design/workspace-mobile.png)

The concepts were generated from the user brief because the Superdesign CLI
preflight remained silent and had to be stopped. They are implementation
references, not proof of functionality. Synthetic sample details in the
concept images must be normalized to one internally consistent demo fixture.

## Design system

- **Canvas:** true white (`#FFFFFF`), cool near-white (`#F7F9FC`) only for
  selected/soft utility surfaces.
- **Text:** deep navy (`#0A1B3A`) for primary, muted blue-gray (`#52627B`) for
  secondary.
- **Accent:** clear medium blue (`#1458D4`) for links, selected navigation,
  citation markers, and primary action.
- **Authorization:** quiet green (`#16834B`) only when a retrieved source has
  passed the real server-side policy check.
- **Borders:** cool pale gray-blue (`#DCE3EE`); avoid heavy shadows.
- **Type:** clean sans serif for controls and body; answer text can use a
  restrained serif only if it remains readable and matches the final concept.
- **Geometry:** slim top bar, 220–260px navigation rail, flexible open chat
  column, 400–450px evidence inspector at desktop widths. Use vertical rules
  and whitespace rather than nested cards.
- **Controls:** compact, high-contrast, keyboard-visible focus. No invented
  metrics, security badges, decorative illustrations, or random gradients.

## Primary components and states

- Navigation rail with real demo identity selector and Chat/Sources/Ingestion/
  Evaluation destinations.
- Central conversation with query, grounded claims, inline source references,
  insufficient-evidence response, and bottom composer.
- Evidence inspector with only authorized sources and exact page/row/region;
  source preview opens from a citation.
- Safe trace shows identity verification, policy application, and selected
  authorized evidence only. It never lists denied sources or hidden counts.
- On mobile, collapse navigation behind a menu and expose evidence as a
  bottom sheet; keep the composer reachable and controls thumb-friendly.

## Copy and data lock

Keep the concept's primary title and source navigation. Build a consistent
synthetic finance fixture before presenting dollar values or dates; the
generated desktop and mobile concepts contain inconsistent sample amounts and
must not be treated as source data. No fabricated evaluation metrics are
allowed. Status text such as “Authorized” may appear only after an actual
server decision.
