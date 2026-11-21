"""
Инвентаризация превью: вес, число файлов и превью без оригиналов.

Ключевое правило: чистить можно только уверенные случаи (записи фото нет
или оригинал удалён при живом каталоге). Отмонтированный том, пропавший
каталог и путь вне корней — не повод удалять превью: иначе одна переехавшая
папка стёрла бы весь корпус.
"""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.api.main import app
from app.preview import inventory

client = TestClient(app, raise_server_exceptions=False)

ALIVE = "PH_" + "a" * 24
GONE = "PH_" + "b" * 24
NO_PHOTO = "PH_" + "c" * 24
MOVED = "PH_" + "d" * 24
FOREIGN = "PH_" + "e" * 24
STRAY = "PH_" + "f" * 24


class _Cursor:
    def __init__(self, rows):
        self._rows = rows
        self.deleted = None

    def execute(self, sql, params=None):
        if "DELETE" in sql:
            self.deleted = list(params[0]) if params else []

    def fetchall(self):
        return self._rows

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


def _setup(tmp_path, monkeypatch):
    """Каталоги превью и корни оригиналов; DB подменяется отдельно."""

    root = tmp_path / "preview"
    small = root / "small"
    middle = root / "middle"
    small.mkdir(parents=True)
    middle.mkdir(parents=True)

    originals = tmp_path / "originals"
    originals.mkdir()
    alive = originals / "alive.jpg"
    alive.write_bytes(b"jpeg")

    monkeypatch.setattr(inventory, "PREVIEW_ROOT", root)
    monkeypatch.setattr(inventory, "ORIGINALS_ROOTS", [originals])
    monkeypatch.setenv("SCENE_DATA", str(tmp_path / "data"))

    return root, originals, alive


def _write_preview(root, photo_id, size="middle", size_bytes=1000):
    path = root / size / f"{photo_id}.webp"
    path.write_bytes(b"x" * size_bytes)
    return path


def _preview_row(photo_id, root, *, has_photo=True, source_path=None):
    return (
        photo_id,
        str(root / "small" / f"{photo_id}.webp"),
        str(root / "middle" / f"{photo_id}.webp"),
        has_photo,
        source_path,
    )


def _patch_db(monkeypatch, rows):
    cursor = _Cursor(rows)
    monkeypatch.setattr(inventory, "get_connection", lambda: _Connection(cursor))
    return cursor


def _cover(row_paths):
    """Заглушка «файл превью есть» из реального каталога не нужна: пишем файлы."""


def test_scan_counts_files_and_bytes(tmp_path, monkeypatch):
    root, _originals, alive = _setup(tmp_path, monkeypatch)
    _write_preview(root, ALIVE, "small", 100)
    _write_preview(root, ALIVE, "middle", 900)

    _patch_db(monkeypatch, [_preview_row(ALIVE, root, source_path=str(alive))])

    summary = inventory.scan()

    assert summary["previews"]["photos"] == 1
    assert summary["previews"]["files"] == 2
    assert summary["previews"]["bytes"] == 1000
    assert summary["previews"]["small"] == {"files": 1, "bytes": 100}
    assert summary["previews"]["middle"] == {"files": 1, "bytes": 900}
    assert summary["orphans"]["count"] == 0


def test_scan_separates_the_reasons_and_only_safe_ones_are_purgeable(
    tmp_path, monkeypatch
):
    root, originals, alive = _setup(tmp_path, monkeypatch)

    for photo_id in (ALIVE, GONE, NO_PHOTO, MOVED, FOREIGN):
        _write_preview(root, photo_id, "small", 10)
        _write_preview(root, photo_id, "middle", 20)

    rows = [
        _preview_row(ALIVE, root, source_path=str(alive)),
        # каталог на месте, файла нет — оригинал удалён
        _preview_row(GONE, root, source_path=str(originals / "gone.jpg")),
        # записи фото нет вообще
        _preview_row(NO_PHOTO, root, has_photo=False),
        # каталог оригинала исчез — переезд/переименование
        _preview_row(MOVED, root, source_path=str(originals / "moved" / "x.jpg")),
        # путь вне разрешённых корней
        _preview_row(FOREIGN, root, source_path=str(tmp_path / "elsewhere" / "x.jpg")),
    ]
    _patch_db(monkeypatch, rows)

    orphans = inventory.scan()["orphans"]

    assert orphans["count"] == 4
    assert orphans["reasons"] == {
        inventory.FILE_MISSING: 1,
        inventory.PHOTO_MISSING: 1,
        inventory.DIRECTORY_MISSING: 1,
        inventory.OUTSIDE_ROOTS: 1,
    }
    assert orphans["purgeable"] == 2
    assert orphans["purgeable_bytes"] == 60


