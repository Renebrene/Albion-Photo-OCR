"""
Удалённая загрузка папки для сборки слепка (задание, п. 5а/5б).

Файлы с компьютера менеджера приезжают по одному во временную папку сервера.
Проверяем лимиты, проверку содержимого декодером, очистку имён и уборку.
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import pytest
from PIL import Image

from app.api import fingerprint_uploads as uploads


@pytest.fixture(autouse=True)
def _staging(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "STAGING_ROOT", tmp_path / "fingerprints")
    return tmp_path / "fingerprints"


def jpeg(name: str = "photo.jpg", size: tuple[int, int] = (32, 24)) -> tuple[str, io.BytesIO]:
    stream = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(stream, format="JPEG")
    stream.seek(0)
    return name, stream


# ---- сессии ----


def test_a_session_gives_a_server_issued_ticket(_staging):
    session = uploads.create_session()

    assert len(session["upload_id"]) == 32
    assert (_staging / session["upload_id"]).is_dir()
    assert session["max_files"] == uploads.MAX_FILES
    assert session["max_file_bytes"] == uploads.MAX_FILE_BYTES


def test_an_unknown_ticket_is_rejected():
    with pytest.raises(uploads.UploadError):
        uploads.folder("0" * 32)

    with pytest.raises(uploads.UploadError):
        uploads.folder("../../etc")


# ---- файлы ----


def test_a_photo_is_stored_and_verified(_staging):
    session = uploads.create_session()
    name, stream = jpeg()

    result = uploads.store_file(session["upload_id"], name, stream)

    assert result["received"] == 1
    assert (_staging / session["upload_id"] / "photo.jpg").is_file()
    assert result["total_bytes"] > 0


def test_the_name_is_sanitized_to_a_basename(_staging):
    """Клиентский путь не используется: остаётся только имя файла."""

    session = uploads.create_session()
    name, stream = jpeg()

    result = uploads.store_file(session["upload_id"], "../../secret.jpg", stream)

    assert result["name"] == "secret.jpg"
    assert not (_staging / "secret.jpg").exists()
    assert (_staging / session["upload_id"] / "secret.jpg").is_file()


def test_a_non_image_is_rejected_and_removed(_staging):
    session = uploads.create_session()

    with pytest.raises(uploads.UploadError):
        uploads.store_file(
            session["upload_id"],
            "fake.jpg",
            io.BytesIO(b"this is not an image at all"),
        )

    assert not list((_staging / session["upload_id"]).iterdir())


def test_an_unexpected_extension_is_rejected(_staging):
    session = uploads.create_session()

    with pytest.raises(uploads.UploadError):
        uploads.store_file(session["upload_id"], "script.php", io.BytesIO(b"<?php"))


def test_the_same_name_does_not_overwrite(_staging):
    session = uploads.create_session()

    first = uploads.store_file(session["upload_id"], "photo.jpg", jpeg()[1])
    second = uploads.store_file(session["upload_id"], "photo.jpg", jpeg()[1])

    assert first["name"] == "photo.jpg"
    assert second["name"] == "photo_1.jpg"


def test_the_number_of_files_is_limited(_staging, monkeypatch):
    monkeypatch.setattr(uploads, "MAX_FILES", 2)
    session = uploads.create_session()

    uploads.store_file(session["upload_id"], "a.jpg", jpeg()[1])
    uploads.store_file(session["upload_id"], "b.jpg", jpeg()[1])

    with pytest.raises(uploads.UploadError):
        uploads.store_file(session["upload_id"], "c.jpg", jpeg()[1])


def test_a_file_over_the_limit_is_rejected(_staging, monkeypatch):
    monkeypatch.setattr(uploads, "MAX_FILE_BYTES", 512)
    session = uploads.create_session()

    name, stream = jpeg(size=(400, 400))

    with pytest.raises(uploads.UploadError):
        uploads.store_file(session["upload_id"], name, stream)


def test_the_total_size_is_limited(_staging, monkeypatch):
    session = uploads.create_session()
    uploads.store_file(session["upload_id"], "a.jpg", jpeg()[1])

    used = uploads.stats(session["upload_id"])["total_bytes"]
    monkeypatch.setattr(uploads, "MAX_TOTAL_BYTES", used)

    with pytest.raises(uploads.UploadError):
        uploads.store_file(session["upload_id"], "b.jpg", jpeg()[1])


# ---- уборка ----


def test_deleting_a_session_removes_the_folder(_staging):
    session = uploads.create_session()
    uploads.store_file(session["upload_id"], "a.jpg", jpeg()[1])

    assert uploads.delete_session(session["upload_id"]) is True
    assert not (_staging / session["upload_id"]).exists()
    assert uploads.delete_session(session["upload_id"]) is False


def test_stale_sessions_are_swept(_staging):
    import os

    stale = uploads.create_session()
    old = time.time() - 48 * 3600
    os.utime(_staging / stale["upload_id"], (old, old))

    assert uploads.sweep_stale() == 1
    assert not (_staging / stale["upload_id"]).exists()

    # Свежая загрузка уборкой не задета.
    fresh = uploads.create_session()

    assert uploads.sweep_stale() == 0
    assert (_staging / fresh["upload_id"]).is_dir()


# ---- маршрут сборки ----


def test_build_from_an_upload_resolves_the_server_folder(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.api.main import app

    client = TestClient(app, raise_server_exceptions=False)

    session = uploads.create_session()
    uploads.store_file(session["upload_id"], "a.jpg", jpeg()[1])

    seen: dict = {}

    def fake_enqueue(fingerprint_id, folder, **kwargs):
        seen.update({"fingerprint_id": fingerprint_id, "folder": folder, **kwargs})
        return 77

    monkeypatch.setattr(routes.jobs_db, "enqueue_fingerprint_build", fake_enqueue)
    monkeypatch.setattr(routes.fingerprints_mod, "_check_id", lambda value: value)

    response = client.post(
        "/api/v1/fingerprints/build",
        json={"fingerprint_id": "test_v33", "upload_id": session["upload_id"]},
    )

    assert response.status_code == 202
    assert seen["upload_id"] == session["upload_id"]
    assert seen["folder"].endswith(session["upload_id"])
    assert response.json()["photos"] == 1
    # Абсолютный путь наружу не уходит.
    assert str(uploads.STAGING_ROOT) not in response.text


def test_build_requires_exactly_one_source():
    from fastapi.testclient import TestClient

    from app.api.main import app

    client = TestClient(app, raise_server_exceptions=False)

    both = client.post(
        "/api/v1/fingerprints/build",
        json={"fingerprint_id": "x_v33", "folder": "/tmp", "upload_id": "0" * 32},
    )
    neither = client.post(
        "/api/v1/fingerprints/build",
        json={"fingerprint_id": "x_v33"},
    )

    assert both.status_code == 422
    assert neither.status_code == 422
