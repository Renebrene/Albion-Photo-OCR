"""Serialization and read-only status for long-running media operations.

The resumable pipeline, the automation scheduler and manual DINO/HYBRID runs
all change recognition state. They must not launch on top of each other. The
state itself stays in the operational tables (pipeline_runs, run_history and
job_queue); this module only reads it and serializes the short launch phase
with a PostgreSQL advisory lock.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from app.ingest.database import get_connection

_LAUNCH_LOCK_KEY = 0x5CE7A0


class OperationBusy(RuntimeError):
    """Another launch is already in its short serialized section."""


@contextmanager
def launch_guard() -> Iterator[None]:
    """Serialize check-and-enqueue of a new pipeline/sort/scheduler operation."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (_LAUNCH_LOCK_KEY,))
            locked = bool(cur.fetchone()[0])

            if not locked:
                raise OperationBusy("another operation is starting")

            try:
                yield
            finally:
                cur.execute("SELECT pg_advisory_unlock(%s)", (_LAUNCH_LOCK_KEY,))


def active_operation() -> dict | None:
    """
    Return the operation currently changing recognition state, or None.

    Pipeline is checked first, then scheduler jobs with their history run, then
    a manual DINO/HYBRID job. This order labels shared job types correctly:
    pipeline and scheduler both create DINO_BATCH/QWEN_PHOTO jobs.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.pipeline_runs')")
            if cur.fetchone()[0] is not None:
                cur.execute(
                    """
                    SELECT run_id, mode, stage, started_at
                    FROM public.pipeline_runs
                    WHERE status IN ('PENDING', 'RUNNING')
                    ORDER BY run_id DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row is not None:
                    return {
                        "kind": "pipeline",
                        "run_id": int(row[0]),
                        "mode": row[1],
                        "stage": row[2],
                        "started_at": row[3],
                    }

            cur.execute(
                "SELECT to_regclass('public.run_history'), "
                "to_regclass('public.run_history_jobs'), "
                "to_regclass('public.job_queue')"
            )
            has_history, has_links, has_queue = cur.fetchone()

            if has_history is not None and has_links is not None and has_queue is not None:
                cur.execute(
                    """
                    SELECT h.run_id, h.started_at
                    FROM public.run_history AS h
                    JOIN public.run_history_jobs AS l ON l.run_id = h.run_id
                    JOIN public.job_queue AS j ON j.id = l.job_id
                    WHERE h.kind = 'scheduler'
                      AND h.status = 'RUNNING'
                      AND j.status IN ('PENDING', 'RUNNING', 'PAUSED')
                    GROUP BY h.run_id, h.started_at
                    ORDER BY h.run_id DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row is not None:
                    return {
                        "kind": "scheduler",
                        "run_id": int(row[0]),
                        "started_at": row[1],
                    }

            if has_queue is not None:
                cur.execute(
                    """
                    SELECT id, job_type, status, started_at
                    FROM public.job_queue
                    WHERE job_type IN ('DINO_BATCH', 'HYBRID_RUN')
                      AND status IN ('PENDING', 'RUNNING', 'PAUSED')
                    ORDER BY id
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row is not None:
                    return {
                        "kind": "sort",
                        "job_id": int(row[0]),
                        "job_type": row[1],
                        "status": row[2],
                        "started_at": row[3],
                    }

            # A DINO/HYBRID batch can be started directly by the runner rather
            # than through job_queue (the re-ingest path does exactly that).
            # The header must still show the current process and its progress.
            cur.execute(
                "SELECT to_regclass('public.dino_batches'), "
                "to_regclass('public.dino_runs'), "
                "to_regclass('public.hybrid_runs'), "
                "to_regclass('public.hybrid_results')"
            )
            has_batches, has_runs, has_hybrid, has_results = cur.fetchone()

            if has_batches is not None and has_runs is not None:
                cur.execute(
                    """
                    SELECT batch_id, status, total_count, started_at
                    FROM public.dino_batches
                    WHERE status IN ('PENDING', 'RUNNING')
                    ORDER BY batch_id DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row is not None:
                    cur.execute(
                        """
                        SELECT count(*) FILTER (WHERE status = 'DONE'),
                               count(*) FILTER (WHERE status = 'FAILED')
                        FROM public.dino_runs
                        WHERE batch_id = %s
                        """,
                        (row[0],),
                    )
                    done, failed = map(int, cur.fetchone())
                    return {
                        "kind": "sort",
                        "stage": "DINO",
                        "status": row[1],
                        "batch_id": int(row[0]),
                        "done": done + failed,
                        "failed": failed,
                        "total": int(row[2]),
                        "started_at": row[3],
                    }

            if has_hybrid is not None and has_results is not None:
                cur.execute(
                    """
                    SELECT hybrid_run_id, status, total_count, started_at
                    FROM public.hybrid_runs
                    WHERE status IN ('PENDING', 'RUNNING')
                    ORDER BY hybrid_run_id DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row is not None:
                    cur.execute(
                        """
                        SELECT count(*) FILTER (WHERE status = 'DONE'),
                               count(*) FILTER (WHERE status = 'FAILED')
                        FROM public.hybrid_results
                        WHERE hybrid_run_id = %s
                        """,
                        (row[0],),
                    )
                    done, failed = map(int, cur.fetchone())
                    return {
                        "kind": "sort",
                        "stage": "HYBRID",
                        "status": row[1],
                        "hybrid_run_id": int(row[0]),
                        "done": done + failed,
                        "failed": failed,
                        "total": int(row[2]),
                        "started_at": row[3],
                    }

    return None


def busy_message(operation: dict) -> str:
    """Human-readable reason for a 409 response or disabled UI control."""

    kind = operation.get("kind")
    if kind == "pipeline":
        stage = operation.get("stage")
        return f"идёт «Обновление базы» (стадия {stage})" if stage else "идёт «Обновление базы»"
    if kind == "scheduler":
        return "идёт тик планировщика"
    if kind == "sort":
        stage = operation.get("stage") or "DINO/HYBRID"
        total = int(operation.get("total") or 0)
        done = int(operation.get("done") or 0)
        if total:
            return f"идёт сортировка {stage}: {done} / {total}"
        return f"идёт сортировка {stage}"
    return "идёт другая операция"
