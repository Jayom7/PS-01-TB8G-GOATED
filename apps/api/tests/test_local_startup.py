from __future__ import annotations

import runpy
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_local_api.py"
START = runpy.run_path(str(SCRIPT))["main"]


def test_local_launcher_uses_absolute_app_path_and_keeps_admin_key_server_side():
    status = CompletedProcess(
        [],
        0,
        stdout=(
            'API_URL="http://127.0.0.1:54321"\n'
            'PUBLISHABLE_KEY="test-public"\nSERVICE_ROLE_KEY="test-local-admin"\n'
        ),
    )
    with patch("subprocess.run", return_value=status), patch("os.execvpe") as launch:
        START()
    _, arguments, environment = launch.call_args.args
    app_path = Path(arguments[arguments.index("--app-dir") + 1])
    assert app_path.is_absolute()
    assert app_path == SCRIPT.parents[1] / "src"
    assert environment["SUPABASE_URL"] == "http://127.0.0.1:54321"
    assert environment["SUPABASE_SECRET_KEY"] == "test-local-admin"
    assert arguments[arguments.index("--host") + 1] == "127.0.0.1"


def test_local_launcher_refuses_hosted_database_before_starting_api():
    status = CompletedProcess([], 0, stdout='API_URL="https://hosted.example.invalid"\n')
    with patch("subprocess.run", return_value=status), patch("os.execvpe") as launch:
        with pytest.raises(RuntimeError, match="remote Supabase"):
            START()
    launch.assert_not_called()
