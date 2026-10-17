"""
Working-folder endpoints for INGEST (items 5 and 6 of the UI backlog).

Validation runs everywhere; endpoints that persist a setting or enqueue a job
skip unless PostgreSQL is configured. The folder-setting tests restore the
previous value, so a developer's own choice is not overwritten.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.app_settings')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


def _ingest_job_type_available() -> bool:
    """True once schema/019 widened the job_type CHECK to INGEST_DIR."""

    if not _db_available():
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_get_constraintdef(oid) "
                    "FROM pg_constraint WHERE conname = 'job_queue_job_type_check'"
                )
                row = cur.fetchone()
                return bool(row) and "INGEST_DIR" in row[0]
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="integration PostgreSQL is not configured (INGEST_DB_*)",
)

requires_ingest_job = pytest.mark.skipif(
    not _ingest_job_type_available(),
    reason="schema/019 (INGEST_DIR job type) is not applied",
)


@pytest.fixture
def photo_folder(tmp_path):
    """A small folder tree with two photos and an unrelated text file."""

    (tmp_path / "a.jpg").write_bytes(b"x" * 10)
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "b.JPG").write_bytes(b"y" * 20)
    (nested / "notes.txt").write_text("nope", encoding="utf-8")

    return tmp_path


# --- validation (no database) ------------------------------------------------


def test_folder_path_is_required():
    assert client.put("/api/v1/ingest/folder", json={"path": ""}).status_code == 422


def test_missing_folder_is_not_found():
    response = client.put("/api/v1/ingest/folder", json={"path": "/nope/nope"})
    assert response.status_code == 404
    # The client's own string is echoed nowhere in the error detail.
    assert "/nope" not in response.text


def test_a_file_is_not_a_directory(tmp_path):
    path = tmp_path / "file.jpg"
    path.write_bytes(b"x")

    response = client.put("/api/v1/ingest/folder", json={"path": str(path)})

    assert response.status_code == 400


def test_scan_of_a_missing_folder_is_not_found():
    response = client.post("/api/v1/ingest/scan", json={"path": "/nope/nope"})
    assert response.status_code == 404


def test_scan_path_is_required():
    assert client.post("/api/v1/ingest/scan", json={}).status_code == 422


# --- counting (no database) --------------------------------------------------


def test_scan_counts_photos_recursively(photo_folder):
    response = client.post(
        "/api/v1/ingest/scan", json={"path": str(photo_folder)}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["files"] == 2
    assert body["bytes"] == 30
    assert body["truncated"] is False


def test_scan_does_not_decode_images(tmp_path):
    # A file with a photo extension but broken content is still counted: the
    # folder picker must not spend time decoding.
    (tmp_path / "broken.jpg").write_bytes(b"not an image")

    body = client.post("/api/v1/ingest/scan", json={"path": str(tmp_path)}).json()

    assert body["files"] == 1


def test_scan_counts_photos_videos_and_extensions(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x" * 10)
    (tmp_path / "clip.mov").write_bytes(b"v" * 20)
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "clip.MP4").write_bytes(b"w" * 30)
    (nested / "notes.txt").write_text("ignored", encoding="utf-8")

    body = client.post("/api/v1/ingest/scan", json={"path": str(tmp_path)}).json()

    assert body["photos"] == 1
    assert body["videos"] == 2
    assert body["media_files"] == 3
    assert body["files"] == 1  # legacy photo-only field
    assert body["photo_bytes"] == 10
    assert body["video_bytes"] == 50
    assert body["bytes"] == 60
    assert body["extensions"] == {".jpg": 1, ".mov": 1, ".mp4": 1}
    assert body["problem_count"] == 0
    assert body["preliminary"] is True
    assert body["timed_out"] is False


def test_scan_reports_empty_supported_files_as_problems(tmp_path):
    (tmp_path / "ok.jpg").write_bytes(b"x" * 5)
    (tmp_path / "empty.mp4").write_bytes(b"")

    body = client.post("/api/v1/ingest/scan", json={"path": str(tmp_path)}).json()

    assert body["photos"] == 1
    assert body["videos"] == 1
    assert body["problem_count"] == 1
    assert body["problems"] == [{"filename": "empty.mp4", "reason": "файл пуст"}]


def test_scan_is_bounded_by_file_count(tmp_path, monkeypatch):
    from app.api import sources

    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "b.jpg").write_bytes(b"y")
    monkeypatch.setattr(sources, "SOURCE_SCAN_FILE_LIMIT", 1)

    body = client.post("/api/v1/ingest/scan", json={"path": str(tmp_path)}).json()

    assert body["media_files"] == 1
    assert body["truncated"] is True
    assert body["timed_out"] is False


def test_scan_is_bounded_by_time(tmp_path, monkeypatch):
    from app.api import sources

    (tmp_path / "a.jpg").write_bytes(b"x" * 5)
    monkeypatch.setattr(sources, "SOURCE_SCAN_TIMEOUT_SECONDS", 1.0)
    moments = iter([0.0] + [100.0] * 8)
    monkeypatch.setattr(sources, "_now", lambda: next(moments))

    body = client.post("/api/v1/ingest/scan", json={"path": str(tmp_path)}).json()

    assert body["media_files"] == 0
    assert body["truncated"] is True
    assert body["timed_out"] is True


# --- persistence (database) --------------------------------------------------


@requires_db
def test_folder_is_saved_and_reported_back(photo_folder):
    from app import settings_store
    from app.api.config import SOURCE_FOLDER_KEY

    previous = settings_store.get(SOURCE_FOLDER_KEY)

    try:
        saved = client.put(
            "/api/v1/ingest/folder", json={"path": str(photo_folder)}
        )
        assert saved.status_code == 200

        body = saved.json()
        assert body["configured"] == str(photo_folder)
        assert body["exists"] is True
        assert body["files"] == 2
        assert body["bytes"] == 30

        reported = client.get("/api/v1/ingest/folder")
        assert reported.status_code == 200
        assert reported.json()["configured"] == str(photo_folder)
    finally:
        if previous is None:
            from app.ingest.database import get_connection

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.app_settings WHERE key = %s",
                        (SOURCE_FOLDER_KEY,),
                    )
        else:
            settings_store.set_value(SOURCE_FOLDER_KEY, previous)


# --- launch (database + schema 019) -----------------------------------------


@requires_ingest_job
def test_run_enqueues_an_ingest_job(photo_folder):
    from app.ingest.database import get_connection

    response = client.post(
        "/api/v1/ingest/run", json={"path": str(photo_folder)}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"]

    try:
        # The second call must not duplicate the pending job.
        again = client.post(
            "/api/v1/ingest/run", json={"path": str(photo_folder)}
        ).json()
        assert again["skipped"] is True
        assert again["job_id"] is None
    finally:
        # Remove only the rows this test created.
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.job_queue "
                    "WHERE job_type = 'INGEST_DIR' "
                    "AND payload ->> 'directory' = %s",
                    (str(photo_folder),),
                )
