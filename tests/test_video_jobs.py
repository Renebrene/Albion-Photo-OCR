from __future__ import annotations

import pytest

from app.jobs import database as jobs_db
from app.jobs import worker
from app.video import transcode


def test_video_job_types_are_allowed():
    assert {"VIDEO_TRANSCODE", "VIDEO_TRIM", "VIDEO_STORYBOARD"} <= jobs_db.JOB_TYPES


def test_worker_dispatches_transcode_only_and_persists_derivative_result(monkeypatch):
    from app.api import video_repository

    progress = []
    updated = []
    monkeypatch.setattr(worker, "job_control", lambda _job_id: lambda *args: progress.append(args))
    monkeypatch.setattr(
        transcode,
        "run_transcode",
        lambda **kwargs: {"video_id": kwargs["video_id"], "status": "DONE", "profile": kwargs["profile"]},
    )
    monkeypatch.setattr(video_repository, "update_derivative", lambda *args, **kwargs: updated.append((args, kwargs)))
    monkeypatch.setattr(video_repository, "register_completed_derivative", lambda _id: "VI_" + "cd" * 12)
    monkeypatch.setattr(video_repository, "registered_asset_source", lambda _id: {"source_path": "/tmp/copy.mp4", "duration_seconds": 1.0})
    from app.preview import video as preview_video
    monkeypatch.setattr(preview_video, "build_video_poster", lambda *_args, **_kwargs: None)

    result = worker._execute({
        "id": 10,
        "job_type": "VIDEO_TRANSCODE",
        "payload": {
            "video_id": "VI_" + "12" * 12,
            "derivative_id": 7,
            "profile": "strong_720p",
            "source_sha256": "ab" * 32,
        },
    })

    assert result["status"] == "DONE"
    assert result["profile"] == "strong_720p"
    assert result["asset_video_id"] == "VI_" + "cd" * 12
    assert updated == []  # run_transcode records DONE atomically after validation


def test_worker_marks_derivative_cancelled_when_ffmpeg_job_is_cancelled(monkeypatch):
    from app.api import video_repository

    updated = []
    monkeypatch.setattr(worker, "job_control", lambda _job_id: lambda *_args: None)
    monkeypatch.setattr(
        transcode,
        "run_transcode",
        lambda **_kwargs: (_ for _ in ()).throw(transcode.VideoTranscodeCancelled("cancelled")),
    )
    monkeypatch.setattr(video_repository, "update_derivative", lambda *args, **kwargs: updated.append((args, kwargs)))

    with pytest.raises(worker.JobCancelled):
        worker._execute({
            "id": 11,
            "job_type": "VIDEO_TRANSCODE",
            "payload": {
                "video_id": "VI_" + "34" * 12,
                "derivative_id": 9,
                "profile": "standard_1080p",
                "source_sha256": "cd" * 32,
            },
        })

    assert updated[-1][1]["status"] == "CANCELLED"


def test_video_worker_requeues_only_video_jobs(monkeypatch):
    from contextlib import contextmanager

    from app.jobs import worker
    from app.ingest import database as ingest_db

    calls = []
    monkeypatch.setattr(worker.jobs, "requeue_stale", lambda **kwargs: calls.append(kwargs) or 2)

    class Cursor:
        def execute(self, sql):
            calls.append(sql)

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

    monkeypatch.setattr(ingest_db, "get_connection", fake_connection)
    result = worker._requeue_stale_jobs(30, video_only=True)

    assert result == {"jobs": 2}
    assert calls[0] == {"older_than_minutes": 30, "types": ["VIDEO_TRANSCODE", "VIDEO_TRIM", "VIDEO_STORYBOARD"]}
    assert "VIDEO_TRIM" in calls[1]


def test_auto_mode_uses_single_nvenc_or_half_cpu_workers(monkeypatch):
    monkeypatch.setenv("SCENE_VIDEO_ENCODER", "auto")
    monkeypatch.delenv("SCENE_VIDEO_TRANSCODE_WORKERS", raising=False)
    monkeypatch.setattr(transcode, "nvenc_available", lambda: True)
    assert transcode.choose_worker_mode(cpu_count=12) == ("h264_nvenc", 1)

    monkeypatch.setattr(transcode, "nvenc_available", lambda: False)
    assert transcode.choose_worker_mode(cpu_count=12) == ("libx264", 6)


def test_video_worker_watch_mode_uses_dedicated_loop_with_one_worker(monkeypatch):
    import sys

    from app.jobs import worker

    monkeypatch.setattr(sys, "argv", ["worker", "--watch", "--only", "VIDEO_TRANSCODE", "--parallel", "0"])
    monkeypatch.setattr(transcode, "choose_worker_mode", lambda: ("libx264", 1))
    monkeypatch.setattr(worker.os, "cpu_count", lambda: 12)
    called = []
    monkeypatch.setattr(worker, "_video_worker", lambda *args: called.append(args))

    worker.main()

    assert called == [(["VIDEO_TRANSCODE"], 3.0, 12, "1/1", None, None)]


def test_explicit_single_video_worker_limits_cpu_threads(monkeypatch):
    import sys

    from app.jobs import worker

    monkeypatch.setattr(sys, "argv", ["worker", "--watch", "--only", "VIDEO_TRANSCODE", "--parallel", "1"])
    monkeypatch.setattr(transcode, "choose_worker_mode", lambda: ("libx264", 6))
    monkeypatch.setattr(worker.os, "cpu_count", lambda: 12)
    called = []
    monkeypatch.setattr(worker, "_video_worker", lambda *args: called.append(args))

    worker.main()

    assert called == [(["VIDEO_TRANSCODE"], 3.0, 12, "1/1", None, None)]


def test_video_worker_stale_recovery_resets_derivative_without_ml_imports(monkeypatch):
    import builtins
    from contextlib import contextmanager

    from app.jobs import worker

    monkeypatch.setattr(worker, "jobs", type("Jobs", (), {
        "requeue_stale": staticmethod(lambda *, older_than_minutes, types: 3 if types == ["VIDEO_TRANSCODE", "VIDEO_TRIM", "VIDEO_STORYBOARD"] else 0),
    }))
    statements = []

    class Cursor:
        def execute(self, sql):
            statements.append(sql)

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

    from app.ingest import database as ingest_database

    monkeypatch.setattr(ingest_database, "get_connection", fake_connection)
    original_import = builtins.__import__
    attempted_ml_imports = []

    def guarded_import(name, *args, **kwargs):
        if name in {"app.dino", "app.hybrid"}:
            attempted_ml_imports.append(name)
            raise AssertionError(f"unexpected ML import: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    result = worker._requeue_stale_jobs(30, video_only=True)

    assert result == {"jobs": 3}
    assert attempted_ml_imports == []
    assert "SET status='PENDING'" in statements[0]
    assert "j.status='PENDING'" in statements[0]
    assert "d.status='RUNNING'" in statements[0]
