"""
PostgreSQL access for the deferred job queue (public.job_queue).

The API enqueues jobs; a worker (app.jobs.worker) claims and executes them.
claim_next() uses SELECT ... FOR UPDATE SKIP LOCKED so several workers can
run safely in parallel.
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Json

from app.ingest.database import get_connection

JOB_TYPES = {
    "DINO_BATCH",
    "HYBRID_RUN",
    "QWEN_PHOTO",
    "NL_SEARCH",
    "INGEST_DIR",
    "MEDIA_SEARCH",
    "FINGERPRINT_BUILD",
    "VIDEO_TRANSCODE",
    "VIDEO_TRIM",
    "VIDEO_STORYBOARD",
    "PHOTO_PREVIEW",
    "MEDIA_EXPORT",
    "BILLBOARD_DETECT",
}

_JOB_COLUMNS = (
    "id, job_type, payload, status, attempts, "
    "result, error_message, created_at, started_at, finished_at, progress"
)


def _row_to_job(row) -> dict:
    return {
        "id": int(row[0]),
        "job_type": str(row[1]),
        "payload": row[2],
        "status": str(row[3]),
        "attempts": int(row[4]),
        "result": row[5],
        "error_message": row[6],
        "created_at": row[7],
        "started_at": row[8],
        "finished_at": row[9],
        "progress": row[10] if len(row) > 10 else None,
    }


def enqueue_in_transaction(
    cur,
    job_type: str,
    payload: dict[str, Any],
    *,
    run_history_id: int | None = None,
) -> int:
    """Insert a PENDING job on a caller-owned transaction/cursor."""

    if job_type not in JOB_TYPES:
        raise ValueError(f"Unsupported job type: {job_type}")

    payload = dict(payload)
    if run_history_id is not None:
        payload["run_history_id"] = int(run_history_id)

    cur.execute(
        """
        INSERT INTO public.job_queue (job_type, payload, status)
        VALUES (%s, %s, 'PENDING')
        RETURNING id
        """,
        (job_type, Json(payload)),
    )
    return int(cur.fetchone()[0])


def enqueue(
    job_type: str,
    payload: dict[str, Any],
    *,
    run_history_id: int | None = None,
) -> int:
    """Insert a PENDING job and return its id."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            return enqueue_in_transaction(
                cur,
                job_type,
                payload,
                run_history_id=run_history_id,
            )


def enqueue_photo_preview(photo_id: str) -> int | None:
    """Atomically enqueue one active preview job per registered photo id."""

    if not photo_id:
        raise ValueError("photo_id is required")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM public.photos WHERE photo_id=%s FOR KEY SHARE", (photo_id,))
            if cur.fetchone() is None:
                return None
            cur.execute(
                """INSERT INTO public.job_queue(job_type, payload, status)
                   VALUES ('PHOTO_PREVIEW', %s, 'PENDING')
                   ON CONFLICT ((payload ->> 'photo_id'))
                   WHERE job_type='PHOTO_PREVIEW' AND status IN ('PENDING', 'RUNNING')
                   DO NOTHING
                   RETURNING id""",
                (Json({"photo_id": photo_id}),),
            )
            row = cur.fetchone()
            return int(row[0]) if row is not None else None


# Who asked for a QWEN job. Recorded in the payload so the statistics card can
# show the last run per trigger: the "Настройки" button (manual), the scheduler
# (automation) and the full "Обновление базы" run (pipeline).
QWEN_SOURCES = ("manual", "automation", "pipeline")


def enqueue_qwen(
    photo_id: str,
    *,
    source: str = "manual",
    provider: str | None = None,
    model: str | None = None,
    run_history_id: int | None = None,
    priority: bool = False,
) -> int | None:
    """
    Enqueue a QWEN job for one photo, deduplicated while active.

    Returns the new job id, or None when a PENDING/RUNNING QWEN job already
    exists for that photo (checked in the same statement, so two concurrent
    callers cannot both insert).
    """

    if source not in QWEN_SOURCES:
        raise ValueError(f"unknown QWEN source: {source}")

    # Разовая пересборка из карточки фото: конкретный провайдер/модель.
    payload: dict = {"photo_id": photo_id, "source": source}

    if provider:
        payload["provider"] = provider

    if model:
        payload["model"] = model
    if run_history_id is not None:
        payload["run_history_id"] = int(run_history_id)
    if priority:
        # Одиночное пересканирование из карточки не должно ждать массовый
        # прогон: claim_next ставит такие задания впереди очереди.
        payload["priority"] = True

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.job_queue (job_type, payload, status)
                SELECT 'QWEN_PHOTO', %s, 'PENDING'
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.job_queue
                    WHERE job_type = 'QWEN_PHOTO'
                      AND status IN ('PENDING', 'RUNNING')
                      AND payload ->> 'photo_id' = %s
                )
                RETURNING id
                """,
                (Json(payload), photo_id),
            )
            row = cur.fetchone()

            return int(row[0]) if row is not None else None


def enqueue_billboard_detect(photo_id: str) -> int | None:
    """
    Queue the background billboard detection for one photo, deduplicated
    while a detection of that photo is already pending/running.
    """

    if not photo_id:
        raise ValueError("photo_id is required")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.job_queue (job_type, payload, status)
                SELECT 'BILLBOARD_DETECT', %s, 'PENDING'
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.job_queue
                    WHERE job_type = 'BILLBOARD_DETECT'
                      AND status IN ('PENDING', 'RUNNING')
                      AND payload ->> 'photo_id' = %s
                )
                RETURNING id
                """,
                (Json({"photo_id": photo_id}), photo_id),
            )
            row = cur.fetchone()

            return int(row[0]) if row is not None else None


