# PS-01 API

FastAPI service for the authenticated query and ingestion paths. Supabase's end-user JWT must be
forwarded to PostgREST so PostgreSQL RLS evaluates the caller. Never replace that token with the
service-role key on a user query.

## Local setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn --app-dir src ps01_api.main:app --reload
```

The service exposes `GET /health`. Query and ingestion endpoints are not available until their
database and provider integrations are implemented.
