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
    """
    Проверяем снимок как контракт, а не конкретные цифры прогона: файл
    пересобирается после каждого эксперимента, и зашитые итоги устаревают
    (21.11.2026 он пришёл с 38 190 подписанных вместо 31 983).
    """

    snapshot = recognition_quality._validate(json.loads(SNAPSHOT.read_text(encoding="utf-8")))

    assert snapshot["source"]["is_temporal_holdout"] is False
    assert snapshot["totals"]["labelled"] > 0

    # Варианты считаются от той же подписанной базы, что и итог: иначе
    # проценты несравнимы между собой и с агрегатом адресов.
    labels = {variant["labelled"] for variant in snapshot["variants"]}
    assert labels == {snapshot["totals"]["labelled"]}

    for variant in snapshot["variants"]:
        assert variant["correct"] + variant["wrong"] + variant["review"] == variant["labelled"]

    # В список попадают только адреса выше порога 5 % ошибок, и их не больше,
    # чем отобрал отчёт (часть строк могла не дойти до снимка).
    assert snapshot["addresses"]
    assert all(item["error_rate"] > 0.05 for item in snapshot["addresses"])
    assert snapshot["address_metrics_source"]["selected_addresses"] >= len(
        snapshot["addresses"]
    )

    for item in snapshot["addresses"]:
        assert item["correct"] + item["wrong"] + item["unknown"] == item["items"]
        assert item["classification"] in {
            "recognition_error",
            "naming_variant",
            "label_error",
        }


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
    published = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    # Эндпоинт отдаёт ровно опубликованный снимок (снимок пересобирается
    # после каждого эксперимента, поэтому сверяем с файлом, а не с номером
    # прогона из старой зашитой константы).
    assert body["schema_version"] == 1
    assert body["source"]["run_id"] == published["source"]["run_id"]
    assert body["source"]["is_temporal_holdout"] is False
    assert body["totals"] == published["totals"]


def test_quality_endpoint_requires_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "quality-reader:jobs:read")
    response = client.get(
        "/api/v1/recognition-quality",
        headers={"Authorization": "Bearer quality-reader"},
    )

    assert response.status_code == 403
