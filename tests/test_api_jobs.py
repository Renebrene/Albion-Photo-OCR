"""
Tests for the job-queue API (enqueue DINO batch / HYBRID run, read jobs).

Scope checks run everywhere; enqueue tests require PostgreSQL and clean up
the batch and job they create.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.ingest.database import get_connection

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select to_regclass('public.photos'), "
                    "to_regclass('public.job_queue')"
                )
                photos, queue = cur.fetchone()
                return photos is not None and queue is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="integration PostgreSQL is not configured",
)


def test_dino_batch_requires_jobs_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/jobs/dino-batch",
        json={"run_type": "NORMAL"},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_list_jobs_requires_jobs_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get(
        "/api/v1/jobs",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_force_rerun_without_photo_ids_is_422(monkeypatch):
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    response = client.post(
        "/api/v1/jobs/dino-batch",
        json={"run_type": "FORCE_RERUN"},
    )
    assert response.status_code == 422


@requires_db
def test_enqueue_force_rerun_batch(monkeypatch):
    from app.runs import coordination

    if coordination.active_operation() is not None:
        pytest.skip("a real pipeline/scheduler/sort operation is active")

    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select photo_id from public.photos order by photo_id limit 2")
            photo_ids = [row[0] for row in cur.fetchall()]

    if len(photo_ids) < 2:
        pytest.skip("not enough photos")

    response = client.post(
        "/api/v1/jobs/dino-batch",
        json={"run_type": "FORCE_RERUN", "photo_ids": photo_ids},
    )
    assert response.status_code == 202

    body = response.json()
    assert body["total_count"] == 2
    assert isinstance(body["job_id"], int)
    batch_id = body["batch_id"]

    job = client.get(f"/api/v1/jobs/{body['job_id']}").json()
    assert job["job_type"] == "DINO_BATCH"
    assert job["status"] == "PENDING"
    assert job["payload"]["batch_id"] == batch_id
    history_id = job["payload"]["run_history_id"]

    # Clean up the test-owned history row, queue job and domain batch.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.run_history WHERE run_id = %s",
                (history_id,),
            )
            cur.execute(
                "DELETE FROM public.job_queue WHERE id = %s",
                (body["job_id"],),
            )
            cur.execute(
                "DELETE FROM public.dino_batches WHERE batch_id = %s",
                (batch_id,),
            )


@requires_db
def test_get_unknown_job_returns_404(monkeypatch):
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    assert client.get("/api/v1/jobs/999999999").status_code == 404


def test_qwen_rescan_uses_only_the_selected_photo(monkeypatch):
    """Карточка шлёт один photo_id — весь корпус не должен ставиться."""

    from app.api import routes
    from app.runs import history

    photo_id = "PH_" + "ab" * 12
    monkeypatch.setattr(
        routes.repository, "all_photo_ids",
        lambda: (_ for _ in ()).throw(AssertionError("must not enqueue all")),
    )
    monkeypatch.setattr(history, "create_run", lambda **kw: 1)
    monkeypatch.setattr(history, "add_jobs", lambda *a, **kw: None)
    monkeypatch.setattr(history, "finish_enqueue", lambda *a, **kw: None)

    queued = []
    monkeypatch.setattr(
        routes.jobs_db, "enqueue_qwen",
        lambda pid, **kw: queued.append(pid) or 10,
    )

    response = client.post(
        "/api/v1/jobs/qwen",
        json={"photo_ids": [photo_id]},
    )

    assert response.status_code == 202
    assert queued == [photo_id]
    assert response.json()["jobs"] == 1


def test_qwen_empty_explicit_list_does_not_fall_back_to_all(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(
        routes.repository, "all_photo_ids",
        lambda: (_ for _ in ()).throw(AssertionError("must not enqueue all")),
    )

    response = client.post("/api/v1/jobs/qwen", json={"photo_ids": []})

    assert response.status_code == 422
