from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.cloud import albion, export as cloud_export, repository as cloud_repository

client = TestClient(app, raise_server_exceptions=False)


class _Response:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload


def test_upload_returns_validated_link(tmp_path, monkeypatch):
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"image")
    seen = {}

    def fake_post(url, *, headers, data, files, timeout, **kwargs):
        seen["url"] = url
        seen["key"] = headers.get("X-API-Key")
        seen["data"] = dict(data)
        seen["filename"] = files["file"][0]
        return _Response(200, {
            "url": "https://files.example.ru/abc",
            "expires_at": "2027-01-15T10:00:00Z",
        })

    monkeypatch.setenv("ALBION_BASE_URL", "https://files.example.ru")
    monkeypatch.setenv("ALBION_API_KEY", "alb_test")
    monkeypatch.delenv("ALBION_FOLDER_ID", raising=False)
    monkeypatch.setattr(albion.httpx, "post", fake_post)

    result = albion.upload_file(source, "photo.jpg", ttl_days=90)

    assert result["url"] == "https://files.example.ru/abc"
    assert result["expires_at"] == datetime(2027, 1, 15, 10, 0, tzinfo=timezone.utc)
    assert seen["url"] == "https://files.example.ru/api/v1/integration/upload"
    assert seen["key"] == "alb_test"
    assert seen["data"] == {"ttl_days": "90"}
    assert seen["filename"] == "photo.jpg"


def test_upload_sends_the_configured_folder(tmp_path, monkeypatch):
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"image")
    seen = {}

    def fake_post(url, *, headers, data, files, timeout, **kwargs):
        seen["data"] = dict(data)
        return _Response(200, {"url": "https://files.example.ru/abc"})

    monkeypatch.setenv("ALBION_BASE_URL", "https://files.example.ru/")
    monkeypatch.setenv("ALBION_API_KEY", "alb_test")
    monkeypatch.setenv("ALBION_FOLDER_ID", "folder-1")
    monkeypatch.setattr(albion.httpx, "post", fake_post)

    albion.upload_file(source, "photo.jpg", ttl_days=30)

    assert seen["data"] == {"ttl_days": "30", "folder_id": "folder-1"}


def test_verify_returns_the_token_rights(monkeypatch):
    seen = {}

    def fake_get(url, *, headers, timeout, follow_redirects):
        seen["url"] = url
        seen["key"] = headers.get("X-API-Key")
        return _Response(200, {
            "ok": True,
            "name": "Photobase",
            "scopes": ["upload", "download"],
            "folder_id": "folder-1",
        })

    monkeypatch.setenv("ALBION_BASE_URL", "https://files.example.ru")
    monkeypatch.setenv("ALBION_API_KEY", "alb_test")
    monkeypatch.setattr(albion.httpx, "get", fake_get)

    result = albion.verify()

    assert result["name"] == "Photobase"
    assert result["scopes"] == ["upload", "download"]
    assert seen == {
        "url": "https://files.example.ru/api/v1/integration/verify",
        "key": "alb_test",
    }


def test_verify_maps_rejected_token(monkeypatch):
    monkeypatch.setenv("ALBION_BASE_URL", "https://files.example.ru")
    monkeypatch.setenv("ALBION_API_KEY", "alb_test")
    monkeypatch.setattr(
        albion.httpx, "get",
        lambda *args, **kwargs: _Response(403, {"error": "no"}),
    )

    with pytest.raises(albion.CloudUploadError, match="нет права"):
        albion.verify()


def test_public_settings_never_returns_the_token(monkeypatch):
    from app.cloud import config

    monkeypatch.setenv("ALBION_BASE_URL", "https://files.example.ru")
    monkeypatch.setenv("ALBION_API_KEY", "super-secret-key")
    monkeypatch.setenv("ALBION_FOLDER_ID", "folder-1")

    public = config.public_settings()

    assert "super-secret-key" not in str(public)
    assert public["api_key_set"] is True
    assert public["api_key_hint"].endswith("key")
    assert public["configured"] is True


def test_cloud_settings_reject_non_http_url(monkeypatch):
    from app.cloud import config

    with pytest.raises(ValueError, match="http"):
        config.update_settings(base_url="javascript:alert(1)")


