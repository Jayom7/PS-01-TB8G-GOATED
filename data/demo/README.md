# NovaCore synthetic corpus

This directory contains generated, fictional demo content only. The retrieval
manifest indexes 19 sources: eight PDFs, four OCR images and seven structured
sources. It includes contracts, policies, a prompt-injection test, invoice and
receipt scans, an HR acknowledgement, a purchase order and typed business
records. The invoice is
USD 48,000, dated 2026-09-01, due 2026-10-01, and unpaid as of 2026-10-08.

The checked-in manifest and all referenced files are included in the clone.
Use the [root README](../../README.md) to install and run on Windows/WSL2 or
macOS; normal setup does not require regenerating the corpus.

For development only, the generator is:

```sh
.venv/bin/python apps/api/scripts/generate_demo_corpus.py
```

Regeneration changes synthetic fixture files and may alter the demo snapshot;
do not use it as a routine startup or troubleshooting step.

`manifest.json` describes role access. It does not itself create users or
database records. To seed the local Supabase stack and generate local-only
demo credentials, run:

```sh
.venv/bin/python apps/api/scripts/seed_local_demo.py
.venv/bin/python apps/api/scripts/evaluate_local_retrieval.py
.venv/bin/python apps/api/scripts/run_local_demo.py
```

The seed script reads keys from `supabase status`, refuses non-loopback URLs,
and writes credentials to the git-ignored `.local-demo-credentials.json` with
owner-only permissions. It creates five local Auth users, role assignments,
source ACLs, extracted chunks, and Gemini embeddings. On reseed, it also removes
superseded documents explicitly tagged as synthetic local demo sources within
the local demo organization; document deletion cascades to their chunks and
grants. It does not modify the hosted Supabase project. The final demo script
needs the Gemini generation endpoint; temporary provider failures are reported
as incomplete demo runs.