def enqueue_fingerprint_build(
    fingerprint_id: str,
    folder: str,
    *,
    max_photos: int | None = None,
    replace: bool = True,
    batch_id: str | None = None,
    recalculate: bool = False,
) -> int | None:
    """
    Queue one fingerprint build (or rebuild).

    One active build per fingerprint: a second request while the first is still
    PENDING/RUNNING is not duplicated (returns None), the same way a repeated
    ingest of one folder is skipped.

    *recalculate* asks the builder to queue one full DINO+HYBRID pass after a
    successful replacement of an existing fingerprint (the reference vectors
    changed, so old verdicts are stale). New fingerprints need no pass.
    """

    payload = {
        "fingerprint_id": str(fingerprint_id),
        "folder": str(folder),
        "replace": bool(replace),
    }

    if max_photos:
        payload["max_photos"] = int(max_photos)

    if batch_id:
        payload["batch_id"] = str(batch_id)

    if recalculate:
        payload["recalculate"] = True

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.job_queue (job_type, payload, status)
                SELECT %s, %s, 'PENDING'
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.job_queue
                    WHERE job_type = 'FINGERPRINT_BUILD'
                      AND status IN ('PENDING', 'RUNNING')
                      AND payload ->> 'fingerprint_id' = %s
                )
                RETURNING id
                """,
                ("FINGERPRINT_BUILD", Json(payload), payload["fingerprint_id"]),
            )

            row = cur.fetchone()

            return int(row[0]) if row is not None else None


def enqueue_ingest(
    directory: str,
    *,
    only_files: list[str] | None = None,
    run_history_id: int | None = None,
) -> int | None:
    """
    Enqueue an INGEST job for one folder, deduplicated while active.

    Returns the new job id, or None when a PENDING/RUNNING ingest of the same
    folder already exists (a second scan of a big tree would only duplicate
    work). The folder itself is validated by the API before this call.

    *only_files* (relative names) restricts the scan to a frozen snapshot, so a
    resumed pipeline run does not pick up files added while it was stopped.
    """

    payload: dict[str, Any] = {"directory": directory}

    if only_files is not None:
        payload["only_files"] = list(only_files)
    if run_history_id is not None:
        payload["run_history_id"] = int(run_history_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.job_queue (job_type, payload, status)
                SELECT 'INGEST_DIR', %s, 'PENDING'
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.job_queue
                    WHERE job_type = 'INGEST_DIR'
                      AND status IN ('PENDING', 'RUNNING')
                      AND payload ->> 'directory' = %s
                )
                RETURNING id
                """,
                (Json(payload), directory),
            )
            row = cur.fetchone()

            return int(row[0]) if row is not None else None


def get_job(job_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_JOB_COLUMNS} FROM public.job_queue WHERE id = %s",  # noqa: S608
                (job_id,),
            )
            row = cur.fetchone()

    return _row_to_job(row) if row is not None else None


def list_jobs(
    *,
    limit: int,
    cursor: int | None = None,
) -> tuple[list[dict], int | None]:
    """Return jobs ordered by id (newest last)."""

    sql = f"SELECT {_JOB_COLUMNS} FROM public.job_queue"  # noqa: S608
    params: list[object] = []

    if cursor is not None:
        sql += " WHERE id > %s"
        params.append(cursor)

    sql += " ORDER BY id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [_row_to_job(row) for row in rows]
    next_cursor = items[-1]["id"] if has_next and items else None

    return items, next_cursor


