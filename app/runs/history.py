"""Repository and lifecycle helpers for user-visible runs."""

from __future__ import annotations

import time
from typing import Any

from psycopg.types.json import Json

from app.ingest.database import get_connection
from app.runs import log_store

RUN_KINDS = {"pipeline", "ingest", "sort", "qwen", "scheduler"}
RUN_MODES = {"manual", "schedule", "outofqueue"}
RUN_STATUSES = {"PENDING", "RUNNING", "DONE", "FAILED", "PARTIAL", "STOPPED", "CANCELLED"}
_RUN_COLUMNS = (
    "run_id, kind, mode, status, source_id, parent_run_id, title, counts, "
    "stages, error_count, message, log_path, created_by, started_at, "
    "finished_at, created_at, updated_at, enqueue_complete"
)
_HISTORY_AVAILABLE: bool | None = None
_LAST_PRUNE_AT = 0.0


def available() -> bool:
    """Feature gate for rolling deploys: old DBs keep working before schema/037."""
    global _HISTORY_AVAILABLE
    if _HISTORY_AVAILABLE is not None:
        return _HISTORY_AVAILABLE
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.run_history')")
                _HISTORY_AVAILABLE = cur.fetchone()[0] is not None
    except Exception:
        _HISTORY_AVAILABLE = False
    return _HISTORY_AVAILABLE


def create_run(
    *,
    kind: str,
    mode: str = "manual",
    title: str = "",
    total: int = 0,
    counts: dict | None = None,
    source_id: str | int | None = None,
    parent_run_id: int | None = None,
    created_by: str | None = None,
    status: str = "PENDING",
    started: bool = False,
) -> int | None:
    if not available():
        return None
    _prune_logs_if_due()
    if kind not in RUN_KINDS:
        raise ValueError(f"unsupported run kind: {kind}")
    if mode not in RUN_MODES:
        raise ValueError(f"unsupported run mode: {mode}")
    if status not in RUN_STATUSES:
        raise ValueError(f"unsupported run status: {status}")

    initial_counts = dict(counts or {})
    initial_counts.setdefault("total", max(0, int(total)))
    initial_counts.setdefault("done", 0)
    initial_counts.setdefault("failed", 0)
    initial_counts.setdefault("cancelled", 0)
    initial_counts.setdefault("skipped", 0)
    initial_counts.setdefault("jobs_total", 0)
    initial_counts.setdefault("jobs_done", 0)
    initial_counts.setdefault("jobs_failed", 0)
    initial_counts.setdefault("jobs_cancelled", 0)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO public.run_history
                    (kind, mode, status, source_id, parent_run_id, title,
                     counts, created_by, started_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                        CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END)
                RETURNING run_id
                """,
                (
                    kind, mode, status,
                    str(source_id) if source_id is not None else None,
                    parent_run_id, str(title or ""), Json(initial_counts),
                    created_by, bool(started),
                ),
            )
            run_id = int(cur.fetchone()[0])

    append_log(run_id, [f"run created: kind={kind} mode={mode} title={title}"])
    return run_id


def _prune_logs_if_due() -> None:
    global _LAST_PRUNE_AT
    now = time.time()
    if now - _LAST_PRUNE_AT < 24 * 60 * 60:
        return
    _LAST_PRUNE_AT = now
    try:
        log_store.prune_stale(now=now)
    except OSError:
        # Retention must not prevent a user-visible run from being created.
        pass


def create_from_pipeline(pipeline_run: dict) -> int:
    counts = {"total": 0, "done": 0, "failed": 0, "cancelled": 0, "skipped": 0}
    return create_run(
        kind="pipeline",
        mode=pipeline_run.get("mode") or "manual",
        title="Обновление базы",
        source_id=pipeline_run["run_id"],
        created_by=pipeline_run.get("created_by"),
        status="RUNNING",
        started=True,
        counts=counts,
    )


def sync_pipeline(pipeline_run: dict) -> int | None:
    """Mirror a resumable pipeline run and its per-stage counters/timings."""
    if not available():
        return None
    pipeline_id = int(pipeline_run["run_id"])
    existing = find_run(kind="pipeline", source_id=pipeline_id)
    if existing is None:
        history_id = create_run(
            kind="pipeline",
            mode=pipeline_run.get("mode") or "manual",
            title="Обновление базы",
            source_id=pipeline_id,
            created_by=pipeline_run.get("created_by"),
            status="RUNNING" if pipeline_run.get("status") in ("RUNNING", "PENDING") else pipeline_run.get("status", "DONE"),
            started=bool(pipeline_run.get("started_at")),
        )
        existing = get_run(history_id) if history_id else None
        if existing is None:
            return None

    stages = pipeline_run.get("stages") or []
    stage_data = []
    by_stage = {}
    for stage in stages:
        started = stage.get("started_at")
        finished = stage.get("finished_at")
        seconds = None
        if started and finished:
            try:
                seconds = round((finished - started).total_seconds(), 3)
            except (TypeError, AttributeError):
                seconds = None
        item = {
            "stage": stage.get("stage"),
            "status": stage.get("status"),
            "total": int(stage.get("total_count") or 0),
            "done": int(stage.get("done_count") or 0),
            "failed": int(stage.get("failed_count") or 0),
            "seconds": seconds,
            "message": stage.get("message"),
        }
        stage_data.append(item)
        by_stage[str(item["stage"])] = item

    counts = {
        "total": sum(item["total"] for item in stage_data),
        "done": sum(item["done"] for item in stage_data),
        "failed": sum(item["failed"] for item in stage_data),
        "by_stage": by_stage,
    }
    status = pipeline_run.get("status") or "RUNNING"
    if status not in RUN_STATUSES:
        status = "RUNNING"
    terminal = status in {"DONE", "FAILED", "STOPPED", "CANCELLED"}
    message = pipeline_run.get("message")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.run_history
                SET mode=%s, status=%s, counts=%s, stages=%s, message=%s,
                    created_by=%s,
                    started_at=COALESCE(started_at,%s,CURRENT_TIMESTAMP),
                    finished_at=CASE WHEN %s THEN COALESCE(finished_at,%s,CURRENT_TIMESTAMP) ELSE NULL END,
                    updated_at=CURRENT_TIMESTAMP
                WHERE run_id=%s
                """,
                (
                    pipeline_run.get("mode") or existing["mode"], status,
                    Json(counts), Json(stage_data), message,
                    pipeline_run.get("created_by"), pipeline_run.get("started_at"),
                    terminal, pipeline_run.get("finished_at"), existing["run_id"],
                ),
            )
    changed = (existing["status"] != status or existing["message"] != message or existing["stages"] != stage_data)
    if changed:
        log_lines = [f"pipeline {pipeline_id}: {status}" ]
        if message:
            log_lines.append(f"message: {message}")
        for stage in stage_data:
            log_lines.append(
                f"stage {stage['stage']}: {stage['status']} "
                f"done={stage['done']}/{stage['total']} failed={stage['failed']} "
                f"seconds={stage['seconds']} message={stage['message'] or ''}"
            )
        child_jobs = []
        for stage in stages:
            ref = stage.get("ref") or {}
            if ref.get("job_id") is not None:
                child_jobs.append(int(ref["job_id"]))
        for job_id in dict.fromkeys(child_jobs):
            link_job(existing["run_id"], job_id)
        append_log(existing["run_id"], log_lines)
    return int(existing["run_id"])


