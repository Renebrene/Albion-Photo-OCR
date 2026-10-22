"""
Доступность оригинала и пересоздание превью по photo_id.

Проверки только читают файловую систему и подменяют соединение с базой:
ни БД, ни рабочая папка не затрагиваются.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest

from app.api.file_access import (
    ORIGINAL_MISSING,
    ORIGINAL_NOT_CONFIGURED,
    ORIGINAL_OK,
    ORIGINAL_OUTSIDE_ROOTS,
    allowed_media_path,
    original_availability,
)
from app.preview import queue as preview_queue


# ---- original_availability (чистая функция) -------------------------------


def test_existing_file_inside_the_root_is_available(tmp_path):
    root = tmp_path / "photos"
    root.mkdir()
    photo = root / "a.jpg"
    photo.write_bytes(b"jpeg")

    assert original_availability(str(photo), [root]) == ORIGINAL_OK
    # Тот же путь, что отдаёт /original: недоступный файл не отдаётся.
    assert allowed_media_path(str(photo), [root]) == photo.resolve()


def test_deleted_file_is_missing_not_an_error(tmp_path):
    root = tmp_path / "photos"
    root.mkdir()
    gone = root / "deleted.jpg"

    assert original_availability(str(gone), [root]) == ORIGINAL_MISSING
    assert original_availability(None, [root]) == ORIGINAL_MISSING


def test_path_outside_the_roots_is_reported_separately(tmp_path):
    root = tmp_path / "photos"
    root.mkdir()
    other = tmp_path / "elsewhere"
    other.mkdir()
    photo = other / "a.jpg"
    photo.write_bytes(b"jpeg")

    assert original_availability(str(photo), [root]) == ORIGINAL_OUTSIDE_ROOTS


def test_without_configured_roots_nothing_is_available(tmp_path):
    photo = tmp_path / "a.jpg"
    photo.write_bytes(b"jpeg")

    assert original_availability(str(photo), []) == ORIGINAL_NOT_CONFIGURED


def test_a_directory_is_not_an_available_original(tmp_path):
    root = tmp_path / "photos"
    root.mkdir()
    nested = root / "sub"
    nested.mkdir()

    assert original_availability(str(nested), [root]) == ORIGINAL_MISSING


# ---- пересоздание превью по photo_id -------------------------------------


def _fake_connection(monkeypatch, pages):
    class Cursor:
        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return next(pages)

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

    monkeypatch.setattr(preview_queue, "get_connection", fake)


def _preview_files(root, photo_id, *, write=True):
    paths = preview_queue.build_preview_paths(preview_root=root, photo_id=photo_id)
    paths.small.parent.mkdir(parents=True, exist_ok=True)
    paths.middle.parent.mkdir(parents=True, exist_ok=True)
    if write:
        paths.small.write_bytes(b"small")
        paths.middle.write_bytes(b"middle")
    return paths


def test_preview_files_missing_distinguishes_present_and_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(preview_queue, "PREVIEW_ROOT", tmp_path)
    photo_id = "PH_" + "11" * 12
    paths = _preview_files(tmp_path, photo_id, write=False)

    assert preview_queue.preview_files_missing(photo_id, str(paths.small), str(paths.middle)) is True

    paths.small.write_bytes(b"small")
    paths.middle.write_bytes(b"middle")

    assert preview_queue.preview_files_missing(photo_id, str(paths.small), str(paths.middle)) is False
    # Пустой файл считается отсутствующим: генератор обязан его перезаписать.
    paths.middle.write_bytes(b"")

    assert preview_queue.preview_files_missing(photo_id, str(paths.small), str(paths.middle)) is True


def test_rebuild_skips_complete_and_unavailable_originals(tmp_path, monkeypatch):
    """Оригинал недоступен — задание не ставится, фото не трогается."""

    originals = tmp_path / "photos"
    originals.mkdir()
    live = originals / "live.jpg"
    live.write_bytes(b"jpeg")

    rebuildable = "PH_" + "aa" * 12
    complete = "PH_" + "bb" * 12
    gone = "PH_" + "cc" * 12

    monkeypatch.setattr(preview_queue, "PREVIEW_ROOT", tmp_path / "preview")
    monkeypatch.setattr(preview_queue, "ORIGINALS_ROOTS", [originals])

    complete_paths = _preview_files(tmp_path / "preview", complete)
    _preview_files(tmp_path / "preview", rebuildable, write=False)
    _preview_files(tmp_path / "preview", gone, write=False)

    _fake_connection(
        monkeypatch,
        iter(
            [
                [
                    (rebuildable, str(live), None, None),
                    (complete, str(live), str(complete_paths.small), str(complete_paths.middle)),
                    (gone, str(originals / "deleted.jpg"), None, None),
                ]
            ]
        ),
    )
    calls = []
    monkeypatch.setattr(
        preview_queue, "enqueue_photo_preview", lambda photo_id: calls.append(photo_id) or 7
    )

    result = preview_queue.enqueue_missing_previews(
        limit=10, photo_ids=[rebuildable, complete, gone]
    )

    assert result == {
        "selected": 1,
        "queued": 1,
        "already_active": 0,
        "originals_missing": 1,
    }
    assert calls == [rebuildable]


def test_rebuild_reports_an_already_active_job(tmp_path, monkeypatch):
    originals = tmp_path / "photos"
    originals.mkdir()
    live = originals / "live.jpg"
    live.write_bytes(b"jpeg")
    photo_id = "PH_" + "dd" * 12

    monkeypatch.setattr(preview_queue, "PREVIEW_ROOT", tmp_path / "preview")
    monkeypatch.setattr(preview_queue, "ORIGINALS_ROOTS", [originals])
    _preview_files(tmp_path / "preview", photo_id, write=False)
    _fake_connection(monkeypatch, iter([[(photo_id, str(live), None, None)]]))
    monkeypatch.setattr(preview_queue, "enqueue_photo_preview", lambda _photo_id: None)

    result = preview_queue.enqueue_missing_previews(limit=10, photo_ids=[photo_id])

    assert result["already_active"] == 1
    assert result["queued"] == 0


def test_rebuild_respects_the_limit(tmp_path, monkeypatch):
    originals = tmp_path / "photos"
    originals.mkdir()
    ids = ["PH_" + f"{index:02d}" * 12 for index in range(1, 4)]
    monkeypatch.setattr(preview_queue, "PREVIEW_ROOT", tmp_path / "preview")
    monkeypatch.setattr(preview_queue, "ORIGINALS_ROOTS", [originals])

    rows = []
    for photo_id in ids:
        live = originals / f"{photo_id}.jpg"
        live.write_bytes(b"jpeg")
        _preview_files(tmp_path / "preview", photo_id, write=False)
        rows.append((photo_id, str(live), None, None))
    _fake_connection(monkeypatch, iter([rows]))
    calls = []
    monkeypatch.setattr(
        preview_queue, "enqueue_photo_preview", lambda photo_id: calls.append(photo_id) or 1
    )

    result = preview_queue.enqueue_missing_previews(limit=2, photo_ids=ids)

    assert result["selected"] == 2
    assert len(calls) == 2


def test_rebuild_rejects_an_out_of_range_limit():
    with pytest.raises(ValueError):
        preview_queue.enqueue_missing_previews(limit=0, photo_ids=[])


# ---- маршрут статуса оригинала -------------------------------------------


def test_status_route_reports_availability_without_the_path(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.api.main import app

    root = tmp_path / "photos"
    root.mkdir()
    photo = root / "a.jpg"
    photo.write_bytes(b"jpeg")
    photo_id = "PH_" + "ee" * 12

    monkeypatch.setattr(routes, "ORIGINALS_ROOTS", [root])
    monkeypatch.setattr(
        routes.repository,
        "get_photo_source",
        lambda value: {"source_path": str(photo), "filename": "a.jpg", "container_format": "JPEG"},
    )

    client = TestClient(app)
    body = client.get(f"/api/v1/photos/{photo_id}/original/status").json()

    assert body == {"photo_id": photo_id, "available": True, "reason": ORIGINAL_OK}
    # Наружу не уходит ни путь, ни имя файла.
    assert "source_path" not in body
    assert str(root) not in str(body)


def test_status_route_marks_a_vanished_original(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.api.main import app

    root = tmp_path / "photos"
    root.mkdir()
    photo_id = "PH_" + "ff" * 12

    monkeypatch.setattr(routes, "ORIGINALS_ROOTS", [root])
    monkeypatch.setattr(
        routes.repository,
        "get_photo_source",
        lambda value: {"source_path": str(root / "gone.jpg")},
    )

    client = TestClient(app)
    body = client.get(f"/api/v1/photos/{photo_id}/original/status").json()

    assert body["available"] is False
    assert body["reason"] == ORIGINAL_MISSING


def test_status_route_is_404_for_an_unknown_photo(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.api.main import app

    monkeypatch.setattr(routes.repository, "get_photo_source", lambda _value: None)

    client = TestClient(app)
    response = client.get("/api/v1/photos/PH_" + "00" * 12 + "/original/status")

    assert response.status_code == 404


# ---- скрипты (без базы: только проверки аргументов и конфигурации) --------


def _load_script(name: str, relative: str):
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(name, root / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_originals_script_reports_a_missing_configuration(monkeypatch, capsys):
    module = _load_script("check_originals", "scripts/check_originals.py")
    monkeypatch.setattr(module, "ORIGINALS_ROOTS", [])

    assert module.main([]) == 2
    assert "SCENE_ORIGINALS_ROOTS" in capsys.readouterr().err


def test_rebuild_script_rejects_an_out_of_range_limit(capsys):
    module = _load_script("rebuild_previews", "scripts/rebuild_previews.py")

    assert module.main(["--limit", "0"]) == 2
    assert "1 до 5000" in capsys.readouterr().err