def claim_next(
    types: list[str] | None = None,
    *,
    exclude_types: list[str] | None = None,
) -> dict | None:
    """
    Atomically move the oldest PENDING job to RUNNING.

    `types` restricts the claim to those job types, which is how dedicated
    builder workers take only FINGERPRINT_BUILD and leave the rest of the queue
    to the main worker. Returns the claimed job, or None when nothing matches.

    A PAUSED job is never claimed: pausing a queued job is a way to hold it.
    """

    clauses = []
    params: list[object] = []

    if types:
        clauses.append("job_type = ANY(%s)")
        params.append(list(types))
    if exclude_types is None and types is None:
        exclude_types = ["PHOTO_PREVIEW", "VIDEO_TRANSCODE", "VIDEO_TRIM", "VIDEO_STORYBOARD"]
    if exclude_types:
        clauses.append("NOT (job_type = ANY(%s))")
        params.append(list(exclude_types))
    where = " AND " + " AND ".join(clauses) if clauses else ""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, job_type, payload, attempts
                FROM public.job_queue
                WHERE status = 'PENDING'
                """
                + where
                + """
                ORDER BY (payload ->> 'priority') IS NOT NULL DESC, id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """,
                params,
            )
            row = cur.fetchone()

            if row is None:
                return None

            job_id = int(row[0])

            cur.execute(
                """
                UPDATE public.job_queue
                SET status = 'RUNNING',
                    attempts = attempts + 1,
                    started_at = CURRENT_TIMESTAMP,
                    error_message = NULL
                WHERE id = %s
                """,
                (job_id,),
            )

            return {
                "id": job_id,
                "job_type": str(row[1]),
                "payload": row[2],
                "attempts": int(row[3]) + 1,
            }


def mark_done(job_id: int, result: dict[str, Any] | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.job_queue
                SET status = 'DONE',
                    result = %s,
                    finished_at = CURRENT_TIMESTAMP,
                    error_message = NULL
                WHERE id = %s
                  AND status = 'RUNNING'
                """,
                (Json(result or {}), job_id),
            )

            if cur.rowcount != 1:
                raise ValueError(
                    f"Cannot complete job {job_id}: not RUNNING"
                )


def list_batch(batch_id: str) -> list[dict]:
    """
    Every job of one batch, oldest first, with its progress.

    Used by the window to draw a single bar for a batch of fingerprint builds.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {_JOB_COLUMNS}
                FROM public.job_queue
                WHERE payload ->> 'batch_id' = %s
                ORDER BY id
                """,
                (str(batch_id),),
            )
            rows = cur.fetchall()

    return [_row_to_job(row) for row in rows]


def set_progress(job_id: int, progress: dict[str, Any]) -> bool:
    """
    Record what a running job has done so far (percent/done/total/stage).

    Called by the worker between batches; the job window polls the row and
    draws the bar from it. Returns False when the job is gone.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.job_queue
                SET progress = %s
                WHERE id = %s
                """,
                (Json(progress), job_id),
            )

            return cur.rowcount == 1


