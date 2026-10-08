# Clearframe UI Direction and Visual Audit

A quiet enterprise knowledge workspace: neutral light canvas, layered graphite dark surfaces, one restrained green accent, shared type/spacing/border/focus tokens, and six grouped destinations. App shell, source tables, forms, conversations, and inspectors share the same system. No decorative 3D, gradients, new UI framework, or copied product assets were introduced.

Overview favors readable live counts and recent activity. Ask prioritizes the conversation, inline citations, composer, and optional within-page history. Evidence and detailed timings live in temporary drawers. Structured fields use business labels and formatted currency; originals preserve PDF page/OCR region. Sources uses dense searchable/filterable/sortable rows; mobile source actions remain visible. Ingest separates coordinated file and typed-record workflows with validation and truthful atomic indexing status. Security explains the boundary; Evaluation separates recorded synthetic observations from live runs and keeps failure states visible.

Native modal drawers provide close button, Escape, outside click, focus trap/return, background inertness, scroll lock, internal scrolling, and full-width mobile layout. Mobile navigation traps/restores focus and makes background content inert. Closed mobile navigation is not keyboard reachable. Account selection/theme, outside click, and Escape close the menu. Reduced motion uses existing global preference handling.

## Fresh visual boundary

Actual public login was inspected. All workspace routes were inspected on a separate explicitly labeled fixture server because live Supabase is unavailable. Desktop light/dark, mobile light/dark, and tablet layout checks found no page-level horizontal overflow; Evaluation tables retain a bounded horizontal scroller. All five role controls were exercised as UI controls, not live Auth/RLS verification. Conversation replay/new, source filters, record/PDF/image previews, OCR highlight, trace, drawers, and mobile navigation were inspected. Recorded Evaluation table data came from a historical local report and stayed labeled recorded.

Fixed findings: drawer focus failed to return; Tab could escape the only drawer control; record title/location duplicated; amount fields showed raw minor units; late requests could reopen or contaminate a closed inspector; mobile source action was offscreen; refresh errors disappeared behind previous data; ingestion repeated its error message. Source sorting and partial-validation copy were added during the final bounded repair pass.

[Desktop Ask fixture](design/final-desktop-ask-fixture.jpg) and [mobile evidence fixture](design/final-mobile-evidence-fixture.jpg) are layout evidence only. Browser tests did not validate live role switching, provider answers, persistent history, upload completion, or database policy execution.
