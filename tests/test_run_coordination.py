from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.main import app
from app.jobs import automation
from app.runs import coordination

client = TestClient(app, raise_server_exceptions=False)


def test_activity_endpoint_reports_current_operation(monkeypatch):
    monkeypatch.setattr(
        coordination,
        "active_operation",
        lambda: {"kind": "pipeline", "run_id": 7, "stage": "DINO", "mode": "manual"},
    )

    response = client.get("/api/v1/runs/activity")

    assert response.status_code == 200
    body = response.json()
    assert body["active"]["kind"] == "pipeline"
    assert "DINO" in body["message"]


def test_manual_dino_is_rejected_while_scheduler_runs(monkeypatch):
    from app.api import routes

    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setattr(coordination, "launch_guard", _noop_guard)
    monkeypatch.setattr(
        coordination, "active_operation", lambda: {"kind": "scheduler", "run_id": 3}
    )
    create_batch = Mock()
    monkeypatch.setattr(routes.dino_db, "create_batch", create_batch)

    response = client.post("/api/v1/jobs/dino-batch", json={"run_type": "NORMAL"})

    assert response.status_code == 409
    assert "планировщика" in response.json()["detail"]
    create_batch.assert_not_called()


def test_manual_hybrid_is_rejected_while_pipeline_runs(monkeypatch):
    from app.api import routes

    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setattr(coordination, "launch_guard", _noop_guard)
    monkeypatch.setattr(
        coordination,
        "active_operation",
        lambda: {"kind": "pipeline", "run_id": 7, "stage": "HYBRID"},
    )
    create_run = Mock()
    monkeypatch.setattr(routes.hybrid_db, "create_run", create_run)

    response = client.post("/api/v1/jobs/hybrid", json={"dino_batch_id": 12})

    assert response.status_code == 409
    assert "Обновление базы" in response.json()["detail"]
    create_run.assert_not_called()


def test_pipeline_start_is_rejected_while_manual_sort_runs(monkeypatch):
    from app.supervisor import runs as pipeline_runs

    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setattr(coordination, "launch_guard", _noop_guard)
    monkeypatch.setattr(
        coordination,
        "active_operation",
        lambda: {"kind": "sort", "job_id": 5, "job_type": "DINO_BATCH"},
    )
    create_run = Mock()
    monkeypatch.setattr(pipeline_runs, "create_run", create_run)
    monkeypatch.setattr("app.api.routes.sources.current_folder", lambda: "")

    response = client.post("/api/v1/pipeline/start", json={})

    assert response.status_code == 409
    assert "сортировка" in response.json()["detail"].lower()
    create_run.assert_not_called()


class _LockedConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return _LockedCursor()


class _LockedCursor:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, *_args):
        return None

    def fetchone(self):
        return (True,)


@contextmanager
def _noop_guard():
    yield


def test_scheduler_tick_is_skipped_while_pipeline_runs(monkeypatch):
    monkeypatch.setattr(
        automation,
        "get_settings",
        lambda: {
            "enabled": True,
            "interval_minutes": 60,
            "auto_dino": False,
            "auto_qwen": False,
            "last_tick": None,
        },
    )
    monkeypatch.setattr(automation, "is_due", lambda _settings: True)
    monkeypatch.setattr(automation, "get_connection", lambda: _LockedConnection())
    monkeypatch.setattr(coordination, "launch_guard", _noop_guard)
    monkeypatch.setattr(
        coordination,
        "active_operation",
        lambda: {"kind": "pipeline", "run_id": 9, "stage": "DINO"},
    )
    create_history = Mock()
    monkeypatch.setattr(automation, "_create_scheduler_history", create_history)

    result = automation.run_tick()

    assert result == {"skipped": "pipeline_active"}
    create_history.assert_not_called()


def test_scheduler_returns_launch_busy_when_gate_is_taken(monkeypatch):
    @contextmanager
    def busy_guard():
        raise coordination.OperationBusy("another operation is starting")
        yield  # pragma: no cover

    monkeypatch.setattr(
        automation,
        "get_settings",
        lambda: {
            "enabled": True,
            "interval_minutes": 60,
            "auto_dino": False,
            "auto_qwen": False,
            "last_tick": None,
        },
    )
    monkeypatch.setattr(automation, "is_due", lambda _settings: True)
    monkeypatch.setattr(automation, "get_connection", lambda: _LockedConnection())
    monkeypatch.setattr(coordination, "launch_guard", busy_guard)

    assert automation.run_tick() == {"skipped": "launch_busy"}
