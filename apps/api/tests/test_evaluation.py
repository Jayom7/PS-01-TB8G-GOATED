from __future__ import annotations

import copy
import json
import runpy
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from ps01_api import main
from ps01_api.main import evaluation_checks_passed, recorded_evaluation

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/evaluate_local_retrieval.py"
SUMMARY = runpy.run_path(str(SCRIPT))["summarize_results"]


def test_hit_rate_uses_only_positive_queries_and_locations_are_metadata_checks():
    results = [
        {
            "hit": hit,
            "reciprocal_rank": rank,
            "source_types_found": ["pdf", "image_ocr"],
            "forbidden_source_hits": [],
            "latency_ms": 10,
        }
        for hit, rank in [
            (True, 1.0),
            (False, 0.0),
            (True, 0.5),
            (True, 0.25),
            (True, 0.0),
            (True, 1.0),
        ]
    ]
    results.append(
        {
            "hit": True,
            "unauthorized_chunk_rows": 0,
            "unauthorized_document_rows": 0,
            "forbidden_source_hits": [],
        }
    )
    rows = [
        {"chunk_id": "pdf-row", "source_type": "pdf", "page_number": 1},
        {"chunk_id": "no-location", "source_type": "structured"},
    ]
    result = SUMMARY(results, rows)
    assert result["retrieval_hit_rate_at_k"] == 0.8
    assert result["mean_reciprocal_rank"] == 0.55
    assert result["positive_query_count"] == 5
    assert "retrieval_recall_at_k" not in result
    assert result["measured_checks"]["retrieved_citation_locations_present"] == 1
    assert result["measured_checks"]["retrieved_citation_locations_checked"] == 2
    assert "citation_provenance_valid" not in result["measured_checks"]
    assert result["authorization_violations"] == 0
    assert result["measured_checks"]["cross_modal_retrieval"] is False
    results[5]["source_types_found"] = ["pdf", "image_ocr", "structured"]
    assert SUMMARY(results, rows)["measured_checks"]["cross_modal_retrieval"] is True
    results[5]["hit"] = False
    assert SUMMARY(results, rows)["measured_checks"]["cross_modal_retrieval"] is False
    results[4]["forbidden_source_hits"] = ["forbidden"]
    results[6]["unauthorized_chunk_rows"] = 2
    assert SUMMARY(results, rows)["authorization_violations"] == 3


def test_legacy_results_are_relabelled_as_historical_without_changing_saved_input():
    saved = {
        "retrieval_recall_at_k": 1.0,
        "measured_checks": {"citation_provenance_valid": 39, "citation_provenance_checked": 39},
    }
    original = copy.deepcopy(saved)
    result = recorded_evaluation(saved)
    assert saved == original
    assert result["run_kind"] == "historical_legacy"
    assert result["retrieval_hit_rate_at_k"] == 1.0
    assert "retrieval_recall_at_k" not in result
    assert result["measured_checks"] == {
        "retrieved_citation_locations_present": 39,
        "retrieved_citation_locations_checked": 39,
    }


def test_refreshing_a_current_saved_run_does_not_call_it_fresh():
    result = recorded_evaluation({"schema_version": 2, "retrieval_hit_rate_at_k": 0.5})
    assert result["run_kind"] == "recorded_local"
    assert result["retrieval_hit_rate_at_k"] == 0.5


def test_zero_forbidden_hits_does_not_hide_a_retrieval_failure():
    assert not evaluation_checks_passed(
        {"authorization_violations": 0, "results": [{"hit": False}]}
    )
    assert evaluation_checks_passed({"authorization_violations": 0, "results": [{"hit": True}]})
    assert not evaluation_checks_passed({"authorization_violations": 0, "results": []})
    assert not evaluation_checks_passed({"authorization_violations": 1, "results": [{"hit": True}]})
    assert not evaluation_checks_passed(
        {
            "authorization_violations": 0,
            "results": [{"hit": True}],
            "test_only_results": [{"hit": False}],
        }
    )


def test_expanded_matrix_preserves_baseline_and_declares_role_expectations():
    module = runpy.run_path(str(SCRIPT))
    assert len(module["BASELINE_CASES"]) == 6
    cases = module["CASES"]
    assert len(cases) >= 30
    assert {case["role"] for case in cases} == {
        "CEO",
        "Finance Manager",
        "HR Manager",
        "Sales Manager",
        "Engineer",
    }
    for case in cases:
        assert "expected_abstention" in case and case["expected_behavior"]
        assert not set(case["authorized_evidence"]) & case["forbidden"]
        assert case["expected"] <= set(case["authorized_evidence"])