def get_run(run_id: int) -> dict | None:
    if run_id is None or not available():
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_RUN_COLUMNS} FROM public.run_history WHERE run_id = %s", (int(run_id),))
            row = cur.fetchone()
    return _row(row) if row else None


def find_run(*, kind: str, source_id: str | int) -> dict | None:
    if not available():
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_RUN_COLUMNS} FROM public.run_history "
                "WHERE kind=%s AND source_id=%s ORDER BY run_id DESC LIMIT 1",
                (kind, str(source_id)),
            )
            row = cur.fetchone()
    return _row(row) if row else None


def list_runs(*, kind: str | None = None, limit: int = 20) -> list[dict]:
    if not available():
        return []
    limit = max(1, min(int(limit), 200))
    sql = f"SELECT {_RUN_COLUMNS} FROM public.run_history"
    params: list[Any] = []
    if kind is not None:
        if kind not in RUN_KINDS:
            raise ValueError(f"unsupported run kind: {kind}")
        sql += " WHERE kind = %s"
        params.append(kind)
    sql += " ORDER BY started_at DESC NULLS LAST, run_id DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [_row(row) for row in rows]


def link_job(run_id: int | None, job_id: int | None) -> None:
    if run_id is None or job_id is None or not available():
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.run_history_jobs(run_id, job_id) "
                "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (int(run_id), int(job_id)),
            )


def attach_job_to_source(*, kind: str, source_id: str | int, job_id: int | None) -> dict | None:
    """Attach a just-created batch/run job to its existing history row."""
    if job_id is None:
        return None
    run = find_run(kind=kind, source_id=source_id)
    if run is None:
        return None
    link_job(run["run_id"], job_id)
    update_run(run["run_id"], counts_delta={"jobs_total": 1}, status="RUNNING", start=True)
    return get_run(run["run_id"])


