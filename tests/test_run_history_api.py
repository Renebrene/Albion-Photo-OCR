from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_history_list_requires_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "jobs:jobs:read")
    response = client.get("/api/v1/runs/history", headers={"Authorization": "Bearer jobs"})
    assert response.status_code == 403


def test_history_list_returns_empty_when_schema_is_not_available(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "reader:read")
    from app.runs import history

    monkeypatch.setattr(history, "_HISTORY_AVAILABLE", False)
    response = client.get("/api/v1/runs/history", headers={"Authorization": "Bearer reader"})
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_log_endpoint_requires_jobs_read_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "reader:read")
    response = client.get(
        "/api/v1/runs/history/1/log",
        headers={"Authorization": "Bearer reader"},
    )
    assert response.status_code == 403


def test_log_endpoint_does_not_accept_or_disclose_file_paths(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "jobs:jobs:read")
    from app.runs import history

    monkeypatch.setattr(history, "read_run_log", lambda run_id: None)
    response = client.get(
        "/api/v1/runs/history/1/log?path=/etc/passwd",
        headers={"Authorization": "Bearer jobs"},
    )
    assert response.status_code == 404
    assert "/etc/passwd" not in response.text