@pytest.fixture
def evaluation_env(tmp_path):
    path = tmp_path / "evaluation.json"
    identity = {"user_id": "actor", "organization_id": "org", "role": "CEO"}
    with (
        patch.object(main, "EVALUATION_RESULTS", path),
        patch.object(main, "_local_demo_enabled", return_value=True),
        patch.object(main, "require_session", AsyncMock(return_value="actor-token")),
        patch.object(main, "_identity", AsyncMock(return_value=identity)),
        patch.object(main, "_context_token", AsyncMock(return_value=("actor-token", "CEO"))),
        patch.object(main, "require_local_ceo", AsyncMock(return_value=("actor-token", identity))),
        patch.object(
            main,
            "_rest_rows",
            AsyncMock(
                return_value=httpx.Response(200, json=[], headers={"content-range": "0-0/18"})
            ),
        ),
    ):
        yield path


def test_empty_recorded_and_corrupt_evaluation_states(evaluation_env):
    client = TestClient(main.app)
    assert client.get("/api/v1/evaluation").json() == {"state": "not_run", "result": None}
    evaluation_env.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "results": [],
                "completed_at": "2026-10-09T00:00:00Z",
                "query_count": 6,
            }
        )
    )
    result = client.get("/api/v1/evaluation").json()["result"]
    assert result["run_kind"] == "recorded_local"
    assert result["completed_at"] == "2026-10-09T00:00:00Z"
    assert "execution_origin" not in result  # Never invent app provenance for CLI artifacts.
    evaluation_env.write_text("broken")
    assert client.get("/api/v1/evaluation").json()["state"] == "unavailable"


def test_run_persists_real_workflow_return_and_archives_previous(evaluation_env):
    prior = {
        "schema_version": 2,
        "dataset": "prior",
        "query_count": 6,
        "completed_at": "2026-10-08T00:00:00Z",
        "results": [],
    }
    evaluation_env.write_text(json.dumps(prior))
    run = AsyncMock(
        return_value={"schema_version": 2, "dataset": "new", "query_count": 6, "results": []}
    )
    with patch.object(main.runpy, "run_path", return_value={"run": run}):
        response = TestClient(main.app).post("/api/v1/evaluation/run")
    assert response.status_code == 200
    run.assert_awaited_once()
    saved = json.loads(evaluation_env.read_text())
    assert saved["execution_origin"] == "app"
    assert saved["completed_at"] and saved["duration_ms"] >= 0
    assert saved["corpus"]["documents"] == 18
    assert evaluation_env.stat().st_mode & 0o777 == 0o600
    archives = list(evaluation_env.parent.glob("evaluation-history-*.json"))
    assert len(archives) == 1 and json.loads(archives[0].read_text()) == prior
    refreshed = TestClient(main.app).get("/api/v1/evaluation").json()["result"]
    assert refreshed["run_id"] == saved["run_id"] and refreshed["run_kind"] == "recorded_local"
    assert refreshed["history"][0]["completed_at"] == prior["completed_at"]


def test_failed_run_keeps_previous_artifact(evaluation_env):
    original = '{"schema_version":2,"results":[]}'
    evaluation_env.write_text(original)
    with patch.object(
        main.runpy, "run_path", return_value={"run": AsyncMock(side_effect=RuntimeError("failed"))}
    ):
        response = TestClient(main.app).post("/api/v1/evaluation/run")
    assert response.status_code == 503
    assert evaluation_env.read_text() == original


def test_restricted_context_does_not_read_saved_metrics(evaluation_env):
    evaluation_env.write_text('{"results":[],"secret":"not visible"}')
    with patch.object(main, "_context_token", AsyncMock(return_value=("hr-token", "HR Manager"))):
        response = TestClient(main.app).get("/api/v1/evaluation")
    assert response.json() == {"state": "restricted", "result": None}


def test_second_run_during_evaluation_is_rejected(evaluation_env):
    with (
        patch.object(main.EVALUATION_LOCK, "locked", return_value=True),
        patch.object(main.runpy, "run_path") as run,
    ):
        response = TestClient(main.app).post("/api/v1/evaluation/run")
    assert response.status_code == 409
    run.assert_not_called()