def job_status(job_id: int) -> str | None:
    """Current status of a job, or None when it does not exist."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM public.job_queue WHERE id = %s",
                (job_id,),
            )
            row = cur.fetchone()

    return str(row[0]) if row is not None else None


def mark_paused(job_id: int) -> bool:
    """
    Hold a job: PENDING or RUNNING becomes PAUSED.

    A PAUSED job is not claimed (claim_next only takes PENDING); one that is
    already running notices between batches and waits for the resume.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.job_queue
                SET status = 'PAUSED',
                    progress = COALESCE(progress, '{}'::jsonb)
                        || jsonb_build_object('paused', TRUE)
                WHERE id = %s
                  AND status IN ('PENDING', 'RUNNING')
                """,
                (job_id,),
            )

            return cur.rowcount == 1


def mark_resumed(job_id: int) -> bool:
    """Release a held job back to the worker."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.job_queue
                SET status = CASE
                        WHEN started_at IS NULL THEN 'PENDING'
                        ELSE 'RUNNING'
                    END,
                    progress = COALESCE(progress, '{}'::jsonb)
                        || jsonb_build_object('paused', FALSE)
                WHERE id = %s
                  AND status = 'PAUSED'
                """,
                (job_id,),
            )

            return cur.rowcount == 1


def mark_cancelled(job_id: int) -> bool:
    """
    Cancel a queued, running, or paused job.

    A job cancelled before its first claim cannot be finalized by a worker, so
    its unstarted DINO/HYBRID domain run is closed in the same transaction.
    Running work observes cancellation at a cooperative checkpoint; any current
    inference step may finish, but its queue result is discarded.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT job_type, payload, status, started_at
                FROM public.job_queue
                WHERE id=%s
                FOR UPDATE
                """,
                (job_id,),
            )
            row = cur.fetchone()
            if row is None:
                return False

            job_type, payload, old_status, started_at = row
            if old_status not in {"PENDING", "RUNNING", "PAUSED"}:
                return False

            cur.execute(
                """
                UPDATE public.job_queue
                SET status='CANCELLED', finished_at=CURRENT_TIMESTAMP
                WHERE id=%s
                """,
                (job_id,),
            )

            # PENDING jobs have no worker. A paused DINO observes cancellation
            # at a cooperative checkpoint; closing its unfinished item rows
            # here also covers a worker that crashed while the queue row stayed
            # PAUSED. HYBRID currently has no control callback, so only close a
            # HYBRID row when its queue job has never been claimed.
            payload = payload or {}
            if (
                job_type == "DINO_BATCH"
                and old_status in {"PENDING", "PAUSED"}
                and payload.get("batch_id") is not None
            ):
                from app.dino.database import abort_batch_in_transaction

                abort_batch_in_transaction(
                    cur,
                    int(payload["batch_id"]),
                    "DINO job cancelled before completion",
                )
            elif (
                job_type == "HYBRID_RUN"
                and old_status in {"PENDING", "PAUSED"}
                and started_at is None
                and payload.get("hybrid_run_id") is not None
            ):
                from app.hybrid.database import fail_unstarted_run_in_transaction

                fail_unstarted_run_in_transaction(
                    cur, int(payload["hybrid_run_id"])
                )

            return True


def requeue_stale(
    *,
    older_than_minutes: int = 30,
    types: list[str] | None = None,
) -> int:
    """
    Return jobs stuck in RUNNING (older than the threshold) to PENDING.

    A crashed or killed worker can leave a claimed job RUNNING forever; this
    recovers it so another worker pass can pick it up. Returns how many jobs
    were requeued.
    """

    if older_than_minutes < 0:
        raise ValueError("older_than_minutes must be >= 0")

    type_clause = " AND job_type = ANY(%s)" if types else ""
    params: list[object] = [str(int(older_than_minutes))]
    if types:
        params.append(list(types))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.job_queue
                SET
                    status = 'PENDING',
                    started_at = NULL,
                    error_message = COALESCE(error_message || ' | ', '')
                        || 'requeued (stale RUNNING)'
                WHERE status = 'RUNNING'
                  AND started_at IS NOT NULL
                  AND started_at < CURRENT_TIMESTAMP
                        - (%s || ' minutes')::interval
                """ + type_clause,
                params,
            )
            return cur.rowcount


def clear_finished_jobs(
    job_type: str,
    *,
    statuses: tuple[str, ...] = ("DONE", "FAILED", "CANCELLED"),
) -> int:
    """
    Убрать завершённые задания одного вида — «очистить список».

    Сами описания живут в `photo_qwen`, поэтому удаление строк очереди ничего
    не теряет: пропадает только журнал выполнений. Активные задания
    (PENDING/RUNNING/PAUSED) не трогаем никогда.
    """

    if job_type not in JOB_TYPES:
        raise ValueError(f"unknown job type: {job_type}")

    allowed = {"DONE", "FAILED", "CANCELLED"}

    if not statuses or not set(statuses) <= allowed:
        raise ValueError("only finished statuses can be cleared")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM public.job_queue
                WHERE job_type = %s AND status = ANY(%s)
                """,
                (job_type, list(statuses)),
            )
            return cur.rowcount


def cancel_jobs(
    job_type: str,
    *,
    statuses: tuple[str, ...] = ("PENDING", "RUNNING", "PAUSED"),
) -> int:
    """
    Остановить активные задания одного вида — кнопка «Остановить».

    PENDING и PAUSED отменяются сразу. RUNNING получает CANCELLED и
    останавливается на ближайшей поддерживаемой контрольной точке; результат
    после отмены не публикуется.
    """

    if job_type not in JOB_TYPES:
        raise ValueError(f"unknown job type: {job_type}")

    allowed = {"PENDING", "RUNNING", "PAUSED"}

    if not statuses or not set(statuses) <= allowed:
        raise ValueError("only active statuses can be cancelled")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.job_queue
                SET status = 'CANCELLED', finished_at = CURRENT_TIMESTAMP
                WHERE job_type = %s AND status = ANY(%s)
                """,
                (job_type, list(statuses)),
            )
            return cur.rowcount


def mark_failed(job_id: int, error_message: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.job_queue
                SET status = 'FAILED',
                    error_message = %s,
                    finished_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status IN ('RUNNING', 'PAUSED')
                """,
                (str(error_message), job_id),
            )

            if cur.rowcount != 1:
                raise ValueError(
                    f"Cannot fail job {job_id}: not RUNNING"
                )
