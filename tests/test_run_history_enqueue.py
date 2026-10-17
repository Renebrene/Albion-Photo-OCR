from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def history_mocks(monkeypatch):
    from app.api import routes
    from app.runs import history

    monkeypatch.setenv("SCENE_API_TOKENS", "operator:jobs:write")
    create_run = Mock(return_value=901)
    add_jobs = Mock()
    finish_enqueue = Mock()
    update_run = Mock()
    monkeypatch.setattr(history, "create_run", create_run)
    monkeypatch.setattr(history, "add_jobs", add_jobs)
    monkeypatch.setattr(history, "finish_enqueue", finish_enqueue)
    monkeypatch.setattr(history, "update_run", update_run)
    return SimpleNamespace(
        routes=routes,
        create_run=create_run,
        add_jobs=add_jobs,
        finish_enqueue=finish_enqueue,
        update_run=update_run,
        headers={"Authorization": "Bearer operator"},
    )


def test_manual_dino_run_links_job_and_preserves_response(history_mocks, monkeypatch):
    h = history_mocks
    monkeypatch.setattr(h.routes.dino_db, "create_batch", lambda *_: SimpleNamespace(
        batch_id=22, total_count=3, status="PENDING"
    ))
    enqueue = Mock(return_value=74)
    monkeypatch.setattr(h.routes.jobs_db, "enqueue", enqueue)

    response = client.post(
        "/api/v1/jobs/dino-batch",
        json={"run_type": "NORMAL"},
        headers=h.headers,
    )

    assert response.status_code == 202
    assert response.json() == {
        "job_id": 74, "batch_id": 22, "batch_status": "PENDING", "total_count": 3,
    }
    h.create_run.assert_called_once_with(
        kind="sort", mode="manual", title="DINO batch #22", total=3,
        source_id=22, status="RUNNING", started=True,
    )
    enqueue.assert_called_once_with("DINO_BATCH", {"batch_id": 22}, run_history_id=901)
    h.add_jobs.assert_called_once_with(901, [74])
    h.finish_enqueue.assert_called_once_with(901, total=3)


def test_zero_work_dino_finishes_history_without_enqueue(history_mocks, monkeypatch):
    h = history_mocks
    monkeypatch.setattr(h.routes.dino_db, "create_batch", lambda *_: SimpleNamespace(
        batch_id=23, total_count=0, status="DONE"
    ))
    enqueue = Mock()
    monkeypatch.setattr(h.routes.jobs_db, "enqueue", enqueue)

    response = client.post(
        "/api/v1/jobs/dino-batch", json={"run_type": "NORMAL"}, headers=h.headers,
    )

    assert response.status_code == 202
    assert response.json()["job_id"] is None
    enqueue.assert_not_called()
    h.finish_enqueue.assert_called_once_with(901, total=0)


def test_dino_enqueue_failure_is_recorded_and_propagated(history_mocks, monkeypatch):
    h = history_mocks
    monkeypatch.setattr(h.routes.dino_db, "create_batch", lambda *_: SimpleNamespace(
        batch_id=24, total_count=1, status="PENDING"
    ))
    monkeypatch.setattr(h.routes.jobs_db, "enqueue", Mock(side_effect=RuntimeError("queue down")))

    response = client.post(
        "/api/v1/jobs/dino-batch", json={"run_type": "NORMAL"}, headers=h.headers,
    )

    assert response.status_code == 500
    h.update_run.assert_called_once()
    assert h.update_run.call_args.args == (901,)
    assert h.update_run.call_args.kwargs["status"] == "FAILED"
    assert h.update_run.call_args.kwargs["error_count_delta"] == 1


def test_manual_hybrid_run_links_job_and_keeps_contract(history_mocks, monkeypatch):
    h = history_mocks
    monkeypatch.setattr(h.routes.hybrid_db, "create_run", lambda *_: SimpleNamespace(
        hybrid_run_id=31, total_count=2, status="PENDING"
    ))
    enqueue = Mock(return_value=75)
    monkeypatch.setattr(h.routes.jobs_db, "enqueue", enqueue)

    response = client.post(
        "/api/v1/jobs/hybrid", json={"dino_batch_id": 12}, headers=h.headers,
    )

    assert response.status_code == 202
    assert response.json() == {
        "job_id": 75, "hybrid_run_id": 31, "status": "PENDING", "total_count": 2,
    }
    enqueue.assert_called_once_with("HYBRID_RUN", {"hybrid_run_id": 31}, run_history_id=901)
    h.add_jobs.assert_called_once_with(901, [75])
    h.finish_enqueue.assert_called_once_with(901, total=2)


def test_hybrid_zero_work_finishes_history_without_enqueue(history_mocks, monkeypatch):
    h = history_mocks
    monkeypatch.setattr(h.routes.hybrid_db, "create_run", lambda *_: SimpleNamespace(
        hybrid_run_id=32, total_count=0, status="DONE"
    ))
    enqueue = Mock()
    monkeypatch.setattr(h.routes.jobs_db, "enqueue", enqueue)

    response = client.post(
        "/api/v1/jobs/hybrid", json={"dino_batch_id": 12}, headers=h.headers,
    )

    assert response.status_code == 202
    assert response.json()["job_id"] is None
    enqueue.assert_not_called()
    h.finish_enqueue.assert_called_once_with(901, total=0)


def test_manual_hybrid_records_enqueue_error_and_propagates(history_mocks, monkeypatch):
    h = history_mocks
    monkeypatch.setattr(h.routes.hybrid_db, "create_run", lambda *_: SimpleNamespace(
        hybrid_run_id=33, total_count=1, status="PENDING"
    ))
    monkeypatch.setattr(h.routes.jobs_db, "enqueue", Mock(side_effect=RuntimeError("queue down")))

    response = client.post(
        "/api/v1/jobs/hybrid", json={"dino_batch_id": 12}, headers=h.headers,
    )

    assert response.status_code == 500
    h.update_run.assert_called_once()
    assert h.update_run.call_args.kwargs["status"] == "FAILED"


def test_manual_dino_is_not_blocked_when_history_storage_is_unavailable(monkeypatch):
    from app.api import routes
    from app.runs import history

    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setattr(history, "create_run", Mock(side_effect=RuntimeError("history unavailable")))
    monkeypatch.setattr(routes.dino_db, "create_batch", lambda *_: SimpleNamespace(
        batch_id=25, total_count=0, status="DONE"
    ))

    response = client.post("/api/v1/jobs/dino-batch", json={"run_type": "NORMAL"})
    assert response.status_code == 202
    assert response.json()["batch_id"] == 25
    assert response.json()["job_id"] is None
