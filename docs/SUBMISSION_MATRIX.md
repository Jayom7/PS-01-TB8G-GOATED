# PS-01 submission matrix — final local pass

[MASTER_ACCEPTANCE_CHECKLIST](MASTER_ACCEPTANCE_CHECKLIST.md) maps all 16 PS-01 items, phases 0–9 and 12 demo steps. All independently achievable implementation is complete. Provider consistency and external/handoff checks remain explicit.

| Requirement | Actual evidence | Status |
|---|---|---|
| Mixed ingestion / unified index | Fresh browser PDF, real OCR and typed invoice; 29 integration checks; pgvector1536 and provenance | PASS |
| Retrieval authorization | 55 SQL / 51 live role checks; exact-ID lookup, HR and cross-org denial | PASS locally |
| Working real answers / exact citations | Browser 3.8 OCR/contract; normal 3.8 Finance and 3.7 fresh fallback; inspected canonical previews | PASS; intermittent provider failures retained |
| Combined modalities / safe context | Real 3.7 three-modal API integration, three previews, outbound IDs matched Finance RLS. Primary deadline deliberately interrupted; no external mocks | PASS within that stated integration scope |
| Grounding / injection guards | Deterministic forgeries/conflicts/poison; actual literal poison quoted untrusted; no general entailment guarantee | PASS bounded checks |
| Conversations / source lifecycle | Generated reload/API restart; current canonical rebuild; 22 original + 30 resume deletion/replay/cleanup checks | PASS |
| Product UI | 48 route/theme/size combinations + 8 populated Ask states; real navigation/modal/control flows | PASS |
| Auth / recovery | Real email login/logout/recovery email/callback/form; no automatic roles | PASS; Google completion BLOCKED, password update NOT RUN |
| Evaluation | Current v2: hit@12 1.0, MRR 0.80, 0 forbidden, 59/59 locations, 655.2 ms mean; six queries plus direct HR | PASS synthetic retrieval |

103 backend tests, 55 SQL assertions and 5 node tests pass. Ruff/format, frontend lint/types/build and diff checks pass. Five additive local migrations; original corpus retained at 19 sources / 45 chunks / 7 typed rows. Hosted Supabase remains untouched.

Unfinished: dependable normal Gemini generation (latest full verifier 51 pass / 1 provider blocked; fresh OCR-specific generated claim incomplete), actual Google completion, password change/success and timed recovery expiry. Deliberate wall-clock browser expiry and automated accessibility/reduced-motion emulation were not run. No general semantic entailment or atomic external-call revocation guarantee is claimed.
