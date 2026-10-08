from __future__ import annotations

import copy
import runpy
from pathlib import Path

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
        for hit, rank in [(True, 1.0), (False, 0.0), (True, 0.5), (True, 0.25), (True, 0.0)]
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
    assert result["retrieval_hit_rate_at_k"] == 0.75
    assert result["mean_reciprocal_rank"] == 0.438
    assert result["positive_query_count"] == 4
    assert "retrieval_recall_at_k" not in result
    assert result["measured_checks"]["retrieved_citation_locations_present"] == 1
    assert result["measured_checks"]["retrieved_citation_locations_checked"] == 2
    assert "citation_provenance_valid" not in result["measured_checks"]
    assert result["authorization_violations"] == 0
    results[4]["forbidden_source_hits"] = ["forbidden"]
    results[5]["unauthorized_chunk_rows"] = 2
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
