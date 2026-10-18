"""
Worker reliability: stale-run recovery, idempotent results, QWEN dedup.

Requires PostgreSQL (schema 003/005/006/017); skipped otherwise.
"""

from __future__ import annotations

import hashlib
import os

import pytest

from app.dino import database as dino_db
from app.hybrid import database as hybrid_db
from app.ingest.database import get_connection
from app.jobs import database as jobs_db

PROBE_PHOTO = "PH_" + "f" * 24


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.job_queue')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="job queue not available (INGEST_DB_*)",
)


def _ensure_photo() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photos (
                    photo_id, source_path, filename, sha256,
                    container_format, frame_count, width, height
                )
                VALUES (%s, '/tmp/probe.jpg', 'probe.jpg', %s, 'JPEG', 1, 10, 10)
                ON CONFLICT (photo_id) DO NOTHING
                """,
                (PROBE_PHOTO, hashlib.sha256(PROBE_PHOTO.encode()).hexdigest()),
            )


def _cleanup() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.dino_batches WHERE batch_id IN "
                "(SELECT batch_id FROM public.dino_runs WHERE photo_id = %s)",
                (PROBE_PHOTO,),
            )
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = %s", (PROBE_PHOTO,)
            )


def test_enqueue_qwen_rejects_an_unknown_source():
    # Проверка идёт до обращения к БД: мусорный источник — ошибка вызывающего.
    with pytest.raises(ValueError):
        jobs_db.enqueue_qwen(PROBE_PHOTO, source="somewhere")


@requires_db
def test_enqueue_qwen_records_the_source():
    created = []

    try:
        job_id = jobs_db.enqueue_qwen(PROBE_PHOTO, source="automation")
        assert job_id is not None
        created.append(job_id)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload ->> 'source' FROM public.job_queue "
                    "WHERE id = %s",
                    (job_id,),
                )
                assert cur.fetchone()[0] == "automation"
    finally:
        if created:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.job_queue WHERE id = ANY(%s)",
                        (created,),
                    )


@requires_db
def test_qwen_stats_reports_base_size_and_runs(sample_photo):
    from app.api import repository

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select to_regclass('public.photo_qwen')")

            if cur.fetchone()[0] is None:
                pytest.skip("photo_qwen not available (schema 007)")

    stats = repository.qwen_stats()

    assert stats["photos"] >= 1
    # «Распознано» — у фото есть описание, а не «сейчас в статусе DONE»:
    # при повторном прогоне строка уходит в RUNNING, и счётчик не должен
    # идти назад (mark_running описание не стирает). DONE с пустым описанием
    # тоже встречается, поэтому жёсткое processed >= DONE не гарантируется.
    assert 0 <= stats["processed"] <= stats["photos"]
    assert stats["remaining"] == stats["photos"] - stats["processed"]
    assert stats["processed"] <= stats["photos"]
    assert stats["remaining"] == max(0, stats["photos"] - stats["processed"])
    assert stats["queued"] == (
        stats["counts"].get("PENDING", 0) + stats["counts"].get("RUNNING", 0)
    )
    assert isinstance(stats["runs"], list)
    assert isinstance(stats["models"], list)

    for run in stats["runs"]:
        assert run["source"] in jobs_db.QWEN_SOURCES
        assert run["jobs"] >= 1
        assert run["failed"] >= 0

    for item in stats["models"]:
        assert item["model"]
        assert item["photos"] >= 1


@requires_db
def test_enqueue_qwen_is_deduplicated():
    created = []

    try:
        first = jobs_db.enqueue_qwen(PROBE_PHOTO)
        assert first is not None
        created.append(first)

        # A second request while the first is still PENDING is skipped.
        assert jobs_db.enqueue_qwen(PROBE_PHOTO) is None

        # Marking the first DONE frees the photo for a new job.
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.job_queue SET status = 'DONE' WHERE id = %s",
                    (first,),
                )

        second = jobs_db.enqueue_qwen(PROBE_PHOTO)
        assert second is not None
        created.append(second)
    finally:
        if created:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.job_queue WHERE id = ANY(%s)",
                        (created,),
                    )


@requires_db
def test_dino_requeue_stale_runs():
    _cleanup()
    _ensure_photo()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.dino_batches (
                        run_type, status, total_count,
                        completed_count, failed_count
                    )
                    VALUES ('NORMAL', 'RUNNING', 1, 0, 0)
                    RETURNING batch_id
                    """
                )
                batch_id = int(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO public.dino_runs (
                        photo_id, run_type, status, batch_id, started_at
                    )
                    VALUES (%s, 'NORMAL', 'RUNNING', %s,
                            CURRENT_TIMESTAMP - interval '2 hours')
                    """,
                    (PROBE_PHOTO, batch_id),
                )

        reset = dino_db.requeue_stale_runs(older_than_minutes=30)
        assert reset >= 1

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, started_at FROM public.dino_runs "
                    "WHERE batch_id = %s",
                    (batch_id,),
                )
                status, started = cur.fetchone()
                assert status == "PENDING"
                assert started is None

        assert dino_db.has_active_batch() is True
    finally:
        _cleanup()


@requires_db
def test_hybrid_requeue_stale_runs():
    _cleanup()
    _ensure_photo()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.dino_batches (
                        run_type, status, total_count,
                        completed_count, failed_count
                    )
                    VALUES ('NORMAL', 'DONE', 1, 1, 0)
                    RETURNING batch_id
                    """
                )
                batch_id = int(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO public.hybrid_runs (
                        dino_batch_id, status, total_count,
                        completed_count, failed_count, started_at
                    )
                    VALUES (%s, 'RUNNING', 1, 0, 0,
                            CURRENT_TIMESTAMP - interval '2 hours')
                    RETURNING hybrid_run_id
                    """,
                    (batch_id,),
                )
                hybrid_run_id = int(cur.fetchone()[0])

        reset = hybrid_db.requeue_stale_runs(older_than_minutes=30)
        assert reset >= 1

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM public.hybrid_runs "
                    "WHERE hybrid_run_id = %s",
                    (hybrid_run_id,),
                )
                assert cur.fetchone()[0] == "PENDING"
    finally:
        _cleanup()


@requires_db
def test_hybrid_save_success_is_idempotent():
    _cleanup()
    _ensure_photo()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.dino_batches (
                        run_type, status, total_count,
                        completed_count, failed_count
                    )
                    VALUES ('NORMAL', 'DONE', 1, 1, 0)
                    RETURNING batch_id
                    """
                )
                batch_id = int(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO public.dino_runs (
                        photo_id, run_type, status, batch_id
                    )
                    VALUES (%s, 'NORMAL', 'DONE', %s)
                    RETURNING run_id
                    """,
                    (PROBE_PHOTO, batch_id),
                )
                dino_run_id = int(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO public.hybrid_runs (
                        dino_batch_id, status, total_count,
                        completed_count, failed_count, started_at
                    )
                    VALUES (%s, 'RUNNING', 1, 0, 0, CURRENT_TIMESTAMP)
                    RETURNING hybrid_run_id
                    """,
                    (batch_id,),
                )
                hybrid_run_id = int(cur.fetchone()[0])

        def save():
            hybrid_db.save_success(
                hybrid_run_id=hybrid_run_id,
                photo_id=PROBE_PHOTO,
                dino_run_id=dino_run_id,
                hybrid_original_id="78_v33",
                hybrid_final_id="78_v33",
                hybrid_changed=False,
                hybrid_old_score=1.0,
                hybrid_score=1.0,
                hybrid_margin=0.1,
                hybrid_neighbors="{}",
                hybrid_time_sec=0.01,
            )

        save()
        save()  # must not raise on the duplicate (run, photo)

        assert hybrid_db.completed_photo_ids(hybrid_run_id) == {PROBE_PHOTO}
    finally:
        _cleanup()