def test_scan_marks_stray_files_without_a_preview_row(tmp_path, monkeypatch):
    root, _originals, _alive = _setup(tmp_path, monkeypatch)
    _write_preview(root, STRAY, "middle", 77)
    _patch_db(monkeypatch, [])

    orphans = inventory.scan()["orphans"]

    assert orphans["count"] == 1
    assert orphans["reasons"] == {inventory.PHOTO_MISSING: 1}
    assert orphans["bytes"] == 77


def test_unavailable_root_is_not_offered_for_cleanup(tmp_path, monkeypatch):
    root, _originals, _alive = _setup(tmp_path, monkeypatch)
    _write_preview(root, GONE, "small", 10)
    _write_preview(root, GONE, "middle", 20)

    dead = tmp_path / "Win10"  # том отмонтирован
    monkeypatch.setattr(inventory, "ORIGINALS_ROOTS", [dead])

    _patch_db(
        monkeypatch,
        [_preview_row(GONE, root, source_path=str(dead / "photo.jpg"))],
    )

    orphans = inventory.scan()["orphans"]

    assert orphans["reasons"] == {inventory.ROOT_UNAVAILABLE: 1}
    assert orphans["purgeable"] == 0


def test_purge_deletes_only_safe_orphans_and_keeps_a_report(tmp_path, monkeypatch):
    root, originals, alive = _setup(tmp_path, monkeypatch)

    for photo_id in (ALIVE, GONE, NO_PHOTO, MOVED):
        _write_preview(root, photo_id, "small", 10)
        _write_preview(root, photo_id, "middle", 20)

    rows = [
        _preview_row(ALIVE, root, source_path=str(alive)),
        _preview_row(GONE, root, source_path=str(originals / "gone.jpg")),
        _preview_row(NO_PHOTO, root, has_photo=False),
        _preview_row(MOVED, root, source_path=str(originals / "moved" / "x.jpg")),
    ]
    cursor = _patch_db(monkeypatch, rows)

    result = inventory.purge_orphans()

    assert result["photos"] == 2
    assert result["deleted_files"] == 4
    assert result["freed_bytes"] == 60
    assert result["skipped"] == 1

    # Файлы «сирот» удалены, превью переехавшего фото осталось.
    assert not (root / "small" / f"{GONE}.webp").exists()
    assert not (root / "middle" / f"{NO_PHOTO}.webp").exists()
    assert (root / "middle" / f"{MOVED}.webp").exists()
    assert (root / "middle" / f"{ALIVE}.webp").exists()

    assert sorted(cursor.deleted) == sorted([GONE, NO_PHOTO])

    stored = json.loads(open(result["report"], encoding="utf-8").read())
    assert stored["photos"] == 2
    assert stored["deleted_files"] == 4
    assert stored["skipped"] == {inventory.DIRECTORY_MISSING: 1}


def test_purge_never_touches_files_outside_the_preview_root(tmp_path, monkeypatch):
    root, originals, alive = _setup(tmp_path, monkeypatch)

    outside = tmp_path / "somewhere" / f"{GONE}.webp"
    outside.parent.mkdir()
    outside.write_bytes(b"keep me")

    _patch_db(
        monkeypatch,
        [
            (
                GONE,
                str(outside),
                str(outside),
                True,
                str(originals / "gone.jpg"),
            )
        ],
    )

    result = inventory.purge_orphans()

    assert outside.exists()
    assert result["deleted_files"] == 0


def test_inventory_endpoint_returns_the_summary(monkeypatch):
    monkeypatch.setattr(
        inventory,
        "scan",
        lambda: {"previews": {"photos": 2}, "orphans": {"count": 0}},
    )

    response = client.get("/api/v1/previews/inventory")

    assert response.status_code == 200
    assert response.json()["previews"]["photos"] == 2


def test_purge_endpoint_reports_what_was_deleted(monkeypatch):
    monkeypatch.setattr(
        inventory,
        "purge_orphans",
        lambda: {"photos": 3, "deleted_files": 6, "freed_bytes": 9, "skipped": 0},
    )

    response = client.post("/api/v1/previews/orphans/purge")

    assert response.status_code == 200
    assert response.json()["photos"] == 3
