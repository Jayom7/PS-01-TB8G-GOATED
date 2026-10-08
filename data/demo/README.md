# NovaCore synthetic corpus

This directory contains generated, fictional demo content only. It includes a
selectable-text invoice and contract PDF, a rasterized invoice scan, a
prompt-injection test PDF, and structured finance, HR, sales, and engineering
records. The invoice is USD 48,000, dated 2026-09-01, due 2026-10-01, and
unpaid as of 2026-10-08.

Regenerate the corpus with:

```sh
.venv/bin/python apps/api/scripts/generate_demo_corpus.py
```

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
source ACLs, extracted chunks, and Gemini embeddings. It does not modify the
hosted Supabase project. The final demo script needs the Gemini generation
endpoint; temporary provider failures are reported as incomplete demo runs.
