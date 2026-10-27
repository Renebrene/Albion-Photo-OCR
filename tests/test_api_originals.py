"""
Доступность оригиналов: сводка по корням для технического раздела.

База не нужна — соединение подменяется: проверяется подсчёт, различение
отмонтированного тома и то, что ответ не перебирает файлы (иначе он не годился
бы для HTTP-запроса).
"""

from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.api import repository
from app.api.main import app


def _fake_connection(monkeypatch, counts):
    """Отдаёт заранее заданные ответы count(*) в порядке запросов."""

    class Cursor:
        def execute(self, sql, params=()):
            self.sql = sql
            self.params = params

        def fetchone(self):
            return (next(counts),)

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

    monkeypatch.setattr(repository, "get_connection", fake)


def test_originals_health_marks_an_unmounted_volume(tmp_path, monkeypatch):
    """Том без каталога виден отдельно: это диск, а не пропавшие файлы."""

    live = tmp_path / "TEST"
    live.mkdir()
    dead = tmp_path / "Win10"  # том отмонтирован

    monkeypatch.setattr(repository, "ORIGINALS_ROOTS", [dead, live])
    # Порядок запросов: всего, внутри корней, затем по одному на корень.
    _fake_connection(monkeypatch, iter([100, 90, 0, 90]))

    health = repository.originals_health()

    assert health["configured"] is True
    assert health["total_photos"] == 100
    assert health["outside_roots"] == 10
    assert health["unavailable_roots"] == 1
    assert [root["label"] for root in health["roots"]] == ["Win10", "TEST"]
    assert [root["available"] for root in health["roots"]] == [False, True]
    assert [root["photos"] for root in health["roots"]] == [0, 90]


def test_originals_health_counts_a_root_by_its_path_prefix(tmp_path, monkeypatch):
    """Счётчик корня сравнивает путь с корнем и его префиксом, без LIKE."""

    seen = []
    root = tmp_path / "TEST"
    root.mkdir()

    class Cursor:
        def execute(self, sql, params=()):
            seen.append((sql, params))

        def fetchone(self):
            return (0,)

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

    monkeypatch.setattr(repository, "ORIGINALS_ROOTS", [root])
    monkeypatch.setattr(repository, "get_connection", fake)

    repository.originals_health()

    per_root = seen[-1]
    assert "starts_with(source_path, %s)" in per_root[0]
    assert per_root[1] == (str(root), str(root) + "/")


def test_originals_health_without_roots_does_not_touch_the_database(monkeypatch):
    """Пустой SCENE_ORIGINALS_ROOTS — это ответ, а не запрос в базу."""

    def explode():
        raise AssertionError("когда корней нет, база не нужна")

    monkeypatch.setattr(repository, "ORIGINALS_ROOTS", [])
    monkeypatch.setattr(repository, "get_connection", explode)

    assert repository.originals_health() == {
        "configured": False,
        "roots": [],
        "total_photos": 0,
        "outside_roots": 0,
        "unavailable_roots": 0,
    }


def test_route_reports_the_summary_for_the_technical_section(tmp_path, monkeypatch):
    live = tmp_path / "TEST"
    live.mkdir()

    monkeypatch.setattr(repository, "ORIGINALS_ROOTS", [live])
    _fake_connection(monkeypatch, iter([5, 5, 5]))

    client = TestClient(app)
    body = client.get("/api/v1/originals/health").json()

    assert body["configured"] is True
    assert body["roots"] == [
        {"path": str(live), "label": "TEST", "available": True, "photos": 5}
    ]
    assert body["total_photos"] == 5
    assert body["outside_roots"] == 0
    assert body["unavailable_roots"] == 0
