from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
API_ROOT = ROOT / "apps" / "api"
CLI = ROOT / "node_modules" / ".bin" / "supabase"
DOCKER_BIN = "/Applications/Docker.app/Contents/Resources/bin"


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
        raise RuntimeError("Local Supabase is not running; start it with `supabase start`.")
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator:
            parts = shlex.split(value)
            if parts:
                values[name] = parts[0]
    url = values["API_URL"]
    if urlparse(url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Refusing to launch the local API against a remote Supabase URL.")
    environment["SUPABASE_URL"] = url
    environment["SUPABASE_PUBLISHABLE_KEY"] = values["PUBLISHABLE_KEY"]
    environment.pop("SUPABASE_SECRET_KEY", None)
    os.execvpe(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--app-dir",
            "src",
            "ps01_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        environment,
    )


if __name__ == "__main__":
    main()
