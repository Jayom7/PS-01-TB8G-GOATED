from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "node_modules" / ".bin" / "supabase"
DOCKER_BIN = "/Applications/Docker.app/Contents/Resources/bin"
WEB_ENV = ROOT / "apps" / "web" / ".env.local"


def main() -> None:
    environment = os.environ.copy()
    environment["PATH"] = f"{DOCKER_BIN}:{environment.get('PATH', '')}"
    result = subprocess.run(
        [str(CLI), "status", "-o", "env"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Local Supabase is not running.")
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator:
            parts = shlex.split(value)
            if parts:
                values[name] = parts[0]
    api_url = values["API_URL"]
    if urlparse(api_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Refusing to configure the web app for a non-local Supabase URL.")
    WEB_ENV.write_text(
        "NEXT_PUBLIC_SUPABASE_URL="
        + api_url
        + "\nNEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY="
        + values["PUBLISHABLE_KEY"]
        + "\nNEXT_PUBLIC_API_BASE_URL=\nAPI_INTERNAL_URL=http://127.0.0.1:8000\n"
    )
    print("Configured ignored apps/web/.env.local for local Supabase and FastAPI.")


if __name__ == "__main__":
    main()
