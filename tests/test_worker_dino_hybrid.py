"""DINO worker atomically queues the optional HYBRID stage."""

from __future__ import annotations

from types import SimpleNamespace

from app.jobs import worker


def test_dino_auto_hybrid_uses_shared_history_and_returns_photo_counts(monkeypatch):
    from app.dino import runner as dino_runner
    from app.hybrid import database as hybrid_db

    batch = SimpleNamespace(
        batch_id=19,
        status="DONE",
        total_count=4,
        completed_count=4,
        failed_count=0,
    )
    hybrid = SimpleNamespace(hybrid_run_id=31, total_count=4)
    calls = []
    runner_options = []

    def fake_run_batch(batch_id, **kwargs):
        runner_options.append((batch_id, kwargs))
        return batch

    monkeypatch.setattr(dino_runner, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        hybrid_db,
        "create_and_enqueue_run",
        lambda batch_id, *, run_history_id=None: (
            calls.append((batch_id, run_history_id)) or (hybrid, 74, None)
        ),
    )

    result = worker._execute({
        "id": 70,
        "job_type": "DINO_BATCH",
        "payload": {
            "batch_id": 19,
            "auto_hybrid": True,
            "run_history_id": 901,
        },
    })

    assert calls == [(19, 901)]
    assert runner_options[0][0] == 19
    assert callable(runner_options[0][1]["control"])
    assert runner_options[0][1]["recover_running"] is False
    assert result == {
        "batch_id": 19,
        "status": "DONE",
        "total_count": 4,
        "done_count": 4,
        "failed_count": 0,
    }


def test_dino_without_auto_hybrid_does_not_create_hybrid(monkeypatch):
    from app.dino import runner as dino_runner
    from app.hybrid import database as hybrid_db

    batch = SimpleNamespace(
        batch_id=20,
        status="DONE",
        total_count=1,
        completed_count=1,
        failed_count=0,
    )
    create = []
    runner_options = []

    def fake_run_batch(batch_id, **kwargs):
        runner_options.append((batch_id, kwargs))
        return batch

    monkeypatch.setattr(dino_runner, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        hybrid_db,
        "create_and_enqueue_run",
        lambda *args, **kwargs: create.append((args, kwargs)),
    )

    worker._execute({
        "id": 71,
        "job_type": "DINO_BATCH",
        "payload": {"batch_id": 20, "auto_hybrid": False},
    })

    assert create == []
