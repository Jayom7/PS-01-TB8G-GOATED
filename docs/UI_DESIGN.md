# Clearframe real UI acceptance audit — 2026-10-09

The existing six-route enterprise workspace retains neutral light surfaces, graphite dark surfaces, restrained green accent, shared type/spacing/focus tokens and grouped navigation. Overview, Ask, Sources, Ingest, Security and Evaluation remain the six destinations. This pass repairs real defects while preserving authorization and citation behavior.

## Actual audit

Inspected the authenticated running app against local Supabase/API at 1440×900, 820×900 and 390×844, all six routes in light and dark modes. These were real rendered pages, not fixture screenshots. CEO-visible counts were 19 sources / 45 chunks / 7 records. Switching actual API contexts showed Finance 13 sources, HR 3, Sales 3, Engineer 5 and CEO 19, preserving the signed-in CEO identity.

Inspected alignment, hierarchy, density, spacing, table actions, field layout, header/account identity, responsive navigation, scroll regions and source inspector composition. No page-level horizontal overflow was observed at the checked sizes. Evaluation deliberately retains an internal table scroller. Ask's mobile example controls are reachable and fill the composer; New clears the draft without a provider call.

Checked source search/type filters, alphabetical sorting and empty results. Actual contract preview shows its canonical page and Net 30 excerpt; invoice fields show persisted `invoices / ACM-INV-2048`, US$48,000, unpaid and dated snapshot; OCR original/selected region fit the mobile drawer. Drawer X, Escape, outside click, focus trapping/return; mobile navigation X, Escape, exposed backdrop closing and focus return; account outside/Escape/theme controls; logout/CEO login; empty history and draft reset were exercised. Invalid JSON shows a clear validation message before indexing.

## Concrete repairs

- Loaded Sources/Security/Evaluation with current workspace context, eliminating rows with a stuck Loading account; guarded late prior-role errors and cleared stale errors on current success.
- Replaced a blank native PDF embed with a protected bounded PNG of the exact PDF page using existing PyMuPDF; original bytes and RLS remain intact.
- Kept tablet source actions inline by moving the compact layout breakpoint to 1000px; toolbar search wraps and actions stay visible.
- Improved mobile target sizes and gave Overview identity its own row.
- Initial Evaluation loading no longer falsely says no evaluation exists; invalid structured JSON gives quoted-key/comma guidance.

## Evidence and limits

[Live desktop overview](design/live-desktop-overview-light.png), [live protected PDF page](design/live-desktop-pdf-dark.png), [live mobile OCR original](design/live-mobile-ocr-dark.png). These images show real sources; they do not demonstrate successful generated answers. Older `final-*-fixture.jpg` images describe an earlier isolated layout pass.

No unresolved placement/overflow defect was observed after the bounded repair pass at these sizes. This is not a claim that every possible viewport/state is flawless. Gemini quota prevented populated live answer, inline generated citation, retrieval trace and stored-history replay audit. Browser successful upload completion, automated WCAG/contrast certification and reduced-motion emulation were not checked. A transient API connection error was recoverable with Retry; its cause was not established.

## Skills and references

Used installed [Impeccable](https://github.com/pbakaus/impeccable) audit/craft instructions. Its context-engine command was unavailable, so context loading did not run; existing project context was read directly. Installed Taste instructions were read; the skill excludes dense enterprise app UI, so its applicable visual-consistency guidance was used without imposing a landing-page redesign. No unavailable Superdesign tool is claimed.

Browser research inspected the [Awwwards Tipalti nominee](https://www.awwwards.com/sites/tipalti) and [Carbon enterprise table guidance](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines). Tipalti was a nominee; this pass did not verify a winning-site status. References informed spacing, quiet hierarchy and visible row actions; no branding, assets or exact layouts were copied.
