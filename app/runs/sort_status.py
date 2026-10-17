"""
Virtual sorting status for the «Сортировка» tab.

Sources of truth stay in DINO/HYBRID tables and the unified run history; this
module only aggregates them for the status card:

* the last manual sort run with «совпадений X из Y»;
* the last run of each trigger: manual / schedule / out-of-queue;
* whether another pipeline operation is running right now.
"""

from __future__ import annotations

from app.ingest.database import get_connection
from app.runs import coordination, history


def _latest_run(*, kind: str | None = None, mode: str | None = None) -> dict | None:
    if not history.available():
        return None

    sql = """
        SELECT run_id, kind, mode, status, source_id, title, counts, stages,
               message, error_count, (log_path IS NOT NULL) AS has_log,
               started_at, finished_at
        FROM public.run_history
        WHERE TRUE
    """
    params: list[object] = []

    if kind is not None:
        sql += " AND kind = %s"
        params.append(kind)
    if mode is not None:
        sql += " AND mode = %s"
        params.append(mode)

    sql += " ORDER BY started_at DESC NULLS LAST, run_id DESC LIMIT 1"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "run_id": int(row[0]),
        "kind": row[1],
        "mode": row[2],
        "status": row[3],
        "source_id": row[4],
        "title": row[5],
        "counts": row[6] or {},
        "stages": row[7] or [],
        "message": row[8],
        "error_count": int(row[9] or 0),
        "has_log": bool(row[10]),
        "started_at": row[11],
        "finished_at": row[12],
    }


