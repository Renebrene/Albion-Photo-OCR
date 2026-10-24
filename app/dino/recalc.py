"""
Recalculate the recognition base after the fingerprint set changes.

Replacing a fingerprint changes the reference vectors, and hiding one removes
it from ranking. In both cases the stored DINO/HYBRID verdicts become stale, so
one full FORCE_RERUN batch is queued:

    photos -> DINO batch (active fingerprints only) -> HYBRID (auto_hybrid)

Фото без MIDDLE-превью в пересчёт не включаются: DINO работает по превью, а
нечитаемый исходник валил бы весь батч. Такие фото видны в отчёте о превью.

The queue job is deduplicated while a recalculation is already PENDING/RUNNING.
The check and the batch creation are serialized by a PostgreSQL advisory lock
so parallel fingerprint builders cannot enqueue several full passes.
"""

from __future__ import annotations

from app.dino import database as dino_db
from app.ingest.database import get_connection
from app.jobs import database as jobs_db
from app.runs import history as run_history

_LOCK_KEY = "scene_dino_recalc"


def _active_recalc(cur) -> int | None:
    cur.execute(
        """
        SELECT id
        FROM public.job_queue
        WHERE job_type = 'DINO_BATCH'
          AND status IN ('PENDING', 'RUNNING')
          AND payload ? 'recalc'
        ORDER BY id
        LIMIT 1
        """
    )
    row = cur.fetchone()
    return int(row[0]) if row is not None else None


def enqueue_recalculation(
    *,
    reason: str,
    fingerprint_id: str | None = None,
) -> dict | None:
    """
    Queue one full DINO+HYBRID pass over every photo.

    Returns ``{batch_id, job_id, total, run_id}``, or ``None`` when a
    recalculation is already queued/running (or the corpus is empty).
    """

    title = "Пересчёт базы"
    if fingerprint_id:
        title = f"Пересчёт базы после «{reason}» слепка {fingerprint_id}"
    else:
        title = f"Пересчёт базы: {reason}"

    # The advisory lock is transaction-scoped. It is held while the batch and
    # the queue row are created through their own connections, so two builders
    # finishing together cannot both pass the "no active recalc" check.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (_LOCK_KEY,),
            )

            if _active_recalc(cur) is not None:
                return None

            # DINO reads MIDDLE previews: фото без превью (битый или нечитаемый
            # исходник) в пересчёт не попадают, иначе весь батч заканчивался бы
            # сбоем из-за одного файла.
            cur.execute(
                """
                SELECT p.photo_id
                FROM public.photos AS p
                WHERE EXISTS (
                    SELECT 1 FROM public.photo_previews AS v
                    WHERE v.photo_id = p.photo_id
                )
                ORDER BY p.photo_id
                """
            )
            photo_ids = [str(row[0]) for row in cur.fetchall()]

        if not photo_ids:
            return None

        batch = dino_db.create_batch("FORCE_RERUN", photo_ids)
        history_id = None
        job_id = None

        try:
            history_id = run_history.create_run(
                kind="sort",
                mode="outofqueue",
                title=title,
                total=batch.total_count,
                counts=run_history.initial_sort_counts(
                    batch.total_count,
                    dino=True,
                    hybrid=True,
                ),
                source_id=batch.batch_id,
                status="RUNNING",
                started=True,
            )

            job_id = jobs_db.enqueue(
                "DINO_BATCH",
                {
                    "batch_id": batch.batch_id,
                    "auto_hybrid": True,
                    "recalc": True,
                },
                run_history_id=history_id,
            )

            if history_id is not None:
                run_history.add_jobs(history_id, [job_id])
                run_history.finish_enqueue(
                    history_id,
                    total=batch.total_count,
                    covered=batch.total_count,
                )
        except Exception:
            # Never leave a PENDING batch without its queue job: it would block
            # the next recalculation and sit in the batches table forever.
            if job_id is None:
                try:
                    with get_connection() as cleanup:
                        with cleanup.cursor() as cur:
                            cur.execute(
                                "UPDATE public.dino_batches "
                                "SET status = 'FAILED', "
                                "    finished_at = CURRENT_TIMESTAMP "
                                "WHERE batch_id = %s",
                                (batch.batch_id,),
                            )
                except Exception:
                    pass
            raise

    return {
        "batch_id": batch.batch_id,
        "job_id": job_id,
        "total": batch.total_count,
        "run_id": history_id,
    }
