"""
Integration tests for DINO batch state and the HYBRID gate.

These tests talk to a real PostgreSQL test database configured through the
same INGEST_DB_* environment variables as the application. They create
temporary photos/batches and clean them up afterwards. When the database is
not configured, the whole module is skipped, so the pure unit suite still runs
everywhere.

They do NOT load the DINO model: run outcomes are simulated by setting
dino_runs.status directly, which is exactly the state finish_batch reads.
"""

from __future__ import annotations

import hashlib
import os

import pytest

from app.ingest.register import PhotoRecord

psycopg = pytest.importorskip("psycopg")  # noqa: F841

from app.dino import database as dino_db  # noqa: E402
from app.hybrid import database as hybrid_db  # noqa: E402
from app.ingest import database as ingest_db  # noqa: E402


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.photos')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="integration PostgreSQL is not configured (INGEST_DB_*)",
)


TEMP_IDS = ("PH_" + "e" * 24, "PH_" + "d" * 24)


def _record(photo_id: str) -> PhotoRecord:
    return PhotoRecord(
        photo_id=photo_id,
        source_path=f"/tmp/{photo_id}.JPG",
        filename=f"{photo_id}.JPG",
        sha256=hashlib.sha256(photo_id.encode()).hexdigest(),
        container_format="JPEG",
        frame_count=1,
        width=1,
        height=1,
    )


@pytest.fixture
def temp_photos():
    records = [_record(pid) for pid in TEMP_IDS]

    for record in records:
        try:
            ingest_db.insert_photo(record)
        except Exception:
            pass  # already present from a previous aborted run

    yield records

    ids = [record.photo_id for record in records]
    with ingest_db.get_connection() as conn:
        with conn.cursor() as cur:
            # batches whose runs reference the temp photos (cascades to runs,
            # candidates, hybrid_runs and hybrid_results)
            cur.execute(
                """
                DELETE FROM public.dino_batches
                WHERE batch_id IN (
                    SELECT DISTINCT batch_id
                    FROM public.dino_runs
                    WHERE photo_id = ANY(%s)
                )
                """,
                (ids,),
            )
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = ANY(%s)",
                (ids,),
            )


def _set_run_status(batch_id: int, statuses: list[str]) -> None:
    with ingest_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT run_id FROM public.dino_runs WHERE batch_id = %s ORDER BY run_id",
                (batch_id,),
            )
            run_ids = [row[0] for row in cur.fetchall()]

            assert len(run_ids) == len(statuses)

            for run_id, status in zip(run_ids, statuses):
                cur.execute(
                    """
                    UPDATE public.dino_runs
                    SET status = %s, finished_at = CURRENT_TIMESTAMP
                    WHERE run_id = %s
                    """,
                    (status, run_id),
                )


def test_finish_batch_done_when_all_runs_done(temp_photos):
    batch = dino_db.create_batch(
        "FORCE_RERUN", [r.photo_id for r in temp_photos]
    )
    _set_run_status(batch.batch_id, ["DONE", "DONE"])

    final = dino_db.finish_batch(batch.batch_id)

    assert final.status == "DONE"
    assert final.completed_count == 2
    assert final.failed_count == 0


def test_finish_batch_failed_when_any_run_failed(temp_photos):
    batch = dino_db.create_batch(
        "FORCE_RERUN", [r.photo_id for r in temp_photos]
    )
    _set_run_status(batch.batch_id, ["DONE", "FAILED"])

    final = dino_db.finish_batch(batch.batch_id)

    assert final.status == "FAILED"
    assert final.completed_count == 1
    assert final.failed_count == 1


def test_finish_batch_running_while_work_pending(temp_photos):
    batch = dino_db.create_batch("FORCE_RERUN", [temp_photos[0].photo_id])

    final = dino_db.finish_batch(batch.batch_id)

    assert final.status == "RUNNING"


def test_hybrid_rejects_failed_batch(temp_photos):
    batch = dino_db.create_batch("FORCE_RERUN", [temp_photos[0].photo_id])
    _set_run_status(batch.batch_id, ["FAILED"])
    dino_db.finish_batch(batch.batch_id)

    with pytest.raises(ValueError):
        hybrid_db.create_run(batch.batch_id)


def test_hybrid_accepts_done_batch(temp_photos):
    batch = dino_db.create_batch("FORCE_RERUN", [temp_photos[0].photo_id])
    _set_run_status(batch.batch_id, ["DONE"])
    dino_db.finish_batch(batch.batch_id)

    run = hybrid_db.create_run(batch.batch_id)

    assert run.status == "PENDING"
    assert run.total_count == 1
    assert run.dino_batch_id == batch.batch_id
