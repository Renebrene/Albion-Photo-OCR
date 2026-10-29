"""
Политика повторов описаний (решение владельца, 29.10.2026):

* сбойное фото не исключается навсегда — следующий запуск его повторяет;
* исключение и пропуск — только вручную;
* таймаут ответа модели короче, чтобы сбой не держал очередь.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest


class _Cursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.queries: list[tuple[str, object]] = []

    def execute(self, sql, params=None):
        self.queries.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return (0,)

    def rowcount(self):
        return 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _patch(monkeypatch, module, cursor):
    @contextmanager
    def fake():
        yield type("Conn", (), {"cursor": lambda _self: cursor})()

    monkeypatch.setattr(module, "get_connection", fake)
    return cursor


# ---- выбор фото для описания ----


def test_pipeline_retries_photos_that_failed(monkeypatch):
    """Строка FAILED не исключает фото из следующего прогона."""

    from app.supervisor import runs as supervisor

    cursor = _patch(monkeypatch, supervisor, _Cursor(rows=[]))

    supervisor._photos_without_qwen(None)

    sql, _params = cursor.queries[0]
    assert "q.status IN ('DONE', 'RUNNING')" in sql
    # Фото с ошибкой в условии исключения нет.
    assert "q.status = 'FAILED'" not in sql


def test_period_scan_retries_photos_that_failed(monkeypatch):
    from app.qwen import database as qwen_db

    cursor = _patch(monkeypatch, qwen_db, _Cursor(rows=[]))

    qwen_db.photo_ids_missing_in_period(
        date_from="2026-10-01", date_to="2026-10-02"
    )

    sql, _params = cursor.queries[0]
    assert "q.status = 'DONE'" in sql


# ---- зависшие задания ----


def test_stale_jobs_are_requeued_without_a_limit(monkeypatch):
    """
    По умолчанию лимита попыток нет: задание возвращается в очередь, а не
    закрывается как пропущенное (исключение — только вручную).
    """

    from app.jobs import database as jobs_db

    monkeypatch.setattr(jobs_db, "STALE_MAX_ATTEMPTS", 0)
    cursor = _patch(monkeypatch, jobs_db, _Cursor())

    jobs_db.requeue_stale(older_than_minutes=30, types=["QWEN_PHOTO"])

    # Один запрос — возврат в очередь; закрытия по числу попыток нет.
    assert len(cursor.queries) == 1

    sql, params = cursor.queries[0]
    assert "status = 'PENDING'" in sql
    assert "attempts <" not in sql
    assert params == ["30", ["QWEN_PHOTO"]]


def test_a_limit_restores_the_auto_skip(monkeypatch):
    from app.jobs import database as jobs_db

    monkeypatch.setattr(jobs_db, "STALE_MAX_ATTEMPTS", 3)
    cursor = _patch(monkeypatch, jobs_db, _Cursor())

    jobs_db.requeue_stale(older_than_minutes=10)

    assert len(cursor.queries) == 2

    failed_sql, failed_params = cursor.queries[0]
    assert "status = 'FAILED'" in failed_sql
    assert failed_params[1] == "3"

    requeue_sql, requeue_params = cursor.queries[1]
    assert "attempts <" in requeue_sql
    assert requeue_params[1] == "3"


# ---- таймаут модели ----


def test_the_default_timeout_is_two_minutes(monkeypatch):
    """
    Медиана ответа 2,6 с, p90 3,2 с: 120 с — с большим запасом, но зависший
    запрос больше не держит очередь пять минут.
    """

    monkeypatch.delenv("QWEN_TIMEOUT", raising=False)

    import importlib

    from app.qwen import config as qwen_config

    reloaded = importlib.reload(qwen_config)

    assert reloaded.QWEN_TIMEOUT == 120

    monkeypatch.setenv("QWEN_TIMEOUT", "300")
    assert importlib.reload(qwen_config).QWEN_TIMEOUT == 300

    monkeypatch.delenv("QWEN_TIMEOUT", raising=False)
    importlib.reload(qwen_config)