def add_jobs(run_id: int | None, job_ids: list[int], *, skipped: int = 0) -> None:
    if run_id is None:
        return
    run = get_run(run_id)
    if run is None:
        return
    for job_id in job_ids:
        link_job(run_id, job_id)
    deltas = {"jobs_total": len(job_ids)}
    if skipped:
        deltas["skipped"] = int(skipped)
    update_run(
        run_id,
        counts_delta=deltas,
        log_lines=[f"enqueued jobs: {len(job_ids)}; skipped/deduplicated: {skipped}"],
    )


def finish_enqueue(run_id: int | None, *, total: int, skipped: int = 0) -> None:
    """Mark that the caller finished enqueueing; zero-work runs finish now."""
    if run_id is None:
        return
    run = get_run(run_id)
    if run is None:
        return
    counts = dict(run["counts"])
    counts["total"] = max(0, int(total))
    counts["skipped"] = int(counts.get("skipped", 0)) + max(0, int(skipped))
    counts["enqueued"] = int(counts.get("jobs_total", 0))
    counts["untracked"] = max(0, int(counts["total"]) - int(counts["enqueued"]) - int(counts["skipped"]))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.run_history SET counts=%s, enqueue_complete=TRUE, "
                "status=CASE WHEN %s=0 AND %s=0 THEN 'DONE' ELSE 'RUNNING' END, "
                "started_at=COALESCE(started_at,CURRENT_TIMESTAMP), "
                "finished_at=CASE WHEN %s=0 AND %s=0 THEN CURRENT_TIMESTAMP ELSE finished_at END, "
                "updated_at=CURRENT_TIMESTAMP WHERE run_id=%s",
                (
                    Json(counts), int(counts.get("jobs_total", 0)), int(counts.get("total", 0)),
                    int(counts.get("jobs_total", 0)), int(counts.get("total", 0)), int(run_id),
                ),
            )
    if int(counts.get("jobs_total", 0)) == 0 and int(counts.get("total", 0)) == 0:
        append_log(run_id, ["run finished: no new jobs"])
    else:
        _finish_if_complete(run_id)


