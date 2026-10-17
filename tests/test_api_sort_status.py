"""Sorting status endpoint (DINO/HYBRID summary)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app
from app.runs import sort_status

client = TestClient(app)


def test_sort_status_returns_the_aggregate(monkeypatch):
    payload = {
        "last": {
            "run_id": 7,
            "kind": "sort",
            "mode": "manual",
            "status": "DONE",
            "has_log": True,
            "stats": {"matched": 12, "total": 20, "failed": 1},
        },
        "modes": {"manual": None, "schedule": None, "outofqueue": None},
        "current": None,
        "active": None,
    }
    monkeypatch.setattr(sort_status, "status", lambda: payload)

    response = client.get("/api/v1/sort/status")

    assert response.status_code == 200
    assert response.json()["last"]["stats"]["matched"] == 12


def _run(run_id, kind, mode, started, title, source_id):
    return {
        "run_id": run_id,
        "kind": kind,
        "mode": mode,
        "status": "DONE",
        "source_id": source_id,
        "title": title,
        "counts": {},
        "stages": [],
        "message": None,
        "error_count": 0,
        "has_log": False,
        "started_at": started,
        "finished_at": started,
    }


def test_pipeline_stage_supplies_stats_without_sort_history(monkeypatch):
    """«Обновление базы» does not create a sort row; its DINO stage must show."""

    pipeline = {
        **_run(21, "pipeline", "manual", "2026-10-17 22:08:58", "Обновление базы — DINO/HYBRID", 7),
        "stats": {"batch_id": 7, "total": 20, "done": 20, "failed": 0, "matched": 18},
    }

    monkeypatch.setattr(sort_status, "_latest_run", lambda **kwargs: None)
    monkeypatch.setattr(sort_status, "_latest_pipeline_sort", lambda: pipeline)
    monkeypatch.setattr(sort_status, "_active_batch", lambda: None)
    monkeypatch.setattr(sort_status.coordination, "active_operation", lambda: None)

    data = sort_status.status()

    assert data["last"]["stats"]["matched"] == 18
    assert data["last"]["stats"]["total"] == 20
    assert data["modes"]["pipeline"] == pipeline


def test_newest_sorting_event_wins(monkeypatch):
    manual = _run(1, "sort", "manual", "2026-10-17 20:00:00", "DINO batch #3", 3)
    pipeline = {
        **_run(2, "pipeline", "manual", "2026-10-17 22:00:00", "Обновление базы — DINO/HYBRID", 4),
        "stats": {"batch_id": 4, "total": 10, "done": 10, "failed": 0, "matched": 9},
    }

    def latest_run(*, kind=None, mode=None):
        if kind == "sort" and mode == "manual":
            return manual
        if kind == "sort":
            return manual
        return None

    monkeypatch.setattr(sort_status, "_latest_run", latest_run)
    monkeypatch.setattr(sort_status, "_latest_pipeline_sort", lambda: pipeline)
    monkeypatch.setattr(sort_status, "_active_batch", lambda: None)
    monkeypatch.setattr(sort_status.coordination, "active_operation", lambda: None)
    monkeypatch.setattr(
        sort_status, "_sort_run_stats",
        lambda run: {"batch_id": 3, "total": 10, "done": 10, "failed": 0, "matched": 7},
    )

    data = sort_status.status()

    assert data["last"]["kind"] == "pipeline"
    assert data["last"]["stats"]["matched"] == 9


def test_hybrid_sort_resolves_its_dino_batch(monkeypatch):
    seen = {}

    def batch_for_hybrid(run_id):
        seen["hybrid_run_id"] = run_id
        return 55

    monkeypatch.setattr(sort_status, "_batch_for_hybrid", batch_for_hybrid)
    monkeypatch.setattr(
        sort_status, "_batch_stats",
        lambda batch_id: {"batch_id": batch_id, "total": 1, "done": 1, "failed": 0, "matched": 1},
    )

    stats = sort_status._sort_run_stats(  # noqa: SLF001 - focused unit test
        _run(5, "sort", "manual", "2026-10-17 20:00:00", "HYBRID run #77", 77)
    )

    assert seen["hybrid_run_id"] == 77
    assert stats["batch_id"] == 55
