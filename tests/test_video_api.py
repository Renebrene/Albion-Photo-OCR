from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import videos
from app.api.auth import ROLE_SCOPES


def make_app():
    app = FastAPI()
    app.include_router(videos.public_router, prefix="/api")
    app.include_router(videos.read_router, prefix="/api")
    app.include_router(videos.playback_router, prefix="/api")
    app.include_router(videos.originals_router, prefix="/api")
    app.include_router(videos.write_router, prefix="/api")
    return app


def test_manager_may_download_and_guest_may_not():
    """
    Матрица «скачивания» держится двумя ролями сразу.

    Решение владельца 2026-10-16: Менеджер отличается от Администратора только
    техническим разделом, поэтому он скачивает и видео, и оригиналы фото.
    Ограничение осталось одно — Гость не получает ни видео-scopes, ни
    `originals` (read-only по метаданным и превью).
    """

    manager = ROLE_SCOPES["Менеджер"]
    guest = ROLE_SCOPES["Гость"]

    assert {"videos:read", "videos:write", "videos:download"} <= manager
    assert "originals" in manager

    for scope in ("videos:read", "videos:write", "videos:download", "originals"):
        assert scope not in guest, f"Гость не должен иметь {scope}"


def test_playback_endpoint_enforces_dedicated_video_read_scope(monkeypatch):
    video_id = "VI_" + "af" * 12
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "1")
    monkeypatch.setenv("SCENE_API_TOKENS", "viewer:read")
    monkeypatch.setattr(videos, "ORIGINALS_ROOTS", [Path("/tmp")])

    client = TestClient(make_app())
    url = f"/api/v1/videos/{video_id}/playback-ticket"
    assert client.post(url).status_code == 401
    response = client.post(url, headers={"Authorization": "Bearer viewer"})
    assert response.status_code == 403


def test_list_videos_passes_capture_date_filter(monkeypatch):
    video_id = "VI_" + "bc" * 12
    seen = {}

    def fake_list(**kwargs):
        seen.update(kwargs)
        return ([{
            "video_id": video_id, "filename": "one.mp4", "display_title": "",
            "container_format": "mp4", "video_codec": "h264", "width": 640,
            "height": 360, "duration_seconds": 1.5, "fps": 25.0,
            "frame_count": 38, "size_bytes": 1000, "taken_at": None,
            "created_at": None,
        }], None)

    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")
    monkeypatch.setenv("SCENE_API_TOKENS", "")
    monkeypatch.setattr(videos.video_repository, "list_videos", fake_list)
    response = TestClient(make_app()).get(
        "/api/v1/videos?date_mode=capture&date_from=2026-10-01&date_to=2026-10-15"
    )

    assert response.status_code == 200
    assert seen["date_mode"] == "capture"
    assert seen["date_from"] == "2026-10-01"
    assert response.json()["items"][0]["video_id"] == video_id


def test_list_videos_rejects_invalid_dates(monkeypatch):
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")
    monkeypatch.setenv("SCENE_API_TOKENS", "")

    response = TestClient(make_app()).get(
        "/api/v1/videos?date_from=abcdefghij"
    )

    assert response.status_code == 422


def test_list_videos_swaps_an_inverted_range(monkeypatch):
    seen = {}

    def fake_list(**kwargs):
        seen.update(kwargs)
        return ([], None)

    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")
    monkeypatch.setenv("SCENE_API_TOKENS", "")
    monkeypatch.setattr(videos.video_repository, "list_videos", fake_list)

    response = TestClient(make_app()).get(
        "/api/v1/videos?date_from=2026-10-31&date_to=2026-10-01"
    )

    assert response.status_code == 200
    assert seen["date_from"] == "2026-10-01"
    assert seen["date_to"] == "2026-10-31"


def test_ranges_parse_single_and_suffix_ranges():
    assert videos._parse_range("bytes=10-19", 100) == (10, 19)
    assert videos._parse_range("bytes=10-", 100) == (10, 99)
    assert videos._parse_range("bytes=-10", 100) == (90, 99)
    assert videos._parse_range(None, 100) is None


def test_range_rejects_unsatisfiable_and_multiple_ranges():
    from fastapi import HTTPException

    for value in ("bytes=100-", "bytes=20-10", "bytes=0-1,4-5", "bytes=-0"):
        try:
            videos._parse_range(value, 100)
        except HTTPException as exc:
            assert exc.status_code == 416
        else:
            raise AssertionError(f"expected range rejection for {value}")


