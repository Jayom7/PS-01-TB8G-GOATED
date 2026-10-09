"""Security action authorization and truthful state mapping, with process stubs."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from ps01_api import main


@pytest.mark.parametrize("role,context", [("HR Manager", "HR Manager"), ("CEO", "HR Manager")])
def test_non_ceo_actor_or_context_cannot_launch_verifier(role, context):
    with (
        patch.object(main, "_local_demo_enabled", return_value=True),
        patch.object(main, "require_session", AsyncMock(return_value="token")),
        patch.object(main, "_identity", AsyncMock(return_value={"role": role})),
        patch.object(main, "_context_token", AsyncMock(return_value=("token", context))),
        patch.object(main.asyncio, "create_subprocess_exec") as launch,
    ):
        response = TestClient(main.app).post("/api/v1/security/checks/run")
    assert response.status_code == 403
    launch.assert_not_called()


def test_security_action_is_unavailable_outside_local_demo():
    with patch.object(main, "_local_demo_enabled", return_value=False):
        assert TestClient(main.app).post("/api/v1/security/checks/run").status_code == 404


@pytest.mark.parametrize(
    "status,expected", [("passed", "passed"), ("failed", "failed"), ("blocked", "unavailable")]
)
def test_process_report_cannot_average_away_failed_or_unavailable_checks(
    tmp_path, status, expected
):
    directory = tmp_path / "data/local"
    directory.mkdir(parents=True)

    async def wait():
        (directory / "security-verification.json").write_text(
            json.dumps(
                {
                    "completed_at": datetime.now(UTC).isoformat(),
                    "checks": [
                        {"name": "Local authorization", "status": status},
                        {
                            "name": "Real Gemini answer/source inspection",
                            "status": "blocked",
                            "detail": "Explicitly skipped.",
                        },
                    ],
                }
            )
        )

    process = AsyncMock()
    process.wait.side_effect = wait
    process.returncode = 2
    with (
        patch.object(main, "REPOSITORY_ROOT", tmp_path),
        patch.object(main, "require_local_ceo", AsyncMock()),
        patch.object(main.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)),
    ):
        response = TestClient(main.app).post("/api/v1/security/checks/run")
    assert response.status_code == 200
    assert response.json()["state"] == expected
    assert response.json()["checks"][1]["status"] == "not_run"
