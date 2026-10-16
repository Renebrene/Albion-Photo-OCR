from __future__ import annotations

from contextlib import contextmanager

from app.ingest.register import PhotoRecord
from app.preview import queue as preview_queue
from app.jobs import worker


def _record(photo_id="PH_" + "12" * 12):
    return PhotoRecord(
        photo_id=photo_id, source_path="/tmp/photo.jpg", filename="photo.jpg",
        sha256="ab" * 32, container_format="JPEG", frame_count=1,
        width=10, height=8, size_bytes=100,
    )


def test_preview_enqueue_checks_persisted_registration(monkeypatch):
    calls = []
    monkeypatch.setattr(preview_queue, "get_registered_photo", lambda photo_id: _record(photo_id))
    monkeypatch.setattr(preview_queue, "enqueue_photo_preview", lambda photo_id: calls.append(photo_id) or 18)

    assert preview_queue.enqueue_registered_photo(_record().photo_id) == 18
    assert calls == [_record().photo_id]


def test_preview_enqueue_ignores_photo_no_longer_registered(monkeypatch):
    calls = []
    monkeypatch.setattr(preview_queue, "get_registered_photo", lambda _photo_id: None)
    monkeypatch.setattr(preview_queue, "enqueue_photo_preview", lambda photo_id: calls.append(photo_id))

    assert preview_queue.enqueue_registered_photo(_record().photo_id) is None
    assert calls == []


def _fake_connection(monkeypatch, pages, statements):
    class Cursor:
        def execute(self, sql, params):
            statements.append((sql, params))

        def fetchall(self):
            return next(pages)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    @contextmanager
    def fake_connection():
        yield Connection()

    monkeypatch.setattr(preview_queue, "get_connection", fake_connection)


def test_backfill_retries_only_if_files_are_missing(monkeypatch, tmp_path):
    photo_id = "PH_" + "11" * 12
    paths = preview_queue.build_preview_paths(preview_root=tmp_path, photo_id=photo_id)
    paths.small.parent.mkdir(parents=True)
    paths.middle.parent.mkdir(parents=True)
    paths.small.write_bytes(b"small-preview")
    paths.middle.write_bytes(b"middle-preview")
    statements = []
    second_id = "PH_" + "22" * 12
    second_paths = preview_queue.build_preview_paths(preview_root=tmp_path, photo_id=second_id)
    second_paths.small.parent.mkdir(parents=True, exist_ok=True)
    second_paths.middle.parent.mkdir(parents=True, exist_ok=True)
    second_paths.small.write_bytes(b"second-small")
    pages = iter([
        [(photo_id, str(paths.small), str(paths.middle))],
        [(second_id, str(second_paths.small), str(second_paths.middle))],
    ])
    _fake_connection(monkeypatch, pages, statements)
    monkeypatch.setattr(preview_queue, "PREVIEW_ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(preview_queue, "enqueue_photo_preview", lambda value: calls.append(value) or 42)

    result = preview_queue.enqueue_missing_previews(limit=1)

    assert result == {"selected": 1, "queued": 1, "already_active": 0}
    assert calls == [second_id]
    assert all("LEFT JOIN public.photo_previews" in sql for sql, _ in statements)
    assert all(params[2] == 100 for _, params in statements)
    assert all("LIMIT %s" in sql for sql, _ in statements)


def test_preview_worker_dispatches_existing_pipeline(monkeypatch):
    record = _record()
    item = type("Result", (), {
        "ready": True,
        "small": type("File", (), {"action": "CREATE", "error": None})(),
        "middle": type("File", (), {"action": "CREATE", "error": None})(),
    })()
    monkeypatch.setattr(preview_queue, "get_registered_photo", lambda _photo_id: record)
    import app.preview.pipeline as pipeline
    monkeypatch.setattr(pipeline, "run", lambda records: type("Pipeline", (), {
        "results": [item], "database_updated": 1, "database_skipped": 0,
    })())

    result = preview_queue.run_photo_preview(record.photo_id)

    assert result["status"] == "DONE"
    assert result["ready"] is True
    assert result["small_action"] == "CREATE"


def test_preview_worker_fails_if_either_size_is_not_ready(monkeypatch):
    record = _record()
    item = type("Result", (), {
        "ready": False,
        "small": type("File", (), {"action": "CREATE", "error": None})(),
        "middle": type("File", (), {"action": "ERROR", "error": "decode failed"})(),
    })()
    monkeypatch.setattr(preview_queue, "get_registered_photo", lambda _photo_id: record)
    import app.preview.pipeline as pipeline
    monkeypatch.setattr(pipeline, "run", lambda _records: type("Pipeline", (), {
        "results": [item], "database_updated": 0, "database_skipped": 0,
    })())

    try:
        preview_queue.run_photo_preview(record.photo_id)
    except RuntimeError as exc:
        assert "decode failed" in str(exc)
    else:
        raise AssertionError("incomplete preview must fail the queue job")


def test_preview_stale_recovery_is_filtered_and_runs_in_one_pass(monkeypatch):
    import sys

    from app.jobs import worker

    monkeypatch.setattr(sys, "argv", ["worker", "--only", "PHOTO_PREVIEW", "--requeue-stale", "30"])
    calls = []
    monkeypatch.setattr(worker, "_requeue_stale_jobs", lambda minutes, **kwargs: calls.append((minutes, kwargs)) or {"jobs": 1, "dino_runs": 0, "hybrid_runs": 0})
    monkeypatch.setattr(worker, "run_once", lambda *_args, **_kwargs: None)
    worker.main()

    assert calls == [(30, {"video_only": False, "preview_only": True})]


def test_worker_has_photo_preview_dispatch(monkeypatch):
    calls = []
    monkeypatch.setattr(preview_queue, "run_photo_preview", lambda photo_id: calls.append(photo_id) or {"status": "DONE"})

    result = worker._execute({"job_type": "PHOTO_PREVIEW", "payload": {"photo_id": _record().photo_id}})

    assert result == {"status": "DONE"}
    assert calls == [_record().photo_id]