def test_playback_ticket_cookie_hides_token_and_stream_supports_range(tmp_path, monkeypatch):
    video_id = "VI_" + "ab" * 12
    source = tmp_path / "source video.mp4"
    source.write_bytes(b"0123456789abcdef")
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")
    monkeypatch.setenv("SCENE_API_TOKENS", "")
    monkeypatch.setattr(videos, "ORIGINALS_ROOTS", [tmp_path])
    monkeypatch.setattr(
        videos.video_repository,
        "video_source",
        lambda _video_id: {"source_path": str(source), "filename": source.name, "size_bytes": source.stat().st_size},
    )
    expires = datetime.now(timezone.utc)
    monkeypatch.setattr(
        videos.video_repository,
        "issue_playback_ticket",
        lambda *_args, **_kwargs: ("opaque-cookie-secret", expires),
    )
    monkeypatch.setattr(
        videos.video_repository,
        "validate_playback_ticket",
        lambda _id, token, action: token == "opaque-cookie-secret" and action == "inline",
    )

    client = TestClient(make_app())
    ticket_response = client.post(f"/api/v1/videos/{video_id}/playback-ticket")

    assert ticket_response.status_code == 200
    payload = ticket_response.json()
    assert payload["url"] == f"/api/v1/videos/{video_id}/stream"
    assert "opaque-cookie-secret" not in payload["url"]
    set_cookie = ticket_response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert f"Path=/api/v1/videos/{video_id}/stream" in set_cookie

    response = client.get(payload["url"], headers={"Range": "bytes=3-7"})

    assert response.status_code == 206
    assert response.content == b"34567"
    assert response.headers["content-range"] == "bytes 3-7/16"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-disposition"].startswith("inline;")


def test_download_requires_originals_scope_and_uses_attachment_ticket(tmp_path, monkeypatch):
    video_id = "VI_" + "cd" * 12
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"download-me")
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")
    monkeypatch.setenv("SCENE_API_TOKENS", "")
    monkeypatch.setattr(videos, "ORIGINALS_ROOTS", [tmp_path])
    monkeypatch.setattr(
        videos.video_repository,
        "video_source",
        lambda _video_id: {"source_path": str(source), "filename": source.name, "size_bytes": source.stat().st_size},
    )
    expires = datetime.now(timezone.utc)
    monkeypatch.setattr(
        videos.video_repository,
        "issue_playback_ticket",
        lambda *_args, **_kwargs: ("download-cookie", expires),
    )
    monkeypatch.setattr(
        videos.video_repository,
        "validate_playback_ticket",
        lambda _id, token, action: token == "download-cookie" and action == "attachment",
    )

    client = TestClient(make_app())
    issue = client.post(f"/api/v1/videos/{video_id}/download-ticket")
    assert issue.status_code == 200
    assert "download-cookie" not in issue.json()["url"]
    response = client.get(issue.json()["url"])

    assert response.status_code == 200
    assert response.content == b"download-me"
    assert response.headers["content-disposition"].startswith("attachment;")


def test_transcode_and_trim_enqueue_return_limit_errors(monkeypatch):
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")
    monkeypatch.setenv("SCENE_API_TOKENS", "")
    message = "редактирование доступно для видео размером не более 1,5 ГиБ"
    monkeypatch.setattr(videos.video_repository, "enqueue_transcode", lambda *_args: (_ for _ in ()).throw(ValueError(message)))
    monkeypatch.setattr(videos.video_repository, "enqueue_trim", lambda *_args: (_ for _ in ()).throw(ValueError(message)))
    client = TestClient(make_app())
    video_id = "VI_" + "ef" * 12
    assert client.post(f"/api/v1/videos/{video_id}/transcodes", json={"profile": "strong_720p"}).status_code == 422
    response = client.post(f"/api/v1/videos/{video_id}/trim", json={"start_seconds": 0, "end_seconds": 1})
    assert response.status_code == 422
    assert response.json()["detail"] == message


def test_source_directory_is_relative_to_allowed_roots_and_hides_untrusted_paths(tmp_path, monkeypatch):
    from app.api import config

    root = tmp_path / "originals"
    nested = root / "project" / "site"
    nested.mkdir(parents=True)
    monkeypatch.setattr(config, "ORIGINALS_ROOTS", [root])
    assert config.display_source_directory(str(nested / "photo.jpg")) == "project/site"
    assert config.display_source_directory("/etc/passwd") == ""


def test_edit_limit_boundaries_allow_exact_caps():
    from app.api.video_repository import (
        MAX_EDIT_VIDEO_BYTES,
        MAX_EDIT_VIDEO_DURATION_SECONDS,
        validate_video_edit_limits,
    )

    validate_video_edit_limits(MAX_EDIT_VIDEO_BYTES, MAX_EDIT_VIDEO_DURATION_SECONDS)
    with pytest.raises(ValueError, match="1,5 ГиБ"):
        validate_video_edit_limits(MAX_EDIT_VIDEO_BYTES + 1, 1)
    with pytest.raises(ValueError, match="10 минут"):
        validate_video_edit_limits(1, MAX_EDIT_VIDEO_DURATION_SECONDS + 0.001)


def test_video_title_write_is_validated_by_scope(tmp_path, monkeypatch):
    video_id = "VI_" + "ef" * 12
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")
    monkeypatch.setenv("SCENE_API_TOKENS", "")
    monkeypatch.setattr(
        videos.video_repository,
        "update_display_title",
        lambda _id, title: {
            "video_id": video_id,
            "filename": "clip.mp4",
            "display_title": title,
            "container_format": "mp4",
            "video_codec": "h264",
            "width": 640,
            "height": 360,
            "duration_seconds": 2.0,
            "size_bytes": 100,
        },
    )
    response = TestClient(make_app()).put(
        f"/api/v1/videos/{video_id}/title",
        json={"display_title": "Съёмка у входа"},
    )

    assert response.status_code == 200
    assert response.json()["display_title"] == "Съёмка у входа"
