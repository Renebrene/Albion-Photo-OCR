from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import recognition_quality
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)
SNAPSHOT = Path(__file__).resolve().parents[1] / "data/reports/recognition_quality/snapshot.json"


def test_published_snapshot_is_valid_and_keeps_denominators_separate():
    snapshot = recognition_quality._validate(json.loads(SNAPSHOT.read_text(encoding="utf-8")))

    assert snapshot["source"]["is_temporal_holdout"] is False
    assert snapshot["totals"]["labelled"] == 31983
    assert snapshot["variants"][0]["labelled"] == 31983
    # The view includes every report row above the 5% error-rate threshold;
    # address_metrics_source keeps the aggregate denominator for the full report.
    assert len(snapshot["addresses"]) == 39
    assert all(item["error_rate"] > 0.05 for item in snapshot["addresses"])
    assert sum(item["is_naming_variant"] for item in snapshot["addresses"]) == 17
    assert snapshot["addresses"][0]["is_naming_variant"] is True
    assert snapshot["addresses"][14]["is_naming_variant"] is False
    assert snapshot["addresses"][16]["classification"] == "naming_variant"
    assert snapshot["addresses"][28]["classification"] == "label_error"
    assert snapshot["address_metrics_source"]["error_addresses"] == 21
    assert snapshot["address_metrics_source"]["naming_variant_addresses"] == 17
    assert snapshot["address_metrics_source"]["label_error_addresses"] == 1
    assert snapshot["address_metrics_source"]["items"] == 32021
    assert snapshot["address_metrics_source"]["selection"] == "error_rate > 5% of items"
    assert snapshot["address_metrics_source"]["selected_addresses"] == 39
    assert snapshot["address_metrics_source"]["total_addresses"] == 109
    assert snapshot["address_metrics_source"]["unknown"] == 38
    assert snapshot["addresses"][0]["address_id"] == 1892


def test_snapshot_rejects_inconsistent_variant_denominator():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snapshot["variants"][0]["correct"] += 1

    with pytest.raises(ValueError, match="counts do not add up"):
        recognition_quality._validate(snapshot)


def test_snapshot_rejects_unsupported_schema():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snapshot["schema_version"] = 2

    with pytest.raises(ValueError, match="unsupported snapshot schema"):
        recognition_quality._validate(snapshot)


def test_missing_snapshot_returns_safe_service_error(monkeypatch, tmp_path):
    monkeypatch.setattr(recognition_quality, "SNAPSHOT_PATH", tmp_path / "missing.json")

    with pytest.raises(HTTPException) as error:
        recognition_quality.load_snapshot()

    assert error.value.status_code == 503
    assert "missing.json" not in error.value.detail


def test_quality_endpoint_returns_curated_snapshot(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "quality-reader:read")
    response = client.get(
        "/api/v1/recognition-quality",
        headers={"Authorization": "Bearer quality-reader"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 1
    assert body["source"]["run_id"] == 4
    assert body["source"]["is_temporal_holdout"] is False


def test_quality_endpoint_requires_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "quality-reader:jobs:read")
    response = client.get(
        "/api/v1/recognition-quality",
        headers={"Authorization": "Bearer quality-reader"},
    )

    assert response.status_code == 403
