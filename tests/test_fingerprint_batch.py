"""
Progress, pause/resume and batch building of fingerprints.

The pause/cancel logic is exercised with stubbed queue calls (no database, no
model); anything that queues a real job cleans it up afterwards.
"""

from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.main import app
from app.jobs import worker as worker_mod

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.job_queue')")
                if cur.fetchone()[0] is None:
                    return False
                cur.execute(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = 'job_queue_status_check'"
                )
                row = cur.fetchone()
                return bool(row) and "PAUSED" in row[0]
    except Exception:
        return False


requires_pause = pytest.mark.skipif(
    not _db_available(),
    reason="schema/025 (progress + PAUSED) is not applied",
)


@pytest.fixture
def photo_folders(tmp_path):
    """Two folders with photos, for batch tests."""

    folders = []

    for name in ("alpha", "beta"):
        folder = tmp_path / name
        folder.mkdir()

        for index in range(3):
            Image.new("RGB", (16, 12)).save(folder / f"{index}.jpg", format="JPEG")

        folders.append(folder)

    empty = tmp_path / "empty"
    empty.mkdir()

    return folders, empty


# ---- progress callback (no database, no model) ----


@pytest.fixture
def fake_queue(monkeypatch):
    """Stub the two queue calls the control callback makes."""

    state = {"status": "RUNNING", "progress": []}

    monkeypatch.setattr(
        worker_mod.jobs,
        "set_progress",
        lambda job_id, progress: state["progress"].append(progress) or True,
    )
    monkeypatch.setattr(
        worker_mod.jobs,
        "job_status",
        lambda job_id: state["status"],
    )

    return state


def test_control_writes_progress_and_keeps_running(fake_queue):
    control = worker_mod.job_control(42)

    control(5, 10, "эмбеддинги")

    assert fake_queue["progress"][0]["percent"] == 50.0
    assert fake_queue["progress"][0]["stage"] == "эмбеддинги"
    assert fake_queue["progress"][0]["done"] == 5


def test_control_stops_a_cancelled_job(fake_queue):
    control = worker_mod.job_control(42)
    fake_queue["status"] = "CANCELLED"

    with pytest.raises(worker_mod.JobCancelled):
        control(1, 10, "эмбеддинги")


def test_control_waits_out_a_pause(monkeypatch, fake_queue):
    monkeypatch.setattr(worker_mod, "PAUSE_MAX_SECONDS", 30)
    monkeypatch.setattr(worker_mod, "CONTROL_INTERVAL", 0)

    control = worker_mod.job_control(42)

    def resume_soon():
        time.sleep(2.5)
        fake_queue["status"] = "RUNNING"

    import threading

    threading.Thread(target=resume_soon, daemon=True).start()

    fake_queue["status"] = "PAUSED"
    started = time.monotonic()
    control(1, 10, "эмбеддинги")

    assert time.monotonic() - started >= 2


def test_control_fails_when_nobody_resumes(monkeypatch, fake_queue):
    monkeypatch.setattr(worker_mod, "PAUSE_MAX_SECONDS", 2)
    monkeypatch.setattr(worker_mod, "CONTROL_INTERVAL", 0)

    control = worker_mod.job_control(42)
    fake_queue["status"] = "PAUSED"

    with pytest.raises(worker_mod.JobPausedTooLong):
        control(1, 10, "эмбеддинги")


def test_progress_writes_are_throttled(monkeypatch, fake_queue):
    monkeypatch.setattr(worker_mod, "CONTROL_INTERVAL", 60)

    control = worker_mod.job_control(42)

    control(1, 100, "эмбеддинги")
    control(2, 100, "эмбеддинги")
    control(3, 100, "эмбеддинги")
    control(100, 100, "дескрипторы")  # the last one always lands

    assert len(fake_queue["progress"]) == 2


# ---- batch endpoint ----


