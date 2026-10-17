"""Unique-photo counters for DINO/HYBRID sort history."""

from __future__ import annotations

from app.runs import history
from app.runs.history import _sort_counts_after_stage, initial_sort_counts


def test_auto_hybrid_counts_unique_photos_and_keeps_per_stage_progress():
    counts = initial_sort_counts(164, dino=True, hybrid=True)

    counts = _sort_counts_after_stage(
        counts,
        "DINO",
        status="DONE",
        total=164,
        done=164,
        failed=0,
    )

    assert counts["done"] == 0
    assert counts["total"] == 164
    assert counts["by_stage"]["DINO"]["done"] == 164
    assert counts["by_stage"]["HYBRID"]["status"] == "PENDING"

    counts = _sort_counts_after_stage(
        counts,
        "HYBRID",
        status="DONE",
        total=164,
        done=164,
        failed=0,
    )

    assert counts["done"] == 164
    assert counts["failed"] == 0
    assert counts["total"] == 164


def test_dino_only_sort_counts_unique_photos():
    counts = initial_sort_counts(8, dino=True, hybrid=False)

    counts = _sort_counts_after_stage(
        counts,
        "DINO",
        status="DONE",
        total=8,
        done=7,
        failed=1,
    )

    assert counts["done"] == 7
    assert counts["failed"] == 1
    assert counts["total"] == 8
    assert counts["by_stage"]["HYBRID"]["status"] == "SKIPPED"


def test_record_job_result_does_not_add_same_photos_twice(monkeypatch):
    state = {
        "kind": "sort",
        "counts": initial_sort_counts(4, dino=True, hybrid=True),
    }

    monkeypatch.setattr(history, "get_run", lambda _run_id: state)
    monkeypatch.setattr(history, "link_job", lambda *_args: None)
    monkeypatch.setattr(history, "_finish_if_complete", lambda _run_id: None)

    def update_run(_run_id, *, counts_delta=None, counts_mutator=None, **_kwargs):
        counts = dict(state["counts"])
        for key, delta in (counts_delta or {}).items():
            counts[key] = int(counts.get(key, 0)) + int(delta)
        if counts_mutator is not None:
            counts = counts_mutator(counts)
        state["counts"] = counts
        return state

    monkeypatch.setattr(history, "update_run", update_run)

    history.record_job_result(
        7,
        job_type="DINO_BATCH",
        job_id=20,
        status="DONE",
        result={"status": "DONE", "total_count": 4, "done_count": 4, "failed_count": 0},
    )
    assert state["counts"]["done"] == 0
    assert state["counts"]["by_stage"]["DINO"]["done"] == 4

    history.record_job_result(
        7,
        job_type="HYBRID_RUN",
        job_id=21,
        status="DONE",
        result={"status": "DONE", "total_count": 4, "done_count": 4, "failed_count": 0},
    )

    assert state["counts"]["done"] == 4
    assert state["counts"]["total"] == 4
    assert state["counts"]["jobs_done"] == 2


def test_failed_dino_skips_hybrid_and_counts_incomplete_photos():
    counts = initial_sort_counts(4, dino=True, hybrid=True)

    counts = _sort_counts_after_stage(
        counts,
        "DINO",
        status="FAILED",
        total=4,
        done=3,
        failed=1,
    )

    assert counts["by_stage"]["HYBRID"]["status"] == "SKIPPED"
    assert counts["done"] == 0
    assert counts["failed"] == 4
    assert counts["total"] == 4


def test_standalone_hybrid_uses_hybrid_as_the_unique_photo_stage():
    counts = initial_sort_counts(3, dino=False, hybrid=True)

    counts = _sort_counts_after_stage(
        counts,
        "HYBRID",
        status="DONE",
        total=3,
        done=3,
        failed=0,
    )

    assert counts["done"] == 3
    assert counts["failed"] == 0
    assert counts["total"] == 3
    assert counts["by_stage"]["DINO"]["status"] == "SKIPPED"
