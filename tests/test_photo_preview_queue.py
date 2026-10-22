from __future__ import annotations

from app.ingest import runner
from app.ingest.register import PhotoRecord


def _record(photo_id="PH_" + "12" * 12):
    return PhotoRecord(
        photo_id=photo_id,
        source_path="/tmp/photo.jpg",
        filename="photo.jpg",
        sha256="ab" * 32,
        container_format="JPEG",
        frame_count=1,
        width=10,
        height=8,
        size_bytes=100,
    )


def test_directory_ingest_queues_preview_after_new_registration(monkeypatch, tmp_path):
    record = _record()
    enqueued = []
    monkeypatch.setattr(runner, "run", lambda *_args, **_kwargs: type("Result", (), {
        "results": [type("Item", (), {"status": "VALID", "record": record, "filename": record.filename})()],
        "discovered": 1,
        "counters": {"VALID": 1, "SKIPPED": 0, "INVALID": 0, "FILTERED": 0},
            "excluded_by_period": 0,
    })())
    monkeypatch.setattr(runner, "check_identity_batch", lambda _records: {"NEW": [record], "EXISTING": [], "CONFLICT": []})
    monkeypatch.setattr(runner, "insert_photos", lambda records: enqueued.append(("registered", records)))
    monkeypatch.setattr(runner, "enqueue_registered_photo", lambda photo_id: enqueued.append(("queued", photo_id)) or 22)
    monkeypatch.setattr(runner, "_ingest_videos", lambda *_args, **_kwargs: {"discovered": 0})

    result = runner.ingest_directory(tmp_path)

    assert enqueued == [("registered", [record]), ("queued", record.photo_id)]
    assert result["registered"] == 1
    assert result["preview"]["queued"] == 1
    assert result["preview"]["enqueue_errors"] == []


def test_directory_ingest_reports_queue_failure_without_undoing_registration(monkeypatch, tmp_path):
    record = _record()
    registered = []
    monkeypatch.setattr(runner, "run", lambda *_args, **_kwargs: type("Result", (), {
        "results": [type("Item", (), {"status": "VALID", "record": record, "filename": record.filename})()],
        "discovered": 1,
        "counters": {"VALID": 1, "SKIPPED": 0, "INVALID": 0, "FILTERED": 0},
            "excluded_by_period": 0,
    })())
    monkeypatch.setattr(runner, "check_identity_batch", lambda _records: {"NEW": [record], "EXISTING": [], "CONFLICT": []})
    monkeypatch.setattr(runner, "insert_photos", lambda records: registered.extend(records))
    monkeypatch.setattr(runner, "enqueue_registered_photo", lambda _photo_id: (_ for _ in ()).throw(RuntimeError("queue unavailable")))
    monkeypatch.setattr(runner, "_ingest_videos", lambda *_args, **_kwargs: {"discovered": 0})

    result = runner.ingest_directory(tmp_path)

    assert registered == [record]
    assert result["registered"] == 1
    assert result["preview"]["queued"] == 0
    assert result["preview"]["enqueue_errors"] == [{"photo_id": record.photo_id, "error": "queue unavailable"}]


def test_directory_ingest_does_not_queue_identity_conflicts(monkeypatch, tmp_path):
    record = _record()
    calls = []
    monkeypatch.setattr(runner, "run", lambda *_args, **_kwargs: type("Result", (), {
        "results": [type("Item", (), {"status": "VALID", "record": record, "filename": record.filename})()],
        "discovered": 1,
        "counters": {"VALID": 1, "SKIPPED": 0, "INVALID": 0, "FILTERED": 0},
            "excluded_by_period": 0,
    })())
    monkeypatch.setattr(runner, "check_identity_batch", lambda _records: {"NEW": [], "EXISTING": [], "CONFLICT": [record]})
    monkeypatch.setattr(runner, "enqueue_registered_photo", lambda photo_id: calls.append(photo_id))
    monkeypatch.setattr(runner, "_ingest_videos", lambda *_args, **_kwargs: {"discovered": 0})

    result = runner.ingest_directory(tmp_path)

    assert calls == []
    assert result["conflicts"] == [record.photo_id]
    assert result["preview"]["queued"] == 0