def test_upload_rejects_relative_link_and_hides_key(tmp_path, monkeypatch):
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"image")
    monkeypatch.setenv("ALBION_BASE_URL", "https://files.example.ru")
    monkeypatch.setenv("ALBION_API_KEY", "super-secret-key")
    monkeypatch.delenv("ALBION_FOLDER_ID", raising=False)

    monkeypatch.setattr(
        albion.httpx, "post", lambda *args, **kwargs: _Response(200, {"url": "/relative"})
    )
    with pytest.raises(albion.CloudUploadError, match="некорректную ссылку"):
        albion.upload_file(source, "photo.jpg")

    monkeypatch.setattr(
        albion.httpx, "post", lambda *args, **kwargs: _Response(403, {"error": "no"})
    )
    with pytest.raises(albion.CloudUploadError) as denied:
        albion.upload_file(source, "photo.jpg")
    assert "super-secret-key" not in str(denied.value)
    assert "API-ключ" in str(denied.value)


def test_cloud_export_marks_ready_and_failed(monkeypatch):
    link = {"link_id": 4, "status": "PENDING", "media_kind": "photo", "media_id": "PH_x", "url": None}
    monkeypatch.setattr(cloud_export.repository, "get", lambda _id: link)
    monkeypatch.setattr(
        cloud_export.repository, "media_source", lambda *_args: {"path": Path("/tmp/a.jpg"), "filename": "a.jpg"}
    )
    ready = Mock()
    failed = Mock()
    monkeypatch.setattr(cloud_export.repository, "mark_ready", ready)
    monkeypatch.setattr(cloud_export.repository, "mark_failed", failed)
    monkeypatch.setattr(
        cloud_export.albion,
        "upload_file",
        lambda *_args, **_kwargs: {
            "url": "https://files.example.ru/a.jpg",
            "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
            "object_key": "a.jpg",
        },
    )

    result = cloud_export.run_export(4)
    assert result["status"] == "READY"
    ready.assert_called_once()

    monkeypatch.setattr(
        cloud_export.albion,
        "upload_file",
        Mock(side_effect=albion.CloudUploadError("Albion отклонил API-ключ")),
    )
    with pytest.raises(albion.CloudUploadError):
        cloud_export.run_export(4)
    failed.assert_called_once()


def test_media_links_require_upload_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/media-links",
        json={"photo_ids": ["PH_" + "a" * 24]},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_media_links_returns_503_when_albion_is_not_configured(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:upload:write")
    monkeypatch.delenv("ALBION_BASE_URL", raising=False)
    monkeypatch.delenv("ALBION_UPLOAD_URL", raising=False)
    monkeypatch.delenv("ALBION_API_KEY", raising=False)
    monkeypatch.delenv("ALBION_FOLDER_ID", raising=False)
    response = client.post(
        "/api/v1/media-links",
        json={"photo_ids": ["PH_" + "a" * 24]},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 503
    assert "Albion" in response.json()["detail"]


def test_create_media_links_enqueues_export(monkeypatch):
    from app.api import routes

    monkeypatch.setenv("SCENE_API_TOKENS", "tok:upload:write")
    monkeypatch.setattr(albion, "is_configured", lambda: True)
    monkeypatch.setattr(cloud_repository, "media_source", lambda *_args: {"path": "/tmp/a.jpg", "filename": "a.jpg"})
    monkeypatch.setattr(cloud_repository, "create_pending", lambda **_kwargs: {
        "link_id": 10, "status": "PENDING", "media_kind": "photo",
        "media_id": "PH_" + "a" * 24, "url": None, "expires_at": None,
    })
    attach = Mock()
    monkeypatch.setattr(cloud_repository, "attach_job", attach)
    enqueue = Mock(return_value=77)
    monkeypatch.setattr(routes.jobs_db, "enqueue", enqueue)

    response = client.post(
        "/api/v1/media-links",
        json={"photo_ids": ["PH_" + "a" * 24]},
        headers={"Authorization": "Bearer tok"},
    )

    assert response.status_code == 202
    assert response.json()["job_ids"] == [77]
    enqueue.assert_called_once_with("MEDIA_EXPORT", {"link_id": 10})
    attach.assert_called_once_with(10, 77)


def test_list_media_links_requires_jobs_read(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.get(
        "/api/v1/media-links",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_list_all_media_links_requires_administrator(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:jobs:read")
    response = client.get(
        "/api/v1/media-links?all=true",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403
    assert "administrator" in response.json()["detail"]