@requires_pause
def test_batch_queues_one_job_per_item(photo_folders):
    folders, empty = photo_folders

    response = client.post(
        "/api/v1/fingerprints/build-batch",
        json={
            "items": [
                {"fingerprint_id": "test_alpha_v33", "folder": str(folders[0])},
                {"fingerprint_id": "test_beta_v33", "folder": str(folders[1])},
                {"fingerprint_id": "test_empty_v33", "folder": str(empty)},
            ],
            "max_photos": 2,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert len(body["jobs"]) == 2
    assert len(body["errors"]) == 1
    assert "фотограф" in body["errors"][0]["error"]

    # Clean up: cancel the queued jobs so the worker never builds anything.
    for job in body["jobs"]:
        client.post(f"/api/v1/jobs/{job['job_id']}/cancel")


@requires_pause
def test_batch_state_aggregates_its_jobs(photo_folders):
    folders, _empty = photo_folders

    started = client.post(
        "/api/v1/fingerprints/build-batch",
        json={
            "items": [
                {"fingerprint_id": "test_state_a_v33", "folder": str(folders[0])},
                {"fingerprint_id": "test_state_b_v33", "folder": str(folders[1])},
            ]
        },
    ).json()

    state = client.get(f"/api/v1/fingerprints/batch/{started['batch_id']}")

    assert state.status_code == 200
    body = state.json()
    assert body["total"] == 2
    assert body["percent"] == 0.0
    assert {job["fingerprint_id"] for job in body["jobs"]} == {
        "test_state_a_v33",
        "test_state_b_v33",
    }

    for job in started["jobs"]:
        client.post(f"/api/v1/jobs/{job['job_id']}/cancel")


def test_batch_rejects_a_malformed_id():
    response = client.get("/api/v1/fingerprints/batch/not-a-batch-id")

    assert response.status_code == 400


# ---- pause / resume endpoints ----


@requires_pause
def test_pause_holds_a_queued_job_and_resume_releases_it(photo_folders):
    folders, _empty = photo_folders

    started = client.post(
        "/api/v1/fingerprints/build",
        json={"fingerprint_id": "test_pause_v33", "folder": str(folders[0])},
    ).json()

    job_id = started["job_id"]

    paused = client.post(f"/api/v1/jobs/{job_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "PAUSED"

    # A paused job is never claimed.
    from app.jobs import database as jobs_db

    assert jobs_db.job_status(job_id) == "PAUSED"

    resumed = client.post(f"/api/v1/jobs/{job_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] in {"PENDING", "RUNNING"}

    client.post(f"/api/v1/jobs/{job_id}/cancel")


@requires_pause
def test_resume_without_a_pause_is_refused(photo_folders):
    folders, _empty = photo_folders

    started = client.post(
        "/api/v1/fingerprints/build",
        json={"fingerprint_id": "test_resume_v33", "folder": str(folders[0])},
    ).json()

    response = client.post(f"/api/v1/jobs/{started['job_id']}/resume")

    assert response.status_code == 409

    client.post(f"/api/v1/jobs/{started['job_id']}/cancel")


@requires_pause
def test_pause_unknown_job_is_404():
    assert client.post("/api/v1/jobs/999999999/pause").status_code == 404
    assert client.post("/api/v1/jobs/999999999/resume").status_code == 404


# ---- worker claim filter ----


@requires_pause
def test_claim_can_be_limited_to_build_jobs(photo_folders):
    """A dedicated builder worker must not steal QWEN/DINO jobs."""

    from app.jobs import database as jobs_db

    folders, _empty = photo_folders

    build_id = jobs_db.enqueue_fingerprint_build(
        "test_filter_v33", str(folders[0]), max_photos=1
    )
    other_id = jobs_db.enqueue("NL_SEARCH", {"query": "тест фильтра"})

    claimed = jobs_db.claim_next(types=["FINGERPRINT_BUILD"])

    assert claimed is not None
    assert claimed["id"] == build_id
    assert claimed["job_type"] == "FINGERPRINT_BUILD"

    # Clean up both jobs (the claimed one is RUNNING now).
    jobs_db.mark_cancelled(build_id)
    jobs_db.mark_cancelled(other_id)
