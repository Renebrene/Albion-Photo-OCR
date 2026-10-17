from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.jobs import automation


@pytest.fixture
def tick_mocks(monkeypatch):
    create_history = Mock(return_value=501)
    added_job_calls = []

    def record_added_jobs(run_id, job_ids, **kwargs):
        added_job_calls.append((run_id, list(job_ids), kwargs))

    add_jobs = Mock(side_effect=record_added_jobs)
    finish_enqueue = Mock()
    update_run = Mock()
    get_run = Mock(return_value={"counts": {"jobs_total": 0}, "enqueue_complete": False})

    from app.runs import history

    monkeypatch.setattr(history, "create_run", create_history)
    monkeypatch.setattr(history, "add_jobs", add_jobs)
    monkeypatch.setattr(history, "finish_enqueue", finish_enqueue)
    monkeypatch.setattr(history, "update_run", update_run)
    monkeypatch.setattr(history, "get_run", get_run)

    monkeypatch.setattr(automation, "get_settings", lambda: {
        "enabled": True, "interval_minutes": 60, "auto_dino": False,
        "auto_qwen": False, "last_tick": None,
    })
    monkeypatch.setattr(automation, "is_due", lambda _settings: True)
    return SimpleNamespace(
        create_history=create_history,
        add_jobs=add_jobs,
        finish_enqueue=finish_enqueue,
        update_run=update_run,
        get_run=get_run,
        added_job_calls=added_job_calls,
    )


def test_disabled_not_due_and_locked_attempts_do_not_create_history(tick_mocks, monkeypatch):
    mocks = tick_mocks
    monkeypatch.setattr(automation, "get_settings", lambda: {
        "enabled": False, "interval_minutes": 60, "auto_dino": False,
        "auto_qwen": False, "last_tick": None,
    })
    assert automation.run_tick() == {"skipped": "disabled"}

    monkeypatch.setattr(automation, "get_settings", lambda: {
        "enabled": True, "interval_minutes": 60, "auto_dino": False,
        "auto_qwen": False, "last_tick": None,
    })
    monkeypatch.setattr(automation, "is_due", lambda _settings: False)
    assert automation.run_tick() == {"skipped": "not_due"}

    monkeypatch.setattr(automation, "is_due", lambda _settings: True)
    monkeypatch.setattr(automation, "get_connection", lambda: _lock_connection(False))
    assert automation.run_tick() == {"skipped": "locked"}
    mocks.create_history.assert_not_called()


def _lock_connection(locked: bool):
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _query, _params=None):
            return None

        def fetchone(self):
            return (locked,)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return Cursor()

    return Connection()


def test_real_empty_tick_creates_and_finishes_one_scheduler_run(tick_mocks, monkeypatch):
    mocks = tick_mocks
    monkeypatch.setattr(automation, "get_connection", lambda: _settings_update_connection(locked=True))

    result = automation.run_tick()

    assert result == {"dino_batch_id": None, "qwen_jobs": 0}
    mocks.create_history.assert_called_once_with(
        kind="scheduler", mode="schedule", title="Тик планировщика",
        status="RUNNING", started=True,
    )
    mocks.finish_enqueue.assert_called_once_with(501, total=0)


def test_tick_links_dino_and_qwen_jobs_to_same_history(tick_mocks, monkeypatch):
    mocks = tick_mocks
    monkeypatch.setattr(automation.dino_db, "has_active_batch", lambda: False)
    monkeypatch.setattr(automation, "_photos_without_dino", lambda: 2)
    monkeypatch.setattr(automation.dino_db, "create_batch", lambda *_: SimpleNamespace(
        batch_id=44, total_count=2,
    ))
    generic_enqueue = Mock(return_value=601)
    monkeypatch.setattr(automation.jobs_db, "enqueue", generic_enqueue)
    monkeypatch.setattr(automation, "_photos_without_qwen", lambda: ["PH_1", "PH_2"])
    qwen_enqueue = Mock(side_effect=[602, 603])
    monkeypatch.setattr(automation.jobs_db, "enqueue_qwen", qwen_enqueue)
    monkeypatch.setattr(automation, "get_connection", lambda: _settings_update_connection())

    result = automation._run_tick_locked({"auto_dino": True, "auto_qwen": True}, history_id=501)

    assert result == {"dino_batch_id": 44, "dino_total": 2, "qwen_jobs": 2}
    generic_enqueue.assert_called_once_with(
        "DINO_BATCH", {"batch_id": 44}, run_history_id=501,
    )
    assert [call.kwargs["run_history_id"] for call in qwen_enqueue.call_args_list] == [501, 501]
    assert mocks.added_job_calls == [
        (501, [601], {}),
        (501, [602], {}),
        (501, [603], {}),
    ]
    mocks.finish_enqueue.assert_called_once_with(501, total=4)


def _settings_update_connection(*, locked: bool = True):
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, *_args):
            return None

        def fetchone(self):
            return (locked,)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return Cursor()

    return Connection()


def test_active_dino_batch_counts_held_work_as_target(tick_mocks, monkeypatch):
    mocks = tick_mocks
    monkeypatch.setattr(automation.dino_db, "has_active_batch", lambda: True)
    monkeypatch.setattr(automation, "_photos_without_dino", lambda: 3)
    monkeypatch.setattr(automation, "_photos_without_qwen", lambda: [])
    monkeypatch.setattr(automation, "get_connection", lambda: _settings_update_connection())

    result = automation._run_tick_locked({"auto_dino": True, "auto_qwen": False}, history_id=501)

    assert result == {"dino_batch_id": None, "qwen_jobs": 0}
    mocks.finish_enqueue.assert_called_once_with(501, total=3)
    assert mocks.update_run.call_args.kwargs["counts_delta"] == {"skipped": 3}


def test_scheduler_partial_enqueue_failure_finalizes_history_and_reraises(tick_mocks, monkeypatch):
    mocks = tick_mocks
    monkeypatch.setattr(automation, "get_settings", lambda: {
        "enabled": True, "interval_minutes": 60, "auto_dino": False,
        "auto_qwen": True, "last_tick": None,
    })
    mocks.get_run.return_value = {
        "counts": {"jobs_total": 1}, "enqueue_complete": False,
    }
    monkeypatch.setattr(automation, "get_connection", lambda: _settings_update_connection(locked=True))
    monkeypatch.setattr(automation.dino_db, "has_active_batch", lambda: False)
    monkeypatch.setattr(automation, "_photos_without_dino", lambda: 0)
    monkeypatch.setattr(automation, "_photos_without_qwen", lambda: ["PH_1", "PH_2"])
    qwen_enqueue = Mock(side_effect=[701, RuntimeError("queue unavailable")])
    monkeypatch.setattr(automation.jobs_db, "enqueue_qwen", qwen_enqueue)

    with pytest.raises(RuntimeError, match="queue unavailable"):
        automation.run_tick()

    assert mocks.added_job_calls == [(501, [701], {})]
    mocks.update_run.assert_called_once()
    assert mocks.update_run.call_args.kwargs["status"] is None
    assert mocks.update_run.call_args.kwargs["finished"] is False
    assert mocks.update_run.call_args.kwargs["error_count_delta"] == 1
