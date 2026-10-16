from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import video_repository
from app.api.main import app

client = TestClient(app)
VIDEO_ID = "VI_" + "12" * 12


def test_storyboard_enqueue_returns_bounded_job(monkeypatch):
    monkeypatch.setattr(video_repository, "enqueue_storyboard", lambda video_id: {
        "job_id": 17, "status": "PENDING", "reused": False,
    })
    response = client.post(f"/api/v1/videos/{VIDEO_ID}/storyboard")
    assert response.status_code == 202
    assert response.json() == {"job_id": 17, "status": "PENDING", "reused": False, "frame_count": 8}


def test_storyboard_enqueue_returns_404_for_unknown_video(monkeypatch):
    monkeypatch.setattr(video_repository, "enqueue_storyboard", lambda _video_id: None)
    response = client.post(f"/api/v1/videos/{VIDEO_ID}/storyboard")
    assert response.status_code == 404


def test_trim_enqueue_returns_job_and_derivative(monkeypatch):
    monkeypatch.setattr(video_repository, "enqueue_trim", lambda video_id, start, end: {
        "video_id": video_id, "derivative_id": 7, "job_id": 18, "status": "PENDING",
        "start_seconds": start, "end_seconds": end, "reused": False,
    })

    response = client.post(f"/api/v1/videos/{VIDEO_ID}/trim", json={"start_seconds": 1, "end_seconds": 4})

    assert response.status_code == 202
    assert response.json()["derivative_id"] == 7
    assert response.json()["start_seconds"] == 1


def test_trim_enqueue_rejects_end_before_source_duration(monkeypatch):
    def reject(_video_id, _start, _end):
        raise ValueError("trim end exceeds source duration")

    monkeypatch.setattr(video_repository, "enqueue_trim", reject)
    response = client.post(f"/api/v1/videos/{VIDEO_ID}/trim", json={"start_seconds": 9, "end_seconds": 12})
    assert response.status_code == 422


def test_storyboard_frame_is_hidden_until_storyboard_job_is_done(monkeypatch):
    monkeypatch.setattr(video_repository, "video_source", lambda _video_id: {"sha256": "ab" * 32})
    monkeypatch.setattr(video_repository, "storyboard_ready", lambda *_args: False)
    response = client.get(f"/api/v1/videos/{VIDEO_ID}/storyboard/0")
    assert response.status_code == 404


def test_storyboard_frame_requires_video_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "read-token:read")
    response = client.get(
        f"/api/v1/videos/{VIDEO_ID}/storyboard/0",
        headers={"Authorization": "Bearer read-token"},
    )
    assert response.status_code == 403


def test_trim_enqueue_requires_video_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "read-token:read")
    response = client.post(
        f"/api/v1/videos/{VIDEO_ID}/trim",
        json={"start_seconds": 1, "end_seconds": 4},
        headers={"Authorization": "Bearer read-token"},
    )
    assert response.status_code == 403
