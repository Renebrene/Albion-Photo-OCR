"""DINO batch runner observes queue control at safe boundaries."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.dino import runner
from app.dino.database import DinoWorkItem
from app.jobs.worker import JobCancelled


def _items(count):
    return [
        DinoWorkItem(
            run_id=index + 1,
            photo_id=f"PH_{index + 1:024x}",
            source_path=f"/photos/{index + 1}.jpg",
            run_type="NORMAL",
        )
        for index in range(count)
    ]


def _install_batch(monkeypatch, items, workers):
    batch = SimpleNamespace(batch_id=5, status="PENDING", run_type="NORMAL")
    monkeypatch.setattr(runner, "resolve_workers", lambda value=None: workers)
    monkeypatch.setattr(runner, "resolve_batch", lambda value=None: 1)
    monkeypatch.setattr(runner, "get_batch", lambda _batch_id: batch)
    monkeypatch.setattr(runner, "get_batch_items", lambda _batch_id: list(items))
    monkeypatch.setattr(runner, "start_batch", lambda _batch_id: None)
    monkeypatch.setattr(
        runner,
        "abort_batch",
        lambda batch_id, error: SimpleNamespace(
            batch_id=batch_id, status="FAILED", completed_count=0, failed_count=1
        ),
    )
    monkeypatch.setattr(
        runner,
        "finish_batch",
        lambda _batch_id: (_ for _ in ()).throw(
            AssertionError("interrupted batch must not finish normally")
        ),
    )
    monkeypatch.setattr(
        runner,
        "DinoRunner",
        lambda workers=1: SimpleNamespace(workers=workers),
    )


def test_retry_resets_interrupted_runs_only_for_the_same_batch(monkeypatch):
    items = _items(1)
    _install_batch(monkeypatch, items, workers=1)
    requeued = []
    monkeypatch.setattr(
        runner,
        "get_batch",
        lambda _batch_id: SimpleNamespace(
            batch_id=5, status="RUNNING", run_type="NORMAL"
        ),
    )
    monkeypatch.setattr(
        runner,
        "requeue_interrupted_batch_runs",
        lambda batch_id: requeued.append(batch_id) or 1,
    )
    monkeypatch.setattr(
        runner,
        "_process_item",
        lambda _runner, item: (item, {"score": 0.8, "time_sec": 0.01}),
    )
    monkeypatch.setattr(
        runner,
        "finish_batch",
        lambda batch_id: SimpleNamespace(
            batch_id=batch_id,
            status="DONE",
            total_count=1,
            completed_count=1,
            failed_count=0,
        ),
    )

    final = runner.run_batch(5, workers=1, recover_running=True)

    assert requeued == [5]
    assert final.status == "DONE"


def test_single_worker_cancel_stops_before_next_photo(monkeypatch):
    items = _items(3)
    _install_batch(monkeypatch, items, workers=1)
    processed = []
    aborted = []

    def process(_runner, item):
        processed.append(item.run_id)
        return item, {"score": 0.8, "time_sec": 0.01}

    monkeypatch.setattr(runner, "_process_item", process)
    monkeypatch.setattr(
        runner,
        "abort_batch",
        lambda batch_id, error: (
            aborted.append((batch_id, error))
            or SimpleNamespace(batch_id=batch_id, status="FAILED", completed_count=0, failed_count=1)
        ),
    )

    calls = 0

    def control(_done, _total, _stage):
        nonlocal calls
        calls += 1
        if calls == 4:  # before the second photo, after the first completed
            raise JobCancelled("cancel requested")

    with pytest.raises(JobCancelled):
        runner.run_batch(5, workers=1, batch_size=1, control=control)

    assert processed == [1]
    assert aborted and aborted[0][0] == 5
    assert "cancel requested" in aborted[0][1]


def test_batched_pause_timeout_stops_before_the_next_chunk(monkeypatch):
    items = _items(3)
    _install_batch(monkeypatch, items, workers=1)
    started = []
    saved = []
    aborted = []
    monkeypatch.setattr(runner, "start_run", lambda run_id: (started.append(run_id) or next(i for i in items if i.run_id == run_id)))
    monkeypatch.setattr(
        runner,
        "_save_result",
        lambda run_id, _result: saved.append(run_id),
    )
    fake = SimpleNamespace(
        workers=1,
        recognize_many=lambda chunk: [
            {"score": 0.8, "time_sec": 0.01} for _item in chunk
        ],
    )
    monkeypatch.setattr(runner, "resolve_batch", lambda _batch=None: 2)
    monkeypatch.setattr(runner, "DinoRunner", lambda workers=1: fake)
    monkeypatch.setattr(
        runner,
        "abort_batch",
        lambda batch_id, error: (
            aborted.append((batch_id, error))
            or SimpleNamespace(batch_id=batch_id, status="FAILED", completed_count=2, failed_count=1)
        ),
    )

    calls = 0

    def control(_done, _total, _stage):
        nonlocal calls
        calls += 1
        if calls == 5:  # after first two-item chunk, before chunk two
            raise TimeoutError("pause timed out")

    with pytest.raises(TimeoutError, match="pause timed out"):
        runner.run_batch(5, workers=1, batch_size=2, control=control)

    assert started == [1, 2]
    assert saved == [1, 2]
    assert aborted and aborted[0][0] == 5


def test_threaded_cancel_does_not_submit_beyond_the_bounded_window(monkeypatch):
    items = _items(8)
    _install_batch(monkeypatch, items, workers=2)
    started = []
    aborted = []

    def process(_runner, item):
        started.append(item.run_id)
        return item, {"score": 0.8, "time_sec": 0.01}

    monkeypatch.setattr(runner, "_process_item", process)
    monkeypatch.setattr(
        runner,
        "abort_batch",
        lambda batch_id, error: (
            aborted.append((batch_id, error))
            or SimpleNamespace(batch_id=batch_id, status="FAILED", completed_count=0, failed_count=1)
        ),
    )

    calls = 0

    def control(_done, _total, _stage):
        nonlocal calls
        calls += 1
        if calls == 2:  # after the first future; initial window is 4
            raise JobCancelled("cancel requested")

    with pytest.raises(JobCancelled):
        runner.run_batch(5, workers=2, batch_size=1, control=control)

    assert started
    assert max(started) <= 4
    assert aborted and aborted[0][0] == 5
