"""Unit suites never authenticate or write audit events to external databases."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def isolate_external_identity_and_audit():
    with (
        patch("ps01_api.main.record_security_event", AsyncMock(return_value=True)),
        patch("ps01_api.main.verify_supabase_session", AsyncMock(return_value=None)),
    ):
        yield
