"""
Панель запуска описания: адреса, пауза/продолжить, зависшие задания,
оценка остатка и жёсткий сброс.

БД подменяется: проверяются условия фильтра, состояние очереди и состав
удаляемых таблиц, а не живая база. Реальный сброс в тестах недопустим.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import repository, routes
from app.api.main import app
from app.jobs import database as jobs_db
from app.qwen import database as qwen_db

client = TestClient(app, raise_server_exceptions=False)


class _Cursor:
    def __init__(self, *, rows=None, rowcount=0, one=None):
        self._rows = rows or []
        self.rowcount = rowcount
        self._one = one
        self.statements: list[tuple[str, object]] = []

    def execute(self, sql, params=None):
        self.statements.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._one

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch(monkeypatch, module, cursor):
    monkeypatch.setattr(module, "get_connection", lambda: _Connection(cursor))
    return cursor


def test_period_filter_passes_address_ids(monkeypatch):
    cursor = _Cursor(rows=[("PH_" + "a" * 24,)])
    _patch(monkeypatch, qwen_db, cursor)

    ids = qwen_db.photo_ids_in_period(
        date_from="2026-11-01",
        date_to="2026-11-21",
        date_mode="capture",
        address_ids=[196, 5, 196],
    )

    assert ids == ["PH_" + "a" * 24]
    sql, params = cursor.statements[-1]
    assert "photo_address_overrides" in sql
    assert "ANY(%s)" in sql
    # Адреса нормализуются: без дублей и отсортированы.
    assert params[2] == [5, 196]


def test_period_filter_without_addresses_has_no_address_clause(monkeypatch):
    cursor = _Cursor()
    _patch(monkeypatch, qwen_db, cursor)

    qwen_db.photo_ids_in_period(date_from="2026-11-01", date_to="2026-11-21")

    sql, params = cursor.statements[-1]
    assert "photo_address_overrides" not in sql
    assert params == ["2026-11-01", "2026-11-21"]


def test_pause_and_resume_touch_only_waiting_jobs(monkeypatch):
    cursor = _Cursor(rowcount=7)
    _patch(monkeypatch, jobs_db, cursor)

    assert jobs_db.pause_jobs("QWEN_PHOTO") == 7
    sql, params = cursor.statements[-1]
    assert "status = 'PENDING'" in sql
    assert params == ("QWEN_PHOTO",)

    assert jobs_db.resume_jobs("QWEN_PHOTO") == 7
    sql, _ = cursor.statements[-1]
    assert "status = 'PAUSED'" in sql
    assert "SET status = 'PENDING'" in sql


def test_stale_cleanup_cancels_old_running_jobs(monkeypatch):
    cursor = _Cursor(rows=[(11,), (12,)])
    _patch(monkeypatch, jobs_db, cursor)

    ids = jobs_db.cancel_stale_jobs("QWEN_PHOTO", older_than_minutes=45)

    assert ids == [11, 12]
    sql, params = cursor.statements[-1]
    assert "status = 'CANCELLED'" in sql
    assert params == ("QWEN_PHOTO", "45")


def test_reset_all_deletes_results_and_clears_regions(monkeypatch):
    cursor = _Cursor(rowcount=3, one=("public.photo_qwen",))
    _patch(monkeypatch, qwen_db, cursor)

    deleted = qwen_db.reset_all()

    tables = [
        params[0]
        for sql, params in cursor.statements
        if sql.startswith("SELECT to_regclass")
    ]
    assert "public.photo_qwen" in tables
    assert "public.photo_qwen_history" in tables
    assert "public.photo_qwen_archive" in tables
    assert "public.photo_qwen_history_archive" in tables

    deleted_sql = [
        sql for sql, _ in cursor.statements if sql.startswith("DELETE FROM")
    ]
    assert len(deleted_sql) == 4
    assert any("UPDATE public.photo_regions" in sql for sql, _ in cursor.statements)
    assert deleted["photo_qwen"] == 3


def test_reset_requires_confirmation():
    response = client.post("/api/v1/qwen/reset", json={"confirm": False})

    assert response.status_code == 422
    assert "confirm" in response.json()["detail"]


def test_pause_endpoint_reports_count(monkeypatch):
    monkeypatch.setattr(jobs_db, "pause_jobs", lambda job_type: 4)

    response = client.post("/api/v1/jobs/qwen/pause")

    assert response.status_code == 200
    assert response.json() == {"paused": 4}


def test_resume_endpoint_reports_count(monkeypatch):
    monkeypatch.setattr(jobs_db, "resume_jobs", lambda job_type: 3)

    response = client.post("/api/v1/jobs/qwen/resume")

    assert response.status_code == 200
    assert response.json() == {"resumed": 3}


def test_stuck_endpoint_cancels_and_returns_ids(monkeypatch):
    seen = {}

    def fake(job_type, *, older_than_minutes):
        seen["job_type"] = job_type
        seen["minutes"] = older_than_minutes
        return [21, 22]

    monkeypatch.setattr(jobs_db, "cancel_stale_jobs", fake)

    response = client.post("/api/v1/jobs/qwen/stuck?older_than_minutes=40")

    assert response.status_code == 200
    assert response.json()["cancelled"] == 2
    assert response.json()["job_ids"] == [21, 22]
    assert seen == {"job_type": "QWEN_PHOTO", "minutes": 40}


def test_preview_endpoint_counts_selection(monkeypatch):
    monkeypatch.setattr(
        qwen_db,
        "photo_ids_in_period",
        lambda **kwargs: ["a", "b", "c"],
    )
    monkeypatch.setattr(
        qwen_db,
        "photo_ids_missing_in_period",
        lambda **kwargs: ["c"],
    )

    response = client.post(
        "/api/v1/jobs/qwen/preview",
        json={
            "date_from": "2026-11-01",
            "date_to": "2026-11-21",
            "date_mode": "capture",
            "address_ids": [196],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["photos"] == 3
    assert body["missing"] == 1
    assert body["described"] == 2
    assert body["addresses"] == 1


def test_addresses_endpoint_lists_hybrid_choices(monkeypatch):
    monkeypatch.setattr(
        repository,
        "qwen_address_choices",
        lambda: [{"address_id": 196, "name": "Нагибина 19 А", "photos": 1606}],
    )

    response = client.get("/api/v1/qwen/addresses")

    assert response.status_code == 200
    assert response.json()["items"][0]["address_id"] == 196


def test_stats_include_timeline(monkeypatch):
    monkeypatch.setattr(repository, "qwen_stats", lambda: {"photos": 1})
    monkeypatch.setattr(repository, "qwen_queue_counts", lambda: {"PENDING": 2})
    monkeypatch.setattr(
        repository,
        "qwen_run_timeline",
        lambda: {"started_at": None, "eta_seconds": 120, "stuck": 0},
    )
    monkeypatch.setattr(
        repository, "photo_ids_with_qwen_status", lambda status: []
    )

    response = client.get("/api/v1/qwen/stats")

    assert response.status_code == 200
    assert response.json()["timeline"]["eta_seconds"] == 120
