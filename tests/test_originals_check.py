"""
Полная проверка оригиналов: обход корпуса, отчёт и постановка задания.

База подменяется: проверяются счётчики по причинам, атомарная запись отчёта,
чтение последнего отчёта и маршруты. Настоящий обход 57 тыс. файлов здесь не
нужен и не должен случаться в тестах.
"""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.api.main import app
from app.jobs import database as jobs_db
from app.originals import check

client = TestClient(app, raise_server_exceptions=False)

LIVE = "PH_" + "a" * 24
GONE = "PH_" + "b" * 24
OUTSIDE = "PH_" + "c" * 24
DEAD = "PH_" + "d" * 24


def _fake_rows(monkeypatch, pages):
    """Подменяет соединение: каждая страница — свой ответ fetchall()."""

    class Cursor:
        def execute(self, sql, params=()):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return pages.pop(0) if pages else []

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

    monkeypatch.setattr(check, "get_connection", fake)


def _roots(tmp_path):
    live = tmp_path / "TEST"
    live.mkdir()
    (live / "a.jpg").write_bytes(b"jpeg")

    dead = tmp_path / "Win10"  # том отмонтирован
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "x.jpg").write_bytes(b"jpeg")

    return live, dead, outside


def test_scan_counts_every_reason_separately(tmp_path, monkeypatch):
    live, dead, outside = _roots(tmp_path)

    _fake_rows(
        monkeypatch,
        [
            [
                (LIVE, str(live / "a.jpg")),
                (GONE, str(live / "gone.jpg")),
                (OUTSIDE, str(outside / "x.jpg")),
                (DEAD, str(dead / "x.jpg")),
            ],
            [],
        ],
    )

    report = check.scan([live, dead])

    assert report["checked"] == 4
    assert report["available"] == 1
    assert report["missing"] == 1
    assert report["outside_roots"] == 1
    assert report["root_unavailable"] == 1
    assert [entry["available"] for entry in report["roots"]] == [True, False]
    assert len(report["samples"]) == 3


def test_scan_reports_progress_and_stops_on_a_full_pass(tmp_path, monkeypatch):
    live, _dead, _outside = _roots(tmp_path)
    _fake_rows(monkeypatch, [[(LIVE, str(live / "a.jpg"))], []])

    seen = []

    class Cursor:
        def execute(self, sql, params=()):
            pass

        def fetchone(self):
            return (1,)

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

    monkeypatch.setattr(check, "get_connection", fake)
    # _total() идёт первым, дальше — страницы обхода.
    original_rows = check._rows
    monkeypatch.setattr(
        check,
        "_rows",
        lambda photo_ids, limit: iter([(LIVE, str(live / "a.jpg"))]),
    )

    report = check.scan([live], progress=lambda done, total, stage: seen.append((done, total, stage)))

    assert report["checked"] == 1
    assert seen == [(1, 1, "проверка оригиналов")]
    monkeypatch.setattr(check, "_rows", original_rows)


def test_report_is_written_atomically_and_read_back(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_DATA", str(tmp_path))

    report = {"checked": 4, "available": 1, "missing": 3, "samples": []}
    path = check.write_report(report)

    assert path.parent == tmp_path / "reports"
    assert path.name.startswith("originals_health_")
    assert not list(path.parent.glob("*.tmp"))

    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["checked"] == 4
    assert stored["generated_at"]

    latest = check.latest_report()
    assert latest["checked"] == 4


def test_latest_report_is_none_before_the_first_check(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_DATA", str(tmp_path))

    assert check.latest_report() is None


def test_run_refuses_without_configured_roots(monkeypatch):
    monkeypatch.setattr("app.api.config.ORIGINALS_ROOTS", [])

    with pytest.raises(ValueError):
        check.run()


def test_run_scans_and_keeps_the_report(tmp_path, monkeypatch):
    live, _dead, _outside = _roots(tmp_path)
    monkeypatch.setenv("SCENE_DATA", str(tmp_path))
    monkeypatch.setattr("app.api.config.ORIGINALS_ROOTS", [live])

    scanned = []

    def fake_scan(roots, **kwargs):
        scanned.append(list(roots))
        return {"checked": 1, "available": 1, "missing": 0, "outside_roots": 0,
                "root_unavailable": 0, "roots": [], "samples": []}

    monkeypatch.setattr(check, "scan", fake_scan)

    result = check.run()

    assert scanned == [[live]]
    assert result["report"].startswith(str(tmp_path / "reports"))
    assert check.latest_report()["checked"] == 1


def test_enqueue_does_not_create_a_second_check(monkeypatch):
    """Пока проверка в очереди или идёт, вторая не ставится."""

    import app.originals.check  # noqa: F401  (импорт нужен для маршрутов)

    class Cursor:
        def execute(self, sql, params=()):
            assert "ORIGINALS_CHECK" in sql

        def fetchone(self):
            return None

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

    assert jobs_db.enqueue_originals_check() is None


def test_enqueue_returns_the_active_check(monkeypatch):
    """Проверка уже идёт — возвращаем её id, чтобы кнопка показала прогресс."""

    answers = iter([None, (77,)])

    class Cursor:
        def execute(self, sql, params=()):
            self.sql = sql

        def fetchone(self):
            return next(answers)

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

    assert jobs_db.enqueue_originals_check() == 77


def test_route_queues_the_check(tmp_path, monkeypatch):
    live, _dead, _outside = _roots(tmp_path)
    monkeypatch.setattr(routes, "ORIGINALS_ROOTS", [live])
    monkeypatch.setattr(jobs_db, "enqueue_originals_check", lambda: 42)

    response = client.post("/api/v1/originals/check")

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == 42
    assert body["report_dir"].endswith("reports")


def test_route_refuses_without_configured_roots(monkeypatch):
    monkeypatch.setattr(routes, "ORIGINALS_ROOTS", [])

    response = client.post("/api/v1/originals/check")

    assert response.status_code == 503


def test_route_returns_the_latest_report(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_DATA", str(tmp_path))
    check.write_report({"checked": 7, "available": 5, "missing": 2})

    body = client.get("/api/v1/originals/check/latest").json()

    assert body["report"]["checked"] == 7


def test_route_returns_none_without_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_DATA", str(tmp_path))

    assert client.get("/api/v1/originals/check/latest").json() == {"report": None}
