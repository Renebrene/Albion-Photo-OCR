"""
Tests for the upload inbox (app.api.upload).

Pure logic (name sanitizing, size limit, atomic publish) runs everywhere;
the end-to-end INGEST path needs PostgreSQL.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api import upload as upload_mod
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def _jpeg_bytes(size=(16, 12)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(10, 120, 60)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def inbox(tmp_path, monkeypatch):
    target = tmp_path / "inbox"
    monkeypatch.setattr(upload_mod, "INBOX", target)
    return target


def test_sanitize_filename_strips_paths_and_rejects_types():
    assert upload_mod.sanitize_filename("../../etc/passwd.jpg") == "passwd.jpg"
    assert upload_mod.sanitize_filename("a b(1).JPG") == "a_b_1_.JPG"
    assert upload_mod.sanitize_filename("note.txt") is None
    assert upload_mod.sanitize_filename("") is None
    assert upload_mod.sanitize_filename(None) is None


def test_store_upload_writes_atomically(inbox):
    path = upload_mod.store_upload("photo.jpg", io.BytesIO(_jpeg_bytes()))

    assert path.parent == inbox
    assert path.is_file()
    assert path.read_bytes()
    # no leftover temp files
    assert not any(p.name.endswith(".part") for p in inbox.iterdir())


def test_store_upload_does_not_overwrite(inbox):
    first = upload_mod.store_upload("dup.jpg", io.BytesIO(_jpeg_bytes()))
    second = upload_mod.store_upload("dup.jpg", io.BytesIO(_jpeg_bytes()))

    assert first != second
    assert first.is_file() and second.is_file()


def test_store_upload_rejects_empty_and_unsafe(inbox):
    with pytest.raises(ValueError):
        upload_mod.store_upload("empty.jpg", io.BytesIO(b""))

    with pytest.raises(ValueError):
        upload_mod.store_upload("evil.txt", io.BytesIO(_jpeg_bytes()))


def test_store_upload_enforces_size_limit(inbox, monkeypatch):
    monkeypatch.setattr(upload_mod, "MAX_FILE_BYTES", 10)

    with pytest.raises(ValueError):
        upload_mod.store_upload("big.jpg", io.BytesIO(_jpeg_bytes()))

    assert not any(p.name.endswith(".part") for p in inbox.iterdir())


def test_upload_requires_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/upload",
        files={"files": ("p.jpg", _jpeg_bytes(), "image/jpeg")},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_upload_preview_queue_error_is_redacted_after_registration(monkeypatch, inbox):
    from app.ingest.register import PhotoRecord

    record = PhotoRecord(
        photo_id="PH_" + "12" * 12,
        source_path=str(inbox / "source.jpg"),
        filename="source.jpg",
        sha256="ab" * 32,
        container_format="JPEG",
        frame_count=1,
        width=10,
        height=8,
        size_bytes=100,
    )
    monkeypatch.setattr(upload_mod, "process_file", lambda _path: record)
    monkeypatch.setattr(upload_mod, "register_new_photos", lambda _records: {"NEW": [record], "EXISTING": [], "CONFLICT": []})
    from app.jobs import database as jobs_db
    monkeypatch.setattr(jobs_db, "enqueue_photo_preview", lambda _photo_id: (_ for _ in ()).throw(RuntimeError(f"failed at {inbox}/private")))

    result = upload_mod.ingest_upload("source.jpg", io.BytesIO(_jpeg_bytes()))

    assert result["status"] == "NEW"
    assert "preview_enqueue_error" in result
    assert str(inbox) not in result["preview_enqueue_error"]


def test_upload_rejects_non_image(inbox):
    response = client.post(
        "/api/v1/upload",
        files={"files": ("p.jpg", b"not an image", "image/jpeg")},
    )
    assert response.status_code == 201

    item = response.json()["items"][0]
    assert "error" in item
    assert "photo_id" not in item


def test_upload_rejects_too_many_files(inbox, monkeypatch):
    monkeypatch.setattr(upload_mod, "MAX_FILES", 1)
    response = client.post(
        "/api/v1/upload",
        files=[
            ("files", ("a.jpg", _jpeg_bytes(), "image/jpeg")),
            ("files", ("b.jpg", _jpeg_bytes(), "image/jpeg")),
        ],
    )
    assert response.status_code == 413