def update_run(
    run_id: int,
    *,
    status: str | None = None,
    counts_delta: dict[str, int] | None = None,
    error_count_delta: int = 0,
    message: str | None = None,
    stages: list[dict] | None = None,
    start: bool = False,
    finished: bool = False,
    log_lines: list[str] | None = None,
) -> dict | None:
    if status is not None and status not in RUN_STATUSES:
        raise ValueError(f"unsupported run status: {status}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT kind, status, counts, stages FROM public.run_history WHERE run_id = %s FOR UPDATE",
                (int(run_id),),
            )
            row = cur.fetchone()
            if row is None:
                return None
            kind, old_status, old_counts, old_stages = row
            counts = dict(old_counts or {})
            for key, delta in (counts_delta or {}).items():
                counts[key] = max(0, int(counts.get(key, 0)) + int(delta))
            new_status = status or old_status
            new_stages = stages if stages is not None else (old_stages or [])
            cur.execute(
                """
                UPDATE public.run_history
                SET status = %s, counts = %s, stages = %s,
                    error_count = GREATEST(0, error_count + %s),
                    message = COALESCE(%s, message),
                    started_at = CASE WHEN %s THEN COALESCE(started_at,CURRENT_TIMESTAMP) ELSE started_at END,
                    finished_at = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE finished_at END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                (
                    new_status, Json(counts), Json(new_stages), int(error_count_delta),
                    message, bool(start), bool(finished), int(run_id),
                ),
            )
    if log_lines:
        append_log(run_id, log_lines)
    if finished:
        _finish_if_complete(run_id)
    return get_run(int(run_id))


def record_job_start(run_id: int | None, job_id: int) -> None:
    if run_id is None:
        return
    run = get_run(run_id)
    if run is None:
        return
    update_run(run_id, status="RUNNING", start=True, log_lines=[f"job {job_id}: RUNNING"])


def record_job_result(
    run_id: int,
    *,
    job_type: str,
    job_id: int,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    run = get_run(run_id)
    if run is None:
        return
    link_job(run_id, job_id)
    result = result if isinstance(result, dict) else {}
    success = status == "DONE"
    cancelled = status == "CANCELLED"
    errors = _extract_errors(result)
    error_count = len(errors) if errors else (0 if success or cancelled else 1)

    delta = {
        "jobs_done": 1 if success else 0,
        "jobs_failed": 1 if status == "FAILED" else 0,
        "jobs_cancelled": 1 if cancelled else 0,
        "done": int(result.get("registered", result.get("done_count", 0)) or 0),
        "failed": int(result.get("failed_count", error_count) or 0),
    }
    lines = [f"job {job_id} {job_type}: {status}"]
    if error:
        lines.append(f"error: {error}")
    for item in errors[:200]:
        if isinstance(item, dict):
            lines.append(f"file {item.get('filename') or item.get('file') or '—'}: {item.get('error') or item.get('reason') or item}")
        else:
            lines.append(f"error: {item}")
    if not errors and result.get("error_message"):
        lines.append(f"error: {result['error_message']}")

    update_run(
        run_id,
        counts_delta=delta,
        error_count_delta=error_count,
        message=error if error else None,
        log_lines=lines,
    )
    _finish_if_complete(run_id)


def linked_run_ids(job_id: int) -> list[int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT run_id FROM public.run_history_jobs WHERE job_id=%s", (int(job_id),))
            return [int(row[0]) for row in cur.fetchall()]


def _finish_if_complete(run_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT h.kind, h.status, h.counts, h.error_count, h.enqueue_complete,
                       count(*) FILTER (WHERE j.status IN ('PENDING','RUNNING','PAUSED')) AS active,
                       count(*) FILTER (WHERE j.status='CANCELLED') AS cancelled
                FROM public.run_history AS h
                LEFT JOIN public.run_history_jobs AS l ON l.run_id=h.run_id
                LEFT JOIN public.job_queue AS j ON j.id=l.job_id
                WHERE h.run_id=%s
                GROUP BY h.run_id
                """,
                (int(run_id),),
            )
            row=cur.fetchone()
            if row is None:
                return
            kind, old_status, counts, errors, enqueue_complete, active, cancelled = row
            if not enqueue_complete or active or old_status in ("STOPPED", "CANCELLED", "PARTIAL", "FAILED"):
                return
            untracked = int(counts.get("untracked", 0))
            if cancelled and not errors:
                status = "STOPPED"
            elif errors or untracked:
                status = "PARTIAL" if counts.get("jobs_done", 0) else "FAILED"
            else:
                status = "DONE"
            cur.execute(
                "UPDATE public.run_history SET status=%s, finished_at=CURRENT_TIMESTAMP, "
                "updated_at=CURRENT_TIMESTAMP WHERE run_id=%s AND status NOT IN ('STOPPED','CANCELLED')",
                (status, int(run_id)),
            )
            kind = str(kind)
    append_log(run_id, [f"run finished: {status}"])


def append_log(run_id: int, lines: list[str]) -> None:
    run = get_run(run_id)
    if run is None:
        return
    relative = log_store.append_lines(run_id, run["kind"], lines)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.run_history SET log_path=%s, updated_at=CURRENT_TIMESTAMP WHERE run_id=%s",
                (relative, int(run_id)),
            )


def write_final_log(run_id: int, lines: list[str]) -> None:
    run = get_run(run_id)
    if run is None:
        return
    relative = log_store.publish_lines(run_id, run["kind"], lines)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE public.run_history SET log_path=%s WHERE run_id=%s", (relative, int(run_id)))


def read_run_log(run_id: int) -> str | None:
    """Read a log by its internal run id; never accept a client path."""
    run = get_run(run_id)
    if run is None:
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT log_path FROM public.run_history WHERE run_id=%s", (int(run_id),))
            row = cur.fetchone()
    if row is None or not row[0]:
        return None
    return log_store.read_log(str(row[0]))


def _extract_errors(result: dict) -> list:
    errors: list = []
    for key in ("errors", "conflicts"):
        value = result.get(key)
        if isinstance(value, list):
            errors.extend(value)
    videos = result.get("videos")
    if isinstance(videos, dict):
        value = videos.get("errors")
        if isinstance(value, list):
            errors.extend(value)
    return errors


def _row(row) -> dict:
    return {
        "run_id": int(row[0]),
        "kind": row[1],
        "mode": row[2],
        "status": row[3],
        "source_id": row[4],
        "parent_run_id": int(row[5]) if row[5] is not None else None,
        "title": row[6],
        "counts": row[7] or {},
        "stages": row[8] or [],
        "error_count": int(row[9] or 0),
        "message": row[10],
        "has_log": bool(row[11]),
        "created_by": row[12],
        "started_at": row[13],
        "finished_at": row[14],
        "created_at": row[15],
        "updated_at": row[16],
        "enqueue_complete": bool(row[17]),
    }
