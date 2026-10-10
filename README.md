# Clearframe — Secure Knowledge Workspace

Clearframe is the PS-01 knowledge workspace: a Next.js frontend, FastAPI backend, and Supabase Auth/PostgreSQL/pgvector stack. It retrieves authorized evidence from PDFs, scanned images and seven typed business tables. The included NovaCore Industries corpus is fictional.

**Start here to run the complete local demo on your own computer.** Windows users should use **WSL2 with Ubuntu 24.04**; macOS users can use Terminal. The launcher is a Bash script, not a native PowerShell application. You do not need the author's passwords, a hosted Supabase project, or a Render account. You do need your own Gemini API key with access to the configured models and sufficient quota.

## Contents

- [Requirements](#requirements)
- [Windows setup](#windows-1011--wsl2)
- [macOS setup](#macos)
- [Clone and install](#clone-and-install-both-platforms)
- [Configure Gemini](#configure-gemini)
- [First launch and sign in](#first-launch-and-sign-in)
- [Check your installation](#check-that-your-installation-works)
- [Restart, stop and update](#restart-stop-and-update)
- [Troubleshooting](#troubleshooting)
- [Optional checks](#optional-developer-checks)
- [Hosted deployment](#hosted-deployment-is-separate)

## Requirements

| Requirement | Version / purpose |
| --- | --- |
| Git | Clone the repository. |
| Node.js + npm | These steps use Node **24.13.0**, matching the development checkout. Next requires Node >=20.9; dependency managers may impose higher requirements. |
| pnpm | **11.25.0**, declared in `apps/web/package.json`. |
| Python | Use **3.12** for these instructions. The API declares >=3.12,<3.15; optional OCR packages have their own wheel/platform constraints. |
| Docker Desktop | Running with Linux containers; on Windows, enable WSL2 integration. Local Supabase runs in Docker. |
| Internet | For initial packages, Docker images and OCR models, and during Gemini embedding/generation requests. |
| Gemini API key | Server-side only. Embeddings are required to populate the searchable demo; a key alone does not guarantee quota/model access. |

Allow several GB of downloads and storage. As a practical allocation, aim for 16 GB system RAM and 20 GB free space, with several GB available to Docker/WSL. This is a suggested resource budget, not a measured minimum. PaddleOCR can use substantial additional memory during extraction; the configured path uses CPU, not GPU.

## Windows 10/11 — WSL2

Use a Windows version supported by [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) and [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/), with virtualization enabled.

### 1. Install Ubuntu and Docker

In **PowerShell as Administrator**, run:

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
wsl --set-default-version 2
```

Restart Windows if prompted. Open **Ubuntu 24.04** from the Start menu and create its Linux username/password. If Ubuntu was already installed, keep it and check its version with `cat /etc/os-release`; the package commands below target Ubuntu 24.04.

In PowerShell, confirm Ubuntu is using version 2:

```powershell
wsl --list --verbose
```

If necessary, convert the existing distribution with `wsl --set-version Ubuntu-24.04 2`.

Install and start Docker Desktop for Windows. In **Settings → General**, select the WSL2 engine; in **Settings → Resources → WSL Integration**, enable **Ubuntu-24.04** and apply the change. Use Linux containers. Follow [Docker's WSL2 instructions](https://docs.docker.com/desktop/features/wsl/) if integration is absent. Do not install a second Docker engine inside Ubuntu alongside Docker Desktop.

### 2. Install Linux prerequisites

**Run all remaining setup and launch commands in Ubuntu**, not PowerShell, CMD, Git Bash or a Windows Python environment:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates build-essential python3.12 python3.12-venv python3.12-dev libgl1 libglib2.0-0t64 libgomp1
python3.12 --version
docker info
```

`docker info` must succeed before continuing. Install Node inside Ubuntu using the shared instructions below; do not reuse Windows-installed Node/Python/dependencies inside WSL.

Keep the clone in your **Linux home directory** (`~/clearframe`), not `/mnt/c/...`, OneDrive or a network share. Open `http://localhost:3000/login` in your normal Windows browser after launch. WSL normally forwards Linux web apps to Windows localhost; see [Microsoft's networking guide](https://learn.microsoft.com/en-us/windows/wsl/networking) if that fails.

## macOS

### 1. Install prerequisites

Install Apple's Command Line Tools if missing:

```bash
xcode-select --install
```

Wait for the installer to finish. If the tools are already installed, keep them.

Install [Homebrew](https://docs.brew.sh/Installation) if necessary, including the `brew shellenv` step printed by its installer. Then:

```bash
brew install python@3.12
export PATH="$(brew --prefix python@3.12)/bin:$PATH"
python3.12 --version
git --version
```

Install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/) for your CPU architecture (Apple Silicon or Intel), start it and wait for the engine:

```bash
docker info
```

If Terminal cannot find Docker Desktop's CLI:

```bash
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
docker info
```

The launcher already includes that Docker Desktop path. An existing Docker-compatible runtime is also usable if its CLI is on `PATH`.

## Clone and install (both platforms)

### 1. Install Node and the pinned pnpm

These commands work in Ubuntu/WSL Bash and macOS Terminal. If you already use [nvm](https://github.com/nvm-sh/nvm), skip its installer and load your existing installation. Otherwise, this official installer downloads and executes nvm's installation script:

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh | bash
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
nvm install 24.13.0
nvm use 24.13.0
npm install -g pnpm@11.25.0
node --version
npm --version
pnpm --version
```

The final pnpm version should be `11.25.0`. See [pnpm installation](https://pnpm.io/installation) if your existing setup uses Corepack instead; keep the declared version. Avoid `sudo npm install` with nvm-managed Node. On a new terminal, load nvm if needed and run `nvm use 24.13.0`.

### 2. Clone into a new directory

```bash
cd ~
git clone https://github.com/Jayom7/PS-01-TB8G-GOATED.git clearframe
cd clearframe
```

If GitHub asks you to authenticate, use an account with repository access. If this clone already exists, use it rather than cloning over it. All subsequent project commands assume you are in this repository root.

### 3. Install dependencies

```bash
npm ci
pnpm --dir apps/web install --frozen-lockfile
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e 'apps/api[dev,ingestion]'
```

Root `npm ci` installs the repository-local Supabase CLI. The separate pnpm command installs the frontend from its lockfile. The API's `ingestion` extra installs PDF parsing, PaddleOCR and ONNX Runtime; `dev` installs development checks. Python dependency ranges are declared in `apps/api/pyproject.toml`, not a fully pinned Python lockfile.

Verify the installed entry points:

```bash
node_modules/.bin/supabase --version
apps/web/node_modules/.bin/next --version
.venv/bin/python -m pip check
.venv/bin/python -c 'import ps01_api, pymupdf, paddleocr, onnxruntime; print("API and document dependencies import successfully")'
```

The first OCR extraction initializes/downloads English models. Imports alone do not prove those models can download or process documents. See the existing native Tesseract alternative under [Troubleshooting](#troubleshooting).

## Configure Gemini

Copy the example **only if you do not already have a root `.env`**:

```bash
test -f .env || cp .env.example .env
chmod 600 .env
```

Open `.env` locally (`nano .env` in Ubuntu, or `open -e .env` on macOS). Set `GEMINI_API_KEY` to your own key from [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key). Keep it private; do not paste it into screenshots, tickets, commits or browser `NEXT_PUBLIC_` variables.

Keep these checked-in defaults for the normal local demo:

| Setting | Local default |
| --- | --- |
| `GEMINI_CHAT_MODEL` | `gemini-3.8-flash` |
| `GEMINI_FALLBACK_CHAT_MODEL` | `gemini-3.7-flash` |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-2` |
| `EMBEDDING_DIMENSIONS` | `1536` |
| `WEB_ORIGIN` | `http://localhost:3000` |
| `INGESTION_ENABLED` / `ORIGINAL_STORAGE` | `false` / `local` (the local-demo gate enables authorized local ingestion) |
| `OCR_ENGINE` | `paddleocr` |

Your Google project must actually expose the configured models. Availability and free-tier quotas vary. **Do not substitute another embedding model or dimension against the existing index.** If a model is unavailable to your account, resolve its access/configuration before seeding; the README cannot grant access or turn a fallback into a genuine model answer.

Leave `GEMINI_PROJECT_ID`, `GEMINI_SECONDARY_PROJECT_ID` and `GEMINI_SECONDARY_API_KEY` blank unless you deliberately provision an independent second project. Optional fallback requires both actual project IDs to be known and different; another key in the same project is not independent quota.

For the **local launcher**, Supabase URL/keys in root `.env.example` can remain placeholders: the API launcher and seed script obtain local keys from the CLI and refuse remote URLs. Do not copy hosted keys. The launcher generates ignored `apps/web/.env.local` with the local public key and same-origin API proxy settings; it replaces existing contents of that file. Keep separate hosted frontend configuration outside this local checkout.

## First launch and sign in

Ensure Docker is running. From the repository root:

```bash
./scripts/dev --seed
```

Leave this terminal open. First launch can take several minutes while images and OCR models download. The launcher:

1. Starts local Supabase and applies the repository's additive local migrations.
2. Writes the local frontend environment configuration.
3. Seeds the included manifest, five local Auth accounts, roles, typed records, document permissions and Gemini embeddings.
4. Starts FastAPI on `127.0.0.1:8000` and Next.js on `127.0.0.1:3000`.

**Wait for the successful `Seeded ...` message and Next.js readiness.** Credentials may be written before embeddings finish; their presence does not mean seeding succeeded. A seed failure exits the launcher before starting API/web; follow failure-specific recovery below.

Open **[http://localhost:3000/login](http://localhost:3000/login)**. Privately open `.local-demo-credentials.json` in your editor (`nano .local-demo-credentials.json`, or `open -e .local-demo-credentials.json` on macOS). Use the `email` and `password` under **`CEO`**. Passwords are generated on your machine; there is no shared default password or required public signup.

Keep that ignored file: it is used by the local role-context broker and has owner-only permissions. The five seeded roles are CEO, Finance Manager, HR Manager, Sales Manager and Engineer. Signing in as CEO enables local demo access-context switching and CEO ingestion; other roles have restricted evidence access.

| Local service | URL / port |
| --- | --- |
| Clearframe | `http://localhost:3000/login` |
| FastAPI health / interactive API docs | `http://127.0.0.1:8000/health` / `http://127.0.0.1:8000/docs` |
| Supabase API/Auth | `http://127.0.0.1:54321` |
| PostgreSQL | `127.0.0.1:54322` |
| Supabase Studio | `http://127.0.0.1:54323` |
| Local test email inbox | `http://127.0.0.1:54324` |

Other Supabase services also reserve ports in `supabase/config.toml`. Use `localhost:3000` consistently for browser login/recovery, as configured by the app origin. The email inbox captures local password-reset messages; it does not send real email. Google OAuth needs separate operator configuration and is not required for the email/password demo.

## Check that your installation works

In a **second terminal**, enter the same checkout (e.g. `cd ~/clearframe`) and run:

```bash
curl --fail http://127.0.0.1:8000/health
.venv/bin/python apps/api/scripts/verify_services.py
```

Readiness checks API/web reachability, real local CEO login, visible documents/chunks/history, and representation of all seven typed tables. It performs no generation request and prints no credentials. Exit code 2 means readiness is blocked; investigate before presenting the demo.

Then check in the browser:

1. Sign in as the generated CEO; inspect Overview and Sources for seeded data.
2. Submit once in Ask: **“What is the total amount on Acme invoice ACM-INV-2048?”** Inspect the answer label and citations/source preview. The canonical demo amount is **USD 48,000**. A labelled verified-evidence fallback is useful evidence, but **does not verify a genuine LLM response**.
3. Switch to a restricted access context and confirm the workspace reflects that role. Return to CEO to use Ingest.
4. To verify uploads, ingest a small PDF/PNG/JPEG or supported structured record through the form, inspect its published source and ask about it. Startup alone does not verify upload/OCR/provider behavior.
5. Toggle light/dark mode and reload to check persistence. History rechecks current authorization when reopened.

These checks are for **your installation**, not a claim that every device has been tested. The original macOS workspace has prior local browser/runtime verification; these instructions have not been executed end-to-end on a clean Windows/WSL device. Recent provider requests have encountered timeouts/503 responses, so dependable live generation remains provider-dependent.

## Restart, stop and update

After a successful initial seed, normally launch with:

```bash
cd ~/clearframe
./scripts/dev
```

`Ctrl+C` stops API/web processes started by the launcher. Supabase and its Docker data remain running. To stop Supabase while retaining local data:

```bash
node_modules/.bin/supabase stop
```

Do not use `--no-backup` or `supabase db reset` to troubleshoot an existing workspace. Do not delete `.local-demo-credentials.json` or Docker volumes: they are needed to reuse accounts/data.

To update a clean checkout safely, stop the app and then:

```bash
git status --short
git pull --ff-only
npm ci
pnpm --dir apps/web install --frozen-lockfile
.venv/bin/python -m pip install -e 'apps/api[dev,ingestion]'
./scripts/dev
```

Preserve local changes first if Git reports them; do not reset them to make a pull succeed. Normal startup applies new local migrations but does not automatically reseed. **`--seed` is not an everyday restart command:** it can refresh synthetic sources, role assignments and account passwords from the credentials file, and prune superseded tagged demo sources. Use it for first setup or a diagnosed incomplete seed, not against unrelated data.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `docker info` fails / engine unavailable | Start Docker Desktop. On Windows enable Ubuntu WSL integration and Linux containers, confirm WSL version 2. On Mac check Docker's CLI path. |
| Missing dependencies / `.venv/bin/python` absent | Install inside the same OS environment as the launcher. A Windows `.venv/Scripts` environment cannot replace WSL's `.venv/bin`. |
| `python3.12` not found | On WSL use Ubuntu 24.04 and install `python3.12-venv`; on Mac restore the Homebrew Python path. Do not use older system Python. |
| `pnpm` / `nvm` not found in a new terminal | Load `. "$HOME/.nvm/nvm.sh"`, select Node 24.13.0 and install pnpm 11.25.0 under that Node. On WSL, `command -v node` must not resolve to Windows under `/mnt/c`. |
| `/usr/bin/env: 'bash\r'` / permission denied | Clone with Linux Git in WSL, not Windows Git with CRLF conversion. Scripts are tracked executable. For a ZIP checkout, `chmod +x scripts/dev scripts/verify_demo` restores permissions. |
| Port already in use | Stop the conflicting local process/project. Launchers hardcode 3000/8000; changing only `API_BASE_URL` does not change their bindings. Do not randomly change Auth/proxy settings. |
| Slow first launch / failed download | Check internet/proxy access to package registries, Docker images and OCR model hosts. Allow downloads to finish; inspect the actual error before retrying. |
| OOM / killed OCR or containers | Increase Docker/WSL memory allocation, close heavy apps, or use the existing lighter Tesseract path below. |
| PaddleOCR import/model error | Confirm the `ingestion` extra, Python/platform wheel support and Ubuntu libraries above. Models need reachable download hosts. Consider the Tesseract option. |
| Seed fails with Gemini 401/403/404 | Check the private key, project/API access and availability of the configured embedding model. Do not regenerate credentials or reset the database. |
| Seed fails with 429/503/timeout | Respect provider cooldown/quota. After resolving it, rerun `./scripts/dev --seed` to finish the incomplete local seed. This reuses saved credentials/reconciles data, but can update existing tagged demo records. Repeated immediate retries will not fix availability. |
| Login fails / Sources empty after seed error | Credentials can exist before a complete seed. Confirm the successful seed message, check readiness, and finish the diagnosed failure. Use this clone's credentials, not another machine's. |
| Ask shows verified evidence / unavailable answer | Inspect the honest label. Generation is bounded (interactive cap 12 seconds); fallback is not model success. Embeddings may still require the provider. Restart API after `.env` edits and avoid repeated quota-consuming probes. |
| Upload controls restricted | Sign in as local CEO and select CEO context. Other roles cannot ingest. Check seed/credentials; keep `ORIGINAL_STORAGE=local`. |
| Recovery email / Google unavailable | Local email is captured at port 54324. Google needs separate Supabase OAuth setup; use seeded email/password. |
| Windows browser cannot open app | Try `curl --fail http://localhost:3000/login` inside Ubuntu. If successful, diagnose Windows localhost forwarding/firewall/VPN using Microsoft's WSL networking guide; do not expose keys or disable app authentication. |

### Existing lighter OCR option: native Tesseract

Optional: the normal installation keeps PaddleOCR. The existing Tesseract adapter supports English OCR with bounded line coordinates. Install its native executable and English language data:

```bash
# Ubuntu / WSL
sudo apt install -y tesseract-ocr tesseract-ocr-eng
```

```bash
# macOS
brew install tesseract
```

Check `tesseract --version` and `tesseract --list-langs` (`eng` must be listed), set `OCR_ENGINE=tesseract` in root `.env`, and restart. Keep PDF/NumPy dependencies installed. For a new environment choosing Tesseract from the start, `.venv/bin/python -m pip install -e 'apps/api[dev,hosted-ingestion]'` installs those without PaddleOCR; despite the extra's name, this does **not** enable hosted mode. Keep `ORIGINAL_STORAGE=local`. Run the same seed/readiness/upload checks; OCR extraction can differ between engines.

For that alternative, use `apps/api[dev,hosted-ingestion]` in the install/update commands and replace the PaddleOCR import check with:

```bash
.venv/bin/python -c 'import ps01_api, pymupdf, numpy; print("API and native OCR dependencies import successfully")'
tesseract --version
tesseract --list-langs
```

## Optional developer checks

From the repository root:

```bash
.venv/bin/python -m pytest apps/api/tests -q
.venv/bin/ruff check apps/api/src apps/api/scripts apps/api/tests
node --experimental-strip-types --test apps/web/tests/session.test.mjs
pnpm --dir apps/web lint
apps/web/node_modules/.bin/tsc --noEmit --incremental false -p apps/web/tsconfig.json
pnpm --dir apps/web build
```

The build needs any external font downloads used by Next.js. Unit tests/builds do not establish live provider/database success. For the fuller **local**, seeded integration check while the app runs:

```bash
./scripts/verify_demo
```

This checks readiness, pgTAP and five-role authorization/citation workflows, and can make real provider requests. It is not needed on every restart. `--skip-generation` deliberately leaves verification incomplete. Reports remain under ignored `data/local/`; failures never become successful metrics.

## Hosted deployment is separate

`render.yaml`, the API Dockerfile and seven Supabase migrations are included for deployment preparation. **They are not a verified one-click hosted demo.** The local launcher/seed must not be used against hosted Supabase. Hosted setup requires separate project provisioning, migrations, private original storage, real Auth users with organization/role assignments, API/frontend environment settings, allowed web origins/Auth redirects, and appropriate email/OAuth setup. Local accounts, Docker data and generated passwords do not transfer automatically. The demo role broker and synthetic Evaluation runner remain local-only.

For another person's laptop, use the local instructions; no hosted provisioning is required. Do not share `.env`, `.local-demo-credentials.json`, `apps/web/.env.local` or private uploads. All are ignored by Git.

## Security and answer boundaries

- Normal reads use verified user/context JWTs and retrieval-time RLS; demo contexts are actor/organization/role bound and freshly checked.
- The provider selects evidence IDs within a server-owned canonical boundary. Unknown IDs/model-supplied quotes are rejected; citations come from authorized records. This does not prove general semantic entailment.
- History reconstructs evidence under current authorization. Previews and source deletion preserve access checks and private-storage cleanup.
- CEO ingestion is privileged; service keys stay server-side and are not used for ordinary retrieval.
- Evidence fallback and recorded/synthetic evaluation are labelled honestly. Historical Gemini success does not prove current provider availability.

The [acceptance checklist](docs/MASTER_ACCEPTANCE_CHECKLIST.md), [submission matrix](docs/SUBMISSION_MATRIX.md), [demo runbook](docs/DEMO_RUNBOOK.md), [final report](docs/FINAL_BUILD_REPORT.md) and [review boundaries](docs/REVIEW_NEEDED.md) retain historical evidence/limitations. Some reflect earlier milestones; use this README and current scripts for installation, rather than old test counts or an old corpus snapshot.
