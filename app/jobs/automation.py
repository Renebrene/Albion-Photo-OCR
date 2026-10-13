"""
Automation scheduler (single-row `automation_settings`).

The scheduler is a thin orchestrator: it only *enqueues* jobs that the manual
flows already produce (a NORMAL DINO batch for photos never recognised, QWEN
metadata for photos missing it). It never reads a source folder, never ingests
new files and never deletes data. Disabled by default; enable explicitly.

Intended to be driven by `python -m app.jobs.worker --automation`, but a single
tick can also be triggered via POST /v1/automation/run.
"""

from __future__ import annotations

import datetime

from typing import Any

from app.dino import database as dino_db
from app.ingest.database import get_connection
from app.jobs import database as jobs_db

_SETTINGS_COLUMNS = (
    "enabled, interval_minutes, auto_dino, auto_qwen, last_tick, updated_at"
)


def _row_to_settings(row) -> dict:
    return {
        "enabled": bool(row[0]),
        "interval_minutes": int(row[1]),
        "auto_dino": bool(row[2]),
        "auto_qwen": bool(row[3]),
        "last_tick": row[4],
        "updated_at": row[5],
    }


def get_settings() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SETTINGS_COLUMNS} FROM public.automation_settings "  # noqa: S608
                "WHERE id = 1"
            )
            row = cur.fetchone()

    return _row_to_settings(row)


def update_settings(
    *,
    enabled: bool | None = None,
    interval_minutes: int | None = None,
    auto_dino: bool | None = None,
    auto_qwen: bool | None = None,
) -> dict:
    """Update only the supplied fields; return the resulting settings."""

    assignments: list[str] = []
    params: list[Any] = []

    if enabled is not None:
        assignments.append("enabled = %s")
        params.append(bool(enabled))
    if interval_minutes is not None:
        assignments.append("interval_minutes = %s")
        params.append(int(interval_minutes))
    if auto_dino is not None:
        assignments.append("auto_dino = %s")
        params.append(bool(auto_dino))
    if auto_qwen is not None:
        assignments.append("auto_qwen = %s")
        params.append(bool(auto_qwen))

    if assignments:
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.automation_settings SET "
                    + ", ".join(assignments)
                    + " WHERE id = 1",
                    params,
                )

    return get_settings()


def is_due(settings: dict) -> bool:
    """True when enough time passed since the last tick (or never ticked)."""

    if not settings["enabled"]:
        return False

    last = settings["last_tick"]

    if last is None:
        return True

    elapsed = datetime.datetime.now() - last
    return elapsed >= datetime.timedelta(minutes=settings["interval_minutes"])


def _photos_without_dino() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM public.photos AS p
                LEFT JOIN public.dino_runs AS r ON r.photo_id = p.photo_id
                WHERE r.photo_id IS NULL
                """
            )
            return int(cur.fetchone()[0])


def _photos_without_qwen() -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id
                FROM public.photos AS p
                LEFT JOIN public.photo_qwen AS q ON q.photo_id = p.photo_id
                WHERE q.photo_id IS NULL
                ORDER BY p.photo_id
                """
            )
            return [row[0] for row in cur.fetchall()]


# Advisory lock key so only one tick can create work at a time.
_TICK_LOCK_KEY = 0x5CE7E1


def run_tick(*, force: bool = False) -> dict:
    """
    Enqueue one round of automatic work.

    Serialized with a PostgreSQL advisory lock, so two workers (or a manual
    tick overlapping the loop) cannot both create the same DINO batch / QWEN
    jobs. Does nothing when disabled (unless *force*), when not yet due, or
    when there is nothing new to process.
    """

    settings = get_settings()

    if not settings["enabled"] and not force:
        return {"skipped": "disabled"}

    if not force and not is_due(settings):
        return {"skipped": "not_due"}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (_TICK_LOCK_KEY,))
            locked = bool(cur.fetchone()[0])

        if not locked:
            return {"skipped": "locked"}

        try:
            return _run_tick_locked(settings)
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (_TICK_LOCK_KEY,))


def _run_tick_locked(settings: dict) -> dict:
    result: dict = {"dino_batch_id": None, "qwen_jobs": 0}

    if settings["auto_dino"] and not dino_db.has_active_batch():
        if _photos_without_dino() > 0:
            batch = dino_db.create_batch("NORMAL")

            if batch.total_count > 0:
                jobs_db.enqueue("DINO_BATCH", {"batch_id": batch.batch_id})
                result["dino_batch_id"] = batch.batch_id
                result["dino_total"] = batch.total_count

    if settings["auto_qwen"]:
        created = 0

        for photo_id in _photos_without_qwen():
            if jobs_db.enqueue_qwen(photo_id) is not None:
                created += 1

        result["qwen_jobs"] = created

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.automation_settings "
                "SET last_tick = CURRENT_TIMESTAMP WHERE id = 1"
            )

    return result
