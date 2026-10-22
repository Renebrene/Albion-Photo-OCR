"""Pure helpers of the retention scripts (no PostgreSQL writes)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.billboard import pipeline as billboard_pipeline


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_job_cleanup_eligibility_never_touches_active_rows():
    module = _load("cleanup_job_queue", "scripts/cleanup_job_queue.py")

    sql, params = module._eligibility(14, 30, None)

    assert "j.status IN ('DONE', 'FAILED', 'CANCELLED')" in sql
    assert "PENDING" not in sql and "RUNNING" not in sql
    assert params == [14, 30]


def test_job_cleanup_archive_batch_keeps_compact_fields():
    module = _load("cleanup_job_queue", "scripts/cleanup_job_queue.py")

    class Cursor:
        def __init__(self):
            self.sql = ""
            self.params = []

        def execute(self, sql, params):
            self.sql = sql
            self.params = list(params)

        def fetchall(self):
            return [(1,), (2,), (3,)]

    cur = Cursor()
    deleted = module._delete_batch(
        cur,
        done_days=14,
        failed_days=30,
        types=None,
        limit=100,
        archive=True,
    )

    assert deleted == 3
    assert "INSERT INTO public.job_queue_archive" in cur.sql
    assert "DELETE FROM public.job_queue" in cur.sql
    assert "payload_photo_id" in cur.sql
    assert cur.params[-1] == 100


def test_crop_eligibility_done_immediately_others_by_age(tmp_path):
    module = _load("cleanup_crops", "scripts/cleanup_crops.py")
    directory = tmp_path / "PH_test"
    directory.mkdir()
    (directory / "crop_01.jpg").write_bytes(b"jpeg")

    mtime = directory.stat().st_mtime
    assert module._eligible("DONE", directory, 0) is True
    assert module._eligible("FAILED", directory, mtime - 1) is False
    assert module._eligible("FAILED", directory, mtime + 1) is True


def test_crop_removal_respects_dry_run_and_limit(tmp_path, monkeypatch):
    module = _load("cleanup_crops", "scripts/cleanup_crops.py")
    root = tmp_path / "crops"
    directory = root / "PH_test"
    directory.mkdir(parents=True)
    first = directory / "crop_01.jpg"
    second = directory / "crop_02.jpg"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    (directory / billboard_pipeline.CROPS_MARKER).write_text("{}")

    monkeypatch.setattr(billboard_pipeline, "CROPS_ROOT", root)

    dry = module._remove_files(
        [first, second], dry_run=True, max_delete=10
    )
    assert dry == {
        "files": 2, "bytes": 6, "missing": 0, "failed": 0, "limited": False,
    }
    assert first.exists() and second.exists()

    real = module._remove_files(
        [first, second], dry_run=False, max_delete=1
    )
    assert real["files"] == 1
    assert real["limited"] is True
    assert first.exists() is False
    assert second.exists() is True
    assert (directory / billboard_pipeline.CROPS_MARKER).exists()
