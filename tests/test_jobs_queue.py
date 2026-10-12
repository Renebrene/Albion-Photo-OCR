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


def test_enqueue_then_claim_then_done(cleanup_jobs):
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


def test_mark_failed(cleanup_jobs):
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


def test_list_jobs_returns_created(cleanup_jobs):
    job_id = jobs_db.enqueue("DINO_BATCH", {"batch_id": 7})
    cleanup_jobs.append(job_id)

    items, _ = jobs_db.list_jobs(limit=100)
    assert any(item["id"] == job_id for item in items)
