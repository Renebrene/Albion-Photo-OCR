from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app
from app.api import routes

client = TestClient(app)


def test_preview_backfill_route_is_bounded_and_delegates(monkeypatch):
    calls = []
    from app.preview import queue as preview_queue

    def fake(*, limit, photo_ids=None):
        calls.append({"limit": limit, "photo_ids": photo_ids})
        return {"selected": 2, "queued": 2, "already_active": 0}

    monkeypatch.setattr(preview_queue, "enqueue_missing_previews", fake)

    response = client.post("/api/v1/previews/backfill?limit=10")

    assert response.status_code == 200
    assert response.json() == {"selected": 2, "queued": 2, "already_active": 0}
    assert calls == [{"limit": 10, "photo_ids": None}]


def test_preview_backfill_accepts_an_explicit_photo_id_list(monkeypatch):
    """Пересоздание превью по photo_id: папка не сканируется, идёт список."""

    calls = []
    from app.preview import queue as preview_queue

    def fake(*, limit, photo_ids=None):
        calls.append({"limit": limit, "photo_ids": photo_ids})
        return {
            "selected": 1,
            "queued": 1,
            "already_active": 0,
            "originals_missing": 1,
        }

    monkeypatch.setattr(preview_queue, "enqueue_missing_previews", fake)

    ids = ["PH_" + "ab" * 12, "PH_" + "cd" * 12]
    response = client.post(
        "/api/v1/previews/backfill?limit=10", json={"photo_ids": ids}
    )

    assert response.status_code == 200
    assert response.json()["originals_missing"] == 1
    assert calls == [{"limit": 10, "photo_ids": ids}]


def test_preview_backfill_rejects_an_empty_photo_id_list():
    response = client.post("/api/v1/previews/backfill", json={"photo_ids": []})

    assert response.status_code == 422


def test_preview_backfill_rejects_unbounded_limit():
    assert client.post("/api/v1/previews/backfill?limit=5001").status_code == 422


def test_preview_job_pause_is_rejected(monkeypatch):
    monkeypatch.setattr(routes.jobs_db, "get_job", lambda _job_id: {"job_type": "PHOTO_PREVIEW"})

    response = client.post("/api/v1/jobs/99/pause")

    assert response.status_code == 409
    assert "cannot be paused" in response.json()["detail"]
