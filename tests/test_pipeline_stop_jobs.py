"""
Stopping a pipeline run also pauses its queued child jobs.

Pure tests: a fake connection captures the SQL, and the supervisor stop path
is driven with stubbed helpers.
"""

from __future__ import annotations

from contextlib import contextmanager

from app.jobs import database as jobs_db
from app.supervisor import runs


def _fake_connection(monkeypatch, captured, rowcount=7):
    class Cursor:
        def execute(self, sql, params=None):
            captured["sql"] = " ".join(sql.split())
            captured["params"] = params
            self.rowcount = rowcount

        def fetchone(self):
            return (rowcount,)

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
    def fake():
        yield Connection()

    monkeypatch.setattr(jobs_db, "get_connection", fake)


def test_pause_pending_pipeline_jobs(monkeypatch):
    captured = {}
    _fake_connection(monkeypatch, captured)

    paused = jobs_db.pause_pending_for_pipeline(42, "2026-10-24 00:14:05")

    assert paused == 7
    assert "status = 'PAUSED'" in captured["sql"]
    assert "paused_by_pipeline_run" in captured["sql"]
    assert "job_type = ANY" in captured["sql"]
    assert captured["params"][0] == 42
    assert "INGEST_DIR" in captured["params"][1]
    assert "PHOTO_PREVIEW" in captured["params"][1]
    assert captured["params"][2] == "2026-10-24 00:14:05"


def test_resume_returns_only_jobs_of_this_run(monkeypatch):
    captured = {}
    _fake_connection(monkeypatch, captured)

    resumed = jobs_db.resume_paused_for_pipeline(42)

    assert resumed == 7
    assert "status = 'PENDING'" in captured["sql"]
    assert "payload ->> 'paused_by_pipeline_run'" in captured["sql"]
    assert captured["params"] == ("42",)


def test_supervisor_stop_pauses_jobs_and_reports_count(monkeypatch):
    run = {
        "run_id": 42,
        "status": "RUNNING",
        "stage": "PREVIEW",
        "stop_requested": True,
        "started_at": "2026-10-24 00:14:05",
        "created_at": "2026-10-24 00:14:05",
        "manifest": {},
    }
    calls = {}

    monkeypatch.setattr(runs, "get_run", lambda _run_id: run)
    monkeypatch.setattr(
        runs.jobs_db,
        "pause_pending_for_pipeline",
        lambda run_id, since: calls.update(run_id=run_id, since=since) or 123,
    )
    monkeypatch.setattr(
        runs,
        "_finish_run",
        lambda run_id, status, message=None: calls.update(
            finished=(run_id, status, message)
        ),
    )

    outcome = runs._advance(42)  # noqa: SLF001

    assert outcome == {"outcome": "STOPPED"}
    assert calls["run_id"] == 42
    assert calls["since"] == "2026-10-24 00:14:05"
    assert calls["finished"][1] == "STOPPED"
    assert "123" in calls["finished"][2]
