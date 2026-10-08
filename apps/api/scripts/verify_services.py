"""Read-only local readiness checks. Credentials never appear in output."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from seed_local_demo import local_supabase_environment

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    try:
        local = local_supabase_environment()
        credentials = json.loads((ROOT / ".local-demo-credentials.json").read_text())
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            client.get("http://127.0.0.1:8000/health").raise_for_status()
            print("VERIFIED: API reachable")
            client.get("http://localhost:3000/login").raise_for_status()
            print("VERIFIED: Web login reachable")
            base = local["API_URL"].rstrip("/")
            login = client.post(
                f"{base}/auth/v1/token",
                params={"grant_type": "password"},
                headers={"apikey": local["PUBLISHABLE_KEY"]},
                json=credentials["CEO"],
            )
            login.raise_for_status()
            headers = {
                "apikey": local["PUBLISHABLE_KEY"],
                "Authorization": f"Bearer {login.json()['access_token']}",
            }
            print("VERIFIED: Local CEO authentication")
            for table in ("documents", "knowledge_chunks", "structured_records", "query_history"):
                response = client.get(
                    f"{base}/rest/v1/{table}",
                    headers=headers,
                    params={"select": "*", "limit": "1000"},
                )
                response.raise_for_status()
                if table != "query_history" and not response.json():
                    raise RuntimeError("Seed rows missing")
                print(f"VERIFIED: {table} accessible ({len(response.json())} visible rows)")
            records = client.get(f"{base}/rest/v1/structured_records", headers=headers).json()
            expected = {
                "customers",
                "projects",
                "employees",
                "invoices",
                "payments",
                "purchase_orders",
                "opportunities",
            }
            if not expected.issubset({row["table_name"] for row in records}):
                raise RuntimeError("Incomplete typed-row seed")
            print("VERIFIED: All seven relational record tables represented")
        return 0
    except (httpx.HTTPError, OSError, ValueError, RuntimeError, KeyError) as exc:
        print(
            f"BLOCKED: Local readiness dependency ({type(exc).__name__}); no secret details logged"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
