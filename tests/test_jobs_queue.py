"""
Integration tests for the deferred job queue (app.jobs.database).

Requires PostgreSQL with schema/006 applied; skipped otherwise. Created jobs
are removed afterwards.
"""

from __future__ import annotations

import os

import pytest

from app.jobs import database as jobs_db


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with jobs_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.job_queue')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="job_queue not available (INGEST_DB_* / schema 006)",
)


@pytest.fixture
def cleanup_jobs():
    created: list[int] = []
    yield created

    if created:
        with jobs_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.job_queue WHERE id = ANY(%s)",
                    (created,),
                )


def _queue_busy() -> bool:
    """True when another consumer (a running worker) is using the queue."""

    with jobs_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM public.job_queue "
                "WHERE status IN ('PENDING', 'RUNNING')"
            )
            return cur.fetchone()[0] > 0


@pytest.fixture
def require_idle_queue():
    """
    Claim-order tests need exclusive access to the queue.

    When a worker is actively consuming jobs (a live QWEN/DINO run), skip
    instead of asserting on a shared, concurrently-mutated queue.
    """

    if _queue_busy():
        pytest.skip("job queue is being consumed by a running worker")


def test_enqueue_then_claim_then_done(cleanup_jobs, require_idle_queue):
    job_id = jobs_db.enqueue("DINO_BATCH", {"batch_id": 1})
    cleanup_jobs.append(job_id)

    job = jobs_db.get_job(job_id)
    assert job["status"] == "PENDING"
    assert job["attempts"] == 0
    assert job["payload"] == {"batch_id": 1}

    claimed = jobs_db.claim_next()
    assert claimed is not None
    assert claimed["id"] == job_id
    assert claimed["job_type"] == "DINO_BATCH"

    jobs_db.mark_done(job_id, {"status": "DONE"})

    final = jobs_db.get_job(job_id)
    assert final["status"] == "DONE"
    assert final["attempts"] == 1
    assert final["result"] == {"status": "DONE"}
    assert final["finished_at"] is not None


def test_mark_failed(cleanup_jobs, require_idle_queue):
    job_id = jobs_db.enqueue("HYBRID_RUN", {"hybrid_run_id": 1})
    cleanup_jobs.append(job_id)

    assert jobs_db.claim_next()["id"] == job_id
    jobs_db.mark_failed(job_id, "boom")

    final = jobs_db.get_job(job_id)
    assert final["status"] == "FAILED"
    assert final["error_message"] == "boom"


def test_claim_returns_none_when_empty():
    # Drain any leftover PENDING jobs first is not needed: this asserts the
    # function returns None on an empty queue only when nothing is pending.
    with jobs_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM public.job_queue WHERE status = 'PENDING'"
            )
            pending = cur.fetchone()[0]

    if pending:
        pytest.skip("queue is not empty")

    assert jobs_db.claim_next() is None


def test_rejects_unknown_job_type():
    with pytest.raises(ValueError):
        jobs_db.enqueue("NOPE", {})


def test_list_jobs_returns_created(cleanup_jobs, require_idle_queue):
    job_id = jobs_db.enqueue("DINO_BATCH", {"batch_id": 7})
    cleanup_jobs.append(job_id)

    # Page from just before our job so it is on the first page even when the
    # table already holds many older jobs.
    items, _ = jobs_db.list_jobs(limit=100, cursor=job_id - 1)
    assert any(item["id"] == job_id for item in items)


def test_requeue_stale_returns_running_job(cleanup_jobs, require_idle_queue):
    job_id = jobs_db.enqueue("DINO_BATCH", {"batch_id": 1})
    cleanup_jobs.append(job_id)

    claimed = jobs_db.claim_next()
    assert claimed["id"] == job_id
    assert jobs_db.get_job(job_id)["status"] == "RUNNING"

    # A zero-minute threshold makes the claimed job immediately stale.
    requeued = jobs_db.requeue_stale(older_than_minutes=0)

    assert requeued >= 1
    assert jobs_db.get_job(job_id)["status"] == "PENDING"