def _batch_stats(batch_id) -> dict | None:
    """Matched / total / failed for one DINO batch."""

    try:
        batch_id = int(batch_id)
    except (TypeError, ValueError):
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.total_count,
                       b.completed_count,
                       b.failed_count,
                       count(*) FILTER (
                           WHERE COALESCE(h.hybrid_final_id, r.dino_best_id)
                                 IS NOT NULL
                       ) AS matched
                FROM public.dino_batches AS b
                LEFT JOIN public.dino_runs AS r ON r.batch_id = b.batch_id
                LEFT JOIN LATERAL (
                    SELECT hr.hybrid_final_id
                    FROM public.hybrid_results AS hr
                    JOIN public.hybrid_runs AS run
                      ON run.hybrid_run_id = hr.hybrid_run_id
                    WHERE hr.photo_id = r.photo_id
                      AND hr.status = 'DONE'
                      -- Only this batch's own HYBRID runs: an old result must
                      -- not make a fresh batch look already matched.
                      AND run.dino_batch_id = b.batch_id
                    ORDER BY hr.finished_at DESC NULLS LAST,
                             hr.hybrid_run_id DESC
                    LIMIT 1
                ) AS h ON TRUE
                WHERE b.batch_id = %s
                GROUP BY b.batch_id
                """,
                (batch_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "batch_id": batch_id,
        "total": int(row[0] or 0),
        "done": int(row[1] or 0),
        "failed": int(row[2] or 0),
        "matched": int(row[3] or 0),
    }


def _batch_for_hybrid(hybrid_run_id) -> int | None:
    """The DINO batch a manual HYBRID sort belongs to."""

    try:
        hybrid_run_id = int(hybrid_run_id)
    except (TypeError, ValueError):
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT dino_batch_id FROM public.hybrid_runs "
                "WHERE hybrid_run_id = %s",
                (hybrid_run_id,),
            )
            row = cur.fetchone()

    return int(row[0]) if row is not None else None


def _sort_run_stats(run: dict) -> dict | None:
    """Stats for a «sort» history row (DINO batch or HYBRID run)."""

    source_id = run.get("source_id")
    title = run.get("title") or ""

    if title.startswith("HYBRID"):
        source_id = _batch_for_hybrid(source_id)

    return _batch_stats(source_id)


def _latest_pipeline_sort() -> dict | None:
    """
    DINO/HYBRID stage of the newest «Обновление базы».

    A pipeline run does not create a ``kind='sort'`` history row, but the
    Sorting tab must still show how many photos matched. The stage rows keep
    the batch id in ``ref``, which is enough to reuse ``_batch_stats``.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pr.run_id, pr.mode, pr.status,
                       dino.status, dino.ref, dino.started_at, dino.finished_at,
                       hybrid.status, hybrid.finished_at,
                       h.run_id, (h.log_path IS NOT NULL) AS has_log
                FROM public.pipeline_run_stages AS dino
                JOIN public.pipeline_runs AS pr ON pr.run_id = dino.run_id
                LEFT JOIN public.pipeline_run_stages AS hybrid
                       ON hybrid.run_id = dino.run_id
                      AND hybrid.stage = 'HYBRID'
                LEFT JOIN public.run_history AS h
                       ON h.kind = 'pipeline'
                      AND h.source_id = pr.run_id::text
                WHERE dino.stage = 'DINO'
                  AND dino.ref ? 'batch_id'
                ORDER BY pr.run_id DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

    if row is None:
        return None

    (
        pipeline_id, mode, pipeline_status,
        dino_status, ref, started_at, dino_finished,
        hybrid_status, hybrid_finished,
        history_id, has_log,
    ) = row

    try:
        batch_id = int((ref or {}).get("batch_id"))
    except (TypeError, ValueError):
        return None

    stats = _batch_stats(batch_id)

    if hybrid_status == "DONE":
        status = "DONE"
    elif hybrid_status in {"PENDING", "RUNNING", "FAILED", "STOPPED", "CANCELLED"}:
        status = hybrid_status
    elif dino_status in {"PENDING", "RUNNING", "FAILED", "STOPPED", "CANCELLED"}:
        status = dino_status
    elif pipeline_status in {"FAILED", "STOPPED", "CANCELLED"}:
        status = pipeline_status
    else:
        status = "DONE"

    counts = {
        "total": int((stats or {}).get("total") or 0),
        "done": int((stats or {}).get("done") or 0),
        "failed": int((stats or {}).get("failed") or 0),
    }

    return {
        "run_id": int(history_id) if history_id is not None else None,
        "kind": "pipeline",
        "mode": mode,
        "status": status,
        "source_id": batch_id,
        "title": "Обновление базы — DINO/HYBRID",
        "counts": counts,
        "stages": [],
        "message": None,
        "error_count": 0,
        "has_log": bool(has_log),
        "started_at": started_at,
        "finished_at": hybrid_finished or dino_finished,
        "stats": stats,
    }


def _started_key(run: dict) -> str:
    value = run.get("started_at")
    return str(value) if value is not None else ""


def _active_batch() -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT batch_id
                FROM public.dino_batches
                WHERE status IN ('PENDING', 'RUNNING')
                ORDER BY batch_id DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

    return _batch_stats(row[0]) if row is not None else None


def status() -> dict:
    manual = _latest_run(kind="sort", mode="manual")
    schedule = _latest_run(kind="scheduler")
    outofqueue = _latest_run(mode="outofqueue")
    any_sort = _latest_run(kind="sort")
    pipeline_sort = _latest_pipeline_sort()

    # The newest sorting event can come from the manual button, the scheduler
    # or the DINO/HYBRID stages of a full «Обновление базы» run.
    candidates = [
        run for run in (manual, any_sort, pipeline_sort) if run is not None
    ]
    last = max(candidates, key=_started_key) if candidates else None

    if last is not None and "stats" not in last:
        stats = _sort_run_stats(last)
        if stats is not None:
            last = {**last, "stats": stats}

    return {
        "last": last,
        "modes": {
            "manual": manual,
            "schedule": schedule,
            "outofqueue": outofqueue,
            "pipeline": pipeline_sort,
        },
        "current": _active_batch(),
        "active": coordination.active_operation(),
    }
