"""HYBRID creation and queue/history linkage share one transaction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.hybrid import database as hybrid_db


class _Cursor:
    def __init__(self):
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, _params=None):
        self.sql = " ".join(str(sql).split())

    def fetchone(self):
        if "INSERT INTO public.run_history" in self.sql:
            return (902,)
        if "INSERT INTO public.run_history_jobs" in self.sql:
            return (902,)
        return (1,)


class _Connection:
    def __init__(self):
        self.exception = None
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.exception = exc
        self.committed = exc_type is None
        return False

    def cursor(self):
        return _Cursor()


def test_create_and_enqueue_links_job_before_commit(monkeypatch):
    connection = _Connection()
    run = SimpleNamespace(
        hybrid_run_id=31,
        dino_batch_id=12,
        status="PENDING",
        total_count=4,
        completed_count=0,
        failed_count=0,
    )
    calls = []

    monkeypatch.setattr(hybrid_db, "get_connection", lambda: connection)
    monkeypatch.setattr(hybrid_db, "_create_run_in_transaction", lambda cur, batch_id: run)
    monkeypatch.setattr(
        "app.jobs.database.enqueue_in_transaction",
        lambda cur, job_type, payload, *, run_history_id=None: (
            calls.append(("enqueue", job_type, payload, run_history_id)) or 74
        ),
    )
    monkeypatch.setattr(
        "app.runs.history.link_job_in_transaction",
        lambda cur, run_id, job_id: calls.append(("link", run_id, job_id)) or True,
    )
    monkeypatch.setattr(
        "app.runs.history.set_sort_stage_in_transaction",
        lambda cur, run_id, stage, **kwargs: calls.append(("stage", run_id, stage, kwargs)),
    )

    result = hybrid_db.create_and_enqueue_run(12, run_history_id=901)

    assert result == (run, 74, None)
    assert calls == [
        ("enqueue", "HYBRID_RUN", {"hybrid_run_id": 31}, 901),
        ("link", 901, 74),
        (
            "stage", 901, "HYBRID",
            {"status": "RUNNING", "total": 4, "required": True},
        ),
    ]
    assert connection.committed is True


def test_manual_hybrid_history_and_job_are_created_atomically(monkeypatch):
    from app.runs import history

    connection = _Connection()
    run = SimpleNamespace(
        hybrid_run_id=41,
        dino_batch_id=14,
        status="PENDING",
        total_count=2,
        completed_count=0,
        failed_count=0,
    )
    calls = []

    monkeypatch.setattr(hybrid_db, "get_connection", lambda: connection)
    monkeypatch.setattr(hybrid_db, "_create_run_in_transaction", lambda cur, batch_id: run)
    monkeypatch.setattr(history, "available", lambda: True)
    monkeypatch.setattr(
        history,
        "create_run_in_transaction",
        lambda cur, **kwargs: calls.append(("history", kwargs)) or 902,
    )
    monkeypatch.setattr(
        "app.jobs.database.enqueue_in_transaction",
        lambda cur, job_type, payload, *, run_history_id=None: (
            calls.append(("enqueue", job_type, payload, run_history_id)) or 75
        ),
    )
    monkeypatch.setattr(
        history,
        "link_job_in_transaction",
        lambda cur, run_id, job_id: calls.append(("link", run_id, job_id)) or True,
    )
    monkeypatch.setattr(
        history,
        "set_sort_stage_in_transaction",
        lambda cur, run_id, stage, **kwargs: calls.append(("stage", run_id, stage, kwargs)),
    )
    monkeypatch.setattr(history, "append_log", lambda *_args: None)
    monkeypatch.setattr(
        history,
        "finish_enqueue_in_transaction",
        lambda _cur, run_id, **kwargs: (
            calls.append(("finish", run_id, kwargs))
            or {"total": kwargs["total"], "jobs_total": 1}
        ),
    )

    result = hybrid_db.create_and_enqueue_run(
        14,
        history_spec={"mode": "manual", "title_prefix": "HYBRID run"},
    )

    assert result == (run, 75, 902)
    assert calls[0][0] == "history"
    assert calls[1] == ("enqueue", "HYBRID_RUN", {"hybrid_run_id": 41}, 902)
    assert calls[2] == ("link", 902, 75)
    assert calls[3][0] == "stage"
    assert calls[4][0] == "finish"
    assert connection.committed is True


def test_enqueue_failure_rolls_back_the_hybrid_row(monkeypatch):
    connection = _Connection()
    run = SimpleNamespace(
        hybrid_run_id=32,
        dino_batch_id=13,
        status="PENDING",
        total_count=1,
        completed_count=0,
        failed_count=0,
    )
    monkeypatch.setattr(hybrid_db, "get_connection", lambda: connection)
    monkeypatch.setattr(hybrid_db, "_create_run_in_transaction", lambda cur, batch_id: run)
    monkeypatch.setattr(
        "app.jobs.database.enqueue_in_transaction",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("queue down")),
    )

    with pytest.raises(RuntimeError, match="queue down"):
        hybrid_db.create_and_enqueue_run(13, run_history_id=902)

    assert connection.committed is False
    assert isinstance(connection.exception, RuntimeError)
