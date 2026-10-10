# Clearframe web

Next.js frontend for the Clearframe knowledge workspace. It requires Supabase
Auth, a migrated/seeded database and the FastAPI service; starting `next dev`
alone does not create a working demo.

For complete **Windows/WSL2 and macOS setup**, follow the
[root README](../../README.md). All commands below run from the repository root.

After installing prerequisites/dependencies and configuring your private Gemini
key, start the complete local stack once with:

```bash
./scripts/dev --seed
```

After successful seeding, use `./scripts/dev` for later launches. Open
`http://localhost:3000/login` and sign in using the CEO entry in the ignored
`.local-demo-credentials.json` generated on your own computer.

The launcher writes ignored `apps/web/.env.local` with the local Supabase public
settings and a same-origin API proxy to `127.0.0.1:8000`. Do not put Gemini or
Supabase service keys in frontend variables. The launcher replaces this local
environment file; keep hosted configuration in a separate checkout/environment.

## Frontend checks

```bash
pnpm --dir apps/web lint
apps/web/node_modules/.bin/tsc --noEmit --incremental false -p apps/web/tsconfig.json
pnpm --dir apps/web build
```

The frontend uses pnpm 11.25.0 and its checked-in lockfile. A successful build
alone does not verify live Auth, RLS, OCR, ingestion or Gemini answers. Hosted
provisioning and deployment are separate from the local startup flow.
