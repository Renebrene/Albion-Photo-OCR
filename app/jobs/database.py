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

JOB_TYPES = {"DINO_BATCH", "HYBRID_RUN", "QWEN_PHOTO"}

_JOB_COLUMNS = (
    "id, job_type, payload, status, attempts, "
    "result, error_message, created_at, started_at, finished_at"
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
    }


def enqueue(job_type: str, payload: dict[str, Any]) -> int:
    """Insert a PENDING job and return its id."""

    if job_type not in JOB_TYPES:
        raise ValueError(f"Unsupported job type: {job_type}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.job_queue (job_type, payload, status)
                VALUES (%s, %s, 'PENDING')
                RETURNING id
                """,
                (job_type, Json(payload)),
            )
            return int(cur.fetchone()[0])


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


def claim_next() -> dict | None:
    """
    Atomically move the oldest PENDING job to RUNNING.

    Returns the claimed job, or None when the queue is empty.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, job_type, payload
                FROM public.job_queue
                WHERE status = 'PENDING'
                ORDER BY id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
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
                  AND status = 'RUNNING'
                """,
                (str(error_message), job_id),
            )

            if cur.rowcount != 1:
                raise ValueError(
                    f"Cannot fail job {job_id}: not RUNNING"
                )
