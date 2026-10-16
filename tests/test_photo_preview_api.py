from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app
from app.api import routes

client = TestClient(app)


def test_preview_backfill_route_is_bounded_and_delegates(monkeypatch):
    calls = []
    from app.preview import queue as preview_queue

    monkeypatch.setattr(preview_queue, "enqueue_missing_previews", lambda *, limit: calls.append(limit) or {
        "selected": 2, "queued": 2, "already_active": 0,
    })

    response = client.post("/api/v1/previews/backfill?limit=10")

    assert response.status_code == 200
    assert response.json() == {"selected": 2, "queued": 2, "already_active": 0}
    assert calls == [10]


def test_preview_backfill_rejects_unbounded_limit():
    assert client.post("/api/v1/previews/backfill?limit=5001").status_code == 422


def test_preview_job_pause_is_rejected(monkeypatch):
    monkeypatch.setattr(routes.jobs_db, "get_job", lambda _job_id: {"job_type": "PHOTO_PREVIEW"})

    response = client.post("/api/v1/jobs/99/pause")

    assert response.status_code == 409
    assert "cannot be paused" in response.json()["detail"]
