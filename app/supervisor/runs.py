"""
Resumable pipeline supervisor.

One *run* walks the fixed stages INGEST -> PREVIEW -> DINO -> HYBRID -> QWEN.
The supervisor is a thin, stateless orchestrator: on every tick it looks at the
run row, enqueues the child work the manual flows already produce (INGEST_DIR,
PHOTO_PREVIEW, DINO_BATCH, HYBRID_RUN, QWEN_PHOTO) and advances to the next
stage when that work is finished. It never runs inference, never reads or
writes source media itself, and never rewrites the DINO/HYBRID/QWEN runners.

Design points that matter:

* **Immutable input snapshot.** When INGEST starts, the folder listing is frozen
  in ``manifest["files"]`` and, once INGEST completes, a ``photo_cutoff``
  timestamp is recorded. A run that is stopped and later *resumed* therefore
  never picks up media that appeared while it was stopped. A *restart*
  (``Заново``) is a brand-new run with a fresh snapshot; steps that are already
  done are skipped by the existing idempotency (registered files, valid
  previews, DONE DINO runs, existing QWEN rows).
* **Cooperative stop.** ``request_stop`` only sets a flag; the next tick marks
  the run STOPPED. Child jobs already in flight finish on their own — the
  supervisor does not kill an in-progress DINO/QWEN step.
* **Single active run** is enforced by a partial unique index (PENDING/RUNNING);
  starting a new run supersedes a stopped one.
"""

from __future__ import annotations

import logging
from typing import Any

from psycopg.types.json import Json

from app.dino import database as dino_db
from app.hybrid import database as hybrid_db
from app.ingest.database import get_connection
from app.jobs import database as jobs_db

logger = logging.getLogger(__name__)
from app.preview.queue import enqueue_missing_previews

STAGES: tuple[str, ...] = ("INGEST", "PREVIEW", "DINO", "HYBRID", "QWEN")
MODES = ("manual", "schedule", "outofqueue")
_ACTIVE = ("PENDING", "RUNNING")

# Advisory-lock key base so one tick per run is serialised across workers.
_LOCK_BASE = 0x5CE7_2000

_RUN_COLUMNS = (
    "run_id, mode, status, stage, stop_requested, folder, manifest, counts, "
    "message, created_by, created_at, started_at, finished_at, updated_at"
)
_STAGE_COLUMNS = (
    "run_id, stage, position, status, total_count, done_count, failed_count, "
    "ref, message, started_at, finished_at"
)


class PipelineBusy(RuntimeError):
    """Raised when a run is already active and a second one is requested."""


def _run_row(row) -> dict:
    return {
        "run_id": int(row[0]),
        "mode": str(row[1]),
        "status": str(row[2]),
        "stage": str(row[3]),
        "stop_requested": bool(row[4]),
        "folder": row[5],
        "manifest": row[6] or {},
        "counts": row[7] or {},
        "message": row[8],
        "created_by": row[9],
        "created_at": row[10],
        "started_at": row[11],
        "finished_at": row[12],
        "updated_at": row[13],
    }


def _stage_row(row) -> dict:
    return {
        "run_id": int(row[0]),
        "stage": str(row[1]),
        "position": int(row[2]),
        "status": str(row[3]),
        "total_count": int(row[4]),
        "done_count": int(row[5]),
        "failed_count": int(row[6]),
        "ref": row[7] or {},
        "message": row[8],
        "started_at": row[9],
        "finished_at": row[10],
    }


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def get_run(run_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_RUN_COLUMNS} FROM public.pipeline_runs WHERE run_id = %s",  # noqa: S608
                (int(run_id),),
            )
            row = cur.fetchone()

    return _run_row(row) if row is not None else None


def get_stages(run_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_STAGE_COLUMNS} FROM public.pipeline_run_stages "  # noqa: S608
                "WHERE run_id = %s ORDER BY position",
                (int(run_id),),
            )
            rows = cur.fetchall()

    return [_stage_row(row) for row in rows]


def get_run_with_stages(run_id: int) -> dict | None:
    run = get_run(run_id)
    if run is None:
        return None
    run["stages"] = get_stages(run_id)
    return run


def active_run() -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_RUN_COLUMNS} FROM public.pipeline_runs "  # noqa: S608
                "WHERE status IN ('PENDING', 'RUNNING') ORDER BY run_id DESC LIMIT 1"
            )
            row = cur.fetchone()

    return _run_row(row) if row is not None else None


def latest_run() -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_RUN_COLUMNS} FROM public.pipeline_runs "  # noqa: S608
                "ORDER BY run_id DESC LIMIT 1"
            )
            row = cur.fetchone()

    return _run_row(row) if row is not None else None


def list_runs(*, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_RUN_COLUMNS} FROM public.pipeline_runs "  # noqa: S608
                "ORDER BY run_id DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()

    return [_run_row(row) for row in rows]


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def create_run(
    *,
    mode: str = "manual",
    folder: str | None = None,
    created_by: str | None = None,
    skip_qwen: bool = False,
) -> dict:
    """
    Start a new run, superseding any stopped run.

    Raises PipelineBusy when a PENDING/RUNNING run already exists (enforced by
    the partial unique index as well, so two concurrent callers cannot both
    win).
    """

    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")

    from psycopg import errors as pg_errors

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.pipeline_runs
                    SET status = 'SUPERSEDED',
                        finished_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE status = 'STOPPED'
                    """
                )
                cur.execute(
                    """
                    INSERT INTO public.pipeline_runs
                        (mode, status, stage, folder, created_by, manifest,
                         started_at)
                    VALUES (%s, 'RUNNING', 'INGEST', %s, %s, %s,
                            CURRENT_TIMESTAMP)
                    RETURNING run_id
                    """,
                    (
                        mode,
                        folder,
                        created_by,
                        Json({"skip_qwen": True}) if skip_qwen else Json({}),
                    ),
                )
                run_id = int(cur.fetchone()[0])
                for position, stage in enumerate(STAGES):
                    cur.execute(
                        """
                        INSERT INTO public.pipeline_run_stages
                            (run_id, stage, position)
                        VALUES (%s, %s, %s)
                        """,
                        (run_id, stage, position),
                    )
    except pg_errors.UniqueViolation as exc:  # pragma: no cover - race path
        raise PipelineBusy("pipeline run already active") from exc

    result = get_run_with_stages(run_id)
    try:
        from app.runs import history as run_history

        run_history.sync_pipeline(result)
    except Exception as exc:  # noqa: BLE001 - history is observational
        logger.warning("pipeline history sync failed (%s)", type(exc).__name__)
    return result


def request_stop(run_id: int) -> bool:
    """Ask the supervisor to stop the run at the next tick (cooperative)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.pipeline_runs
                SET stop_requested = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE run_id = %s AND status IN ('PENDING', 'RUNNING')
                """,
                (int(run_id),),
            )
            changed = cur.rowcount == 1

    # A run whose current stage is not in flight stops immediately; a stage that
    # is RUNNING waits for the next tick (in-flight child jobs finish on their
    # own, the supervisor does not kill them).
    if changed:
        run = get_run(run_id)
        raw = _raw_stage(run_id, run["stage"]) if run is not None else None
        if raw is not None and _stage_row(raw)["status"] in ("PENDING", "DONE", "SKIPPED"):
            _finish_run(run_id, "STOPPED", message="остановлено пользователем")
        _sync_history(run_id)

    return changed


def resume_run(run_id: int) -> bool:
    """Resume a STOPPED run; refuses when another run is active."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM public.pipeline_runs "
                "WHERE status IN ('PENDING', 'RUNNING') AND run_id <> %s",
                (int(run_id),),
            )
            if cur.fetchone() is not None:
                raise PipelineBusy("another pipeline run is active")
            cur.execute(
                """
                UPDATE public.pipeline_runs
                SET status = 'RUNNING',
                    stop_requested = FALSE,
                    finished_at = NULL,
                    message = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE run_id = %s AND status = 'STOPPED'
                """,
                (int(run_id),),
            )
            changed = cur.rowcount == 1

    if changed:
        # Jobs paused by the stop go back to PENDING; the run continues from
        # the same stage and does not redo finished work.
        jobs_db.resume_paused_for_pipeline(run_id)
        _sync_history(run_id)
    return changed


# ---------------------------------------------------------------------------
# Ticking
# ---------------------------------------------------------------------------


def tick(run_id: int | None = None) -> dict:
    """Advance the active run (or the given one) by one step."""

    run = get_run(run_id) if run_id is not None else active_run()

    if run is None:
        return {"skipped": "no run"}
    if run["status"] not in _ACTIVE:
        return {"skipped": f"status {run['status']}"}

    lock = _LOCK_BASE + int(run["run_id"])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (lock,))
            if not cur.fetchone()[0]:
                return {"skipped": "locked"}

        try:
            result = _advance(int(run["run_id"]))
            _sync_history(int(run["run_id"]))
            return result
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (lock,))


def _advance(run_id: int) -> dict:
    run = get_run(run_id)

    if run is None or run["status"] not in _ACTIVE:
        return {"skipped": "no active run"}

    if run["stop_requested"]:
        # Pause the run's queued child jobs: otherwise PREVIEW/QWEN jobs keep
        # the workers busy long after the run is marked STOPPED. Jobs already
        # running finish on their own, as documented.
        paused = jobs_db.pause_pending_for_pipeline(
            run_id,
            run.get("started_at") or run.get("created_at"),
        )
        _finish_run(
            run_id,
            "STOPPED",
            message=f"остановлено пользователем; заданий приостановлено: {paused}",
        )
        return {"outcome": "STOPPED"}

    # QWEN may have been started right after INGEST and runs in parallel with
    # DINO/HYBRID: keep its stage counters fresh for the UI.
    _sync_qwen_progress(run)

    stage = run["stage"]
    row = _stage_row(_raw_stage(run_id, stage))
    outcome = _HANDLERS[stage](run, row)
    result = outcome.get("outcome")

    if result == "WAIT":
        _apply_progress(run_id, stage, outcome)
        return {"outcome": "WAIT", "stage": stage, "progress": outcome}

    if result in ("DONE", "SKIPPED"):
        _complete_stage(run_id, stage, outcome)
        nxt = _next_stage(stage)

        if nxt is None:
            _finish_run(run_id, "DONE", message="база обновлена")
            return {"outcome": "DONE", "stage": stage}

        _update_run(run_id, stage=nxt)
        return {"outcome": "ADVANCED", "stage": nxt}

    message = outcome.get("message")
    _fail_stage(run_id, stage, message)
    _finish_run(run_id, "FAILED", message=message)
    return {"outcome": "FAILED", "stage": stage, "message": message}


# ---------------------------------------------------------------------------
# Stage handlers
# ---------------------------------------------------------------------------


def _qwen_in_pipeline() -> bool:
    """Настройка «Запускать QWEN в обновлении базы» (по умолчанию включена)."""

    try:
        from app.qwen import processor as qwen_processor

        return bool(qwen_processor.in_pipeline())
    except Exception:  # noqa: BLE001 - без настроек считаем QWEN включённым
        return True


def _auto_qwen_enabled() -> bool:
    """Planner setting «Запускать QWEN автоматически» (off by default)."""

    try:
        from app.jobs import automation

        return bool(automation.get_settings().get("auto_qwen"))
    except Exception:  # noqa: BLE001 - a settings read must not break the run
        return False


def _enqueue_early_qwen(run: dict, manifest: dict) -> None:
    """
    Start QWEN right after INGEST (IDs exist), in parallel with sorting.

    The set is frozen by `photo_cutoff`, the same set DINO will use, so files
    added later wait for the next run.
    """

    if (
        manifest.get("skip_qwen")
        or manifest.get("qwen_early")
        or not _qwen_in_pipeline()
        or not _auto_qwen_enabled()
    ):
        return

    manifest["qwen_early"] = True
    photo_ids = _photos_without_qwen(manifest.get("photo_cutoff"))

    if not photo_ids:
        return

    history_id = None

    try:
        from app.runs import history

        found = history.find_run(kind="pipeline", source_id=int(run["run_id"]))

        if found:
            history_id = int(found["run_id"])
    except Exception:  # noqa: BLE001 - history is an index, not the source
        history_id = None

    for photo_id in photo_ids:
        jobs_db.enqueue_qwen(
            photo_id, source="pipeline", run_history_id=history_id
        )

    _set_stage(
        run["run_id"], "QWEN",
        status="RUNNING", started_at_sql=True, total_count=len(photo_ids),
    )


def _sync_qwen_progress(run: dict) -> None:
    """Keep the parallel QWEN stage counters current while sorting runs."""

    if not (run.get("manifest") or {}).get("qwen_early"):
        return

    if run.get("stage") == "QWEN":
        return

    cutoff = _cutoff(run)

    _set_stage(
        run["run_id"], "QWEN",
        done_count=_qwen_count(cutoff, "DONE"),
        failed_count=_qwen_count(cutoff, "FAILED"),
        total_count=_photos_total(cutoff),
    )


def _stage_ingest(run: dict, stage: dict) -> dict:
    folder = run["folder"]

    if not folder:
        return {"outcome": "SKIPPED", "message": "папка не задана"}

    manifest = dict(run["manifest"] or {})

    if stage["status"] == "PENDING":
        if "files" not in manifest:
            try:
                manifest["files"] = _snapshot_files(folder)
            except OSError as exc:
                return {"outcome": "FAILED", "message": f"не удалось прочитать папку: {exc}"}

        job_id = jobs_db.enqueue_ingest(folder, only_files=manifest.get("files"))

        if job_id is None:
            job_id = _find_active_job("INGEST_DIR", "directory", folder)

        _set_stage(
            run["run_id"], "INGEST",
            status="RUNNING",
            started_at_sql=True,
            ref={"job_id": job_id},
            total_count=len(manifest.get("files") or []),
        )
        _update_run(run["run_id"], manifest=manifest)
        return {"outcome": "WAIT"}

    job_id = (stage["ref"] or {}).get("job_id")

    if job_id is None:
        return {"outcome": "DONE"}

    job = jobs_db.get_job(int(job_id))

    if job is None:
        return {"outcome": "WAIT"}

    if job["status"] == "DONE":
        result = job["result"] or {}
        manifest["photo_cutoff"] = _db_now()

        # Auto-QWEN starts as soon as the IDs exist, in parallel with the
        # sorting stages. Disabled by default in the planner settings.
        _enqueue_early_qwen(run, manifest)

        _update_run(run["run_id"], manifest=manifest)
        return {
            "outcome": "DONE",
            "message": None,
            "counts": {
                "discovered": result.get("discovered"),
                "registered": result.get("registered"),
                "existing": result.get("existing"),
            },
            "total_count": int(result.get("discovered") or 0),
            "done_count": int(result.get("registered") or 0),
        }

    if job["status"] in ("FAILED", "CANCELLED"):
        return {"outcome": "FAILED", "message": job.get("error_message") or job["status"]}

    # Surface the child job's live progress so the UI can show "обработано x/y".
    prog = job.get("progress") or {}
    done = prog.get("done")
    total = prog.get("total")

    if isinstance(done, int) and isinstance(total, int):
        return {"outcome": "WAIT", "done_count": done, "total_count": total}

    return {"outcome": "WAIT"}


def _stage_preview(run: dict, stage: dict) -> dict:
    cutoff = _cutoff(run)

    if stage["status"] == "PENDING":
        enqueue_missing_previews(limit=2000)
        total = _photos_total(cutoff)
        _set_stage(
            run["run_id"], "PREVIEW",
            status="RUNNING", started_at_sql=True, total_count=total,
        )

    active = _active_type_count("PHOTO_PREVIEW")
    done = _preview_ready_count(cutoff)
    total = _photos_total(cutoff)

    if active == 0:
        return {"outcome": "DONE", "total_count": total, "done_count": done}

    return {"outcome": "WAIT", "total_count": total, "done_count": done}


def _stage_dino(run: dict, stage: dict) -> dict:
    cutoff = _cutoff(run)
    ref = stage["ref"] or {}

    if stage["status"] == "PENDING":
        photo_ids = _photos_without_dino(cutoff)
        skipped = _photos_without_preview(cutoff)

        if not photo_ids:
            return {
                "outcome": "SKIPPED",
                "message": _dino_message("нет фото без DINO", 0, skipped),
            }

        batch = dino_db.create_batch("NORMAL", photo_ids)
        job_id = (
            jobs_db.enqueue("DINO_BATCH", {"batch_id": batch.batch_id})
            if batch.total_count
            else None
        )
        _set_stage(
            run["run_id"], "DINO",
            status="RUNNING", started_at_sql=True,
            ref={"batch_id": batch.batch_id, "job_id": job_id, "attempt": 1},
            total_count=batch.total_count,
            message=_dino_message(None, 0, skipped),
        )
        return {"outcome": "WAIT", "total_count": batch.total_count}

    batch_id = ref.get("batch_id")

    if batch_id is None:
        return {"outcome": "SKIPPED", "message": "нет batch"}

    batch = dino_db.get_batch(int(batch_id))
    status = batch.status
    skipped = _photos_without_preview(cutoff)
    counts = _batch_run_counts(int(batch_id))

    if status == "FAILED":
        # A batch where nothing was recognised is not HYBRID input. Retry once
        # over what is still missing: a transient model/host failure should not
        # end the whole run, and unreadable files already failed individually.
        attempt = int(ref.get("attempt") or 1)
        retry_ids = _photos_without_dino(cutoff) if attempt < 2 else []

        if not retry_ids:
            return {
                "outcome": "FAILED",
                "message": _dino_message(
                    "DINO batch failed", counts["failed"], skipped
                ),
            }

        retry = dino_db.create_batch("NORMAL", retry_ids)
        job_id = (
            jobs_db.enqueue("DINO_BATCH", {"batch_id": retry.batch_id})
            if retry.total_count
            else None
        )
        _set_stage(
            run["run_id"], "DINO",
            ref={"batch_id": retry.batch_id, "job_id": job_id, "attempt": attempt + 1},
            total_count=retry.total_count,
        )
        logger.warning(
            "DINO batch %s failed; retrying as batch %s (%s фото)",
            batch_id, retry.batch_id, retry.total_count,
        )
        return {"outcome": "WAIT"}

    if status == "DONE":
        return {
            "outcome": "DONE",
            "total_count": batch.total_count,
            "done_count": batch.completed_count,
            "failed_count": batch.failed_count,
            "message": _dino_message(None, batch.failed_count, skipped),
        }

    return {
        "outcome": "WAIT",
        "total_count": batch.total_count,
        "done_count": counts["done"],
        "failed_count": counts["failed"],
        "message": _dino_message(None, counts["failed"], skipped),
    }


def _stage_hybrid(run: dict, stage: dict) -> dict:
    if stage["status"] == "PENDING":
        dino_stage = _stage_row(_raw_stage(run["run_id"], "DINO"))
        batch_id = (dino_stage["ref"] or {}).get("batch_id")

        if batch_id is None:
            return {"outcome": "SKIPPED", "message": "нет DINO batch"}

        hybrid, job_id, _history_id = hybrid_db.create_and_enqueue_run(
            int(batch_id)
        )
        _set_stage(
            run["run_id"], "HYBRID",
            status="RUNNING", started_at_sql=True,
            ref={"hybrid_run_id": hybrid.hybrid_run_id, "job_id": job_id},
            total_count=hybrid.total_count,
        )
        return {"outcome": "WAIT"}

    hybrid_run_id = (stage["ref"] or {}).get("hybrid_run_id")

    if hybrid_run_id is None:
        return {"outcome": "SKIPPED", "message": "нет HYBRID run"}

    hybrid = hybrid_db.get_run(int(hybrid_run_id))
    status = hybrid.status

    if status == "DONE":
        return {
            "outcome": "DONE",
            "total_count": hybrid.total_count,
            "done_count": hybrid.completed_count,
        }
    if status == "FAILED":
        return {"outcome": "FAILED", "message": "HYBRID run failed"}

    return {
        "outcome": "WAIT",
        "total_count": hybrid.total_count,
        "done_count": hybrid.completed_count,
        "failed_count": hybrid.failed_count,
    }


def _stage_qwen(run: dict, stage: dict) -> dict:
    # QWEN выключается двумя способами: разово галочкой в окне запуска
    # (`skip_qwen` в манифесте) или постоянно в настройках распознавания
    # (`qwen_in_pipeline`). В обоих случаях прогон идёт без описаний, а
    # «Уточнение» не запускается — сравнивать нечего.
    if (run.get("manifest") or {}).get("skip_qwen") or not _qwen_in_pipeline():
        return {
            "outcome": "SKIPPED",
            "total_count": 0,
            "done_count": 0,
            "failed_count": 0,
            "message": (
                "QWEN пропущен — запустите отдельно за период "
                "(POST /v1/jobs/qwen/scan)"
            ),
        }

    cutoff = _cutoff(run)

    if stage["status"] == "PENDING":
        photo_ids = _photos_without_qwen(cutoff)

        for photo_id in photo_ids:
            jobs_db.enqueue_qwen(photo_id, source="pipeline")

        _set_stage(
            run["run_id"], "QWEN",
            status="RUNNING", started_at_sql=True, total_count=len(photo_ids),
        )

    active = _active_type_count("QWEN_PHOTO")
    done = _qwen_count(cutoff, "DONE")
    failed = _qwen_count(cutoff, "FAILED")
    total = _photos_total(cutoff)

    if active == 0:
        message = f"ошибок: {failed}" if failed else None
        return {
            "outcome": "DONE",
            "total_count": total,
            "done_count": done,
            "failed_count": failed,
            "message": message,
        }

    return {
        "outcome": "WAIT",
        "total_count": total,
        "done_count": done,
        "failed_count": failed,
    }


_HANDLERS = {
    "INGEST": _stage_ingest,
    "PREVIEW": _stage_preview,
    "DINO": _stage_dino,
    "HYBRID": _stage_hybrid,
    "QWEN": _stage_qwen,
}


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------


def _next_stage(stage: str) -> str | None:
    index = STAGES.index(stage)
    return STAGES[index + 1] if index + 1 < len(STAGES) else None


def _cutoff(run: dict) -> str | None:
    return (run["manifest"] or {}).get("photo_cutoff")


def _raw_stage(run_id: int, stage: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_STAGE_COLUMNS} FROM public.pipeline_run_stages "  # noqa: S608
                "WHERE run_id = %s AND stage = %s",
                (int(run_id), stage),
            )
            return cur.fetchone()


def _update_run(run_id: int, **fields) -> None:
    allowed = {"stage", "status", "manifest", "counts", "message", "stop_requested"}
    assignments = []
    params: list[Any] = []

    for key, value in fields.items():
        if key not in allowed:
            raise ValueError(f"cannot update {key}")
        assignments.append(f"{key} = %s")
        params.append(Json(value) if key in ("manifest", "counts") else value)

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    params.append(int(run_id))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.pipeline_runs SET "
                + ", ".join(assignments)
                + " WHERE run_id = %s",
                params,
            )


def _set_stage(run_id: int, stage: str, **fields) -> None:
    allowed = {
        "status", "total_count", "done_count", "failed_count",
        "ref", "message", "finished_at_sql", "started_at_sql",
    }
    assignments = []
    params: list[Any] = []

    for key, value in fields.items():
        if key not in allowed:
            raise ValueError(f"cannot update stage {key}")
        if key == "finished_at_sql":
            assignments.append("finished_at = CURRENT_TIMESTAMP")
            continue
        if key == "started_at_sql":
            if value:
                assignments.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
            continue
        if key == "ref":
            assignments.append("ref = %s")
            params.append(Json(value))
            continue
        assignments.append(f"{key} = %s")
        params.append(value)

    params.extend([int(run_id), stage])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.pipeline_run_stages SET "
                + ", ".join(assignments)
                + " WHERE run_id = %s AND stage = %s",
                params,
            )


def _complete_stage(run_id: int, stage: str, outcome: dict) -> None:
    _set_stage(
        run_id, stage,
        status="DONE" if outcome.get("outcome") == "DONE" else "SKIPPED",
        total_count=int(outcome.get("total_count") or 0),
        done_count=int(outcome.get("done_count") or 0),
        failed_count=int(outcome.get("failed_count") or 0),
        message=outcome.get("message"),
        finished_at_sql=True,
    )


def _fail_stage(run_id: int, stage: str, message: str | None) -> None:
    _set_stage(
        run_id, stage,
        status="FAILED", message=message, finished_at_sql=True,
    )


def _apply_progress(run_id: int, stage: str, outcome: dict) -> None:
    """Record in-flight counts so the UI can show progress before completion."""

    fields = {}
    for key in ("total_count", "done_count", "failed_count"):
        if outcome.get(key) is not None:
            fields[key] = int(outcome[key])
    if outcome.get("message") is not None:
        fields["message"] = outcome["message"]
    if fields:
        _set_stage(run_id, stage, **fields)


def _finish_run(run_id: int, status: str, *, message: str | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.pipeline_runs
                SET status = %s,
                    message = COALESCE(%s, message),
                    finished_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                (status, message, int(run_id)),
            )
    _sync_history(run_id)


def _sync_history(run_id: int) -> None:
    try:
        from app.runs import history as run_history

        snapshot = get_run_with_stages(run_id)
        if snapshot is not None:
            run_history.sync_pipeline(snapshot)
    except Exception as exc:  # noqa: BLE001 - history is observational
        logger.warning("pipeline history sync failed (%s)", type(exc).__name__)


# ---------------------------------------------------------------------------
# Small queries
# ---------------------------------------------------------------------------


def _db_now() -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT CURRENT_TIMESTAMP::timestamp")
            value = cur.fetchone()[0]
    return value.isoformat(sep=" ")


def _snapshot_files(folder: str) -> list[str]:
    from app.ingest.integrity import discover_files
    from app.ingest.video_integrity import discover_video_files
    from pathlib import Path

    root = Path(folder)
    names: list[str] = []

    for path in list(discover_files(folder, recursive=True)) + list(
        discover_video_files(folder, recursive=True)
    ):
        try:
            names.append(str(Path(path).relative_to(root)))
        except ValueError:
            names.append(Path(path).name)

    return sorted(set(names))


def _find_active_job(job_type: str, key: str, value: str) -> int | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM public.job_queue
                WHERE job_type = %s
                  AND status IN ('PENDING', 'RUNNING', 'PAUSED')
                  AND payload ->> %s = %s
                ORDER BY id DESC LIMIT 1
                """,
                (job_type, key, value),
            )
            row = cur.fetchone()
    return int(row[0]) if row is not None else None


def _active_type_count(job_type: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM public.job_queue "
                "WHERE job_type = %s AND status IN ('PENDING', 'RUNNING', 'PAUSED')",
                (job_type,),
            )
            return int(cur.fetchone()[0])


def _cutoff_clause(cutoff: str | None) -> tuple[str, list[Any]]:
    if cutoff is None:
        return "", []
    return " AND p.created_at <= %s::timestamp", [cutoff]


def _photos_total(cutoff: str | None) -> int:
    clause, params = _cutoff_clause(cutoff)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM public.photos AS p WHERE TRUE" + clause,
                params,
            )
            return int(cur.fetchone()[0])


def _preview_ready_count(cutoff: str | None) -> int:
    clause, params = _cutoff_clause(cutoff)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM public.photos AS p
                JOIN public.photo_previews AS r ON r.photo_id = p.photo_id
                WHERE r.small_path IS NOT NULL AND r.middle_path IS NOT NULL
                """ + clause,
                params,
            )
            return int(cur.fetchone()[0])


def _photos_without_dino(cutoff: str | None) -> list[str]:
    """Фото для DINO: нет готового результата и есть превью-вход.

    DINO работает по MIDDLE-превью. Фото без превью — это либо битый файл,
    либо не удавшееся превью; в батч они не попадают (иначе батч всегда
    заканчивается сбоем на одном нечитаемом файле). Их количество отдельно
    показывается в сообщении стадии.
    """

    clause, params = _cutoff_clause(cutoff)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id
                FROM public.photos AS p
                WHERE EXISTS (
                    SELECT 1 FROM public.photo_previews AS v
                    WHERE v.photo_id = p.photo_id
                )
                  AND NOT EXISTS (
                    SELECT 1 FROM public.dino_runs AS r
                    WHERE r.photo_id = p.photo_id AND r.status = 'DONE'
                  )
                """ + clause + " ORDER BY p.photo_id",
                params,
            )
            return [row[0] for row in cur.fetchall()]


def _photos_without_preview(cutoff: str | None) -> int:
    """Сколько фото прогона остались без превью — они вне DINO."""

    clause, params = _cutoff_clause(cutoff)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM public.photos AS p
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.photo_previews AS v
                    WHERE v.photo_id = p.photo_id
                )
                """ + clause,
                params,
            )
            return int(cur.fetchone()[0])


def _batch_run_counts(batch_id: int) -> dict:
    """Живые счётчики батча: dino_batches обновляется только на финише."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FILTER (WHERE status = 'DONE'),
                       COUNT(*) FILTER (WHERE status = 'FAILED')
                FROM public.dino_runs
                WHERE batch_id = %s
                """,
                (int(batch_id),),
            )
            done, failed = map(int, cur.fetchone())

    return {"done": done, "failed": failed}


def _dino_message(prefix: str | None, failed: int, skipped: int) -> str | None:
    """Сообщение стадии DINO: сбои по файлам и фото без превью."""

    parts = []
    if prefix:
        parts.append(prefix)
    if failed:
        parts.append(f"не удалось распознать файлов: {failed}")
    if skipped:
        parts.append(f"без превью (в DINO не ставим): {skipped}")

    return "; ".join(parts) or None


def _photos_without_qwen(cutoff: str | None) -> list[str]:
    clause, params = _cutoff_clause(cutoff)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id
                FROM public.photos AS p
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.photo_qwen AS q
                    WHERE q.photo_id = p.photo_id
                )
                """ + clause + " ORDER BY p.photo_id",
                params,
            )
            return [row[0] for row in cur.fetchall()]


def _qwen_count(cutoff: str | None, status: str) -> int:
    clause, params = _cutoff_clause(cutoff)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM public.photos AS p
                JOIN public.photo_qwen AS q ON q.photo_id = p.photo_id
                WHERE q.status = %s
                """ + clause,
                [status, *params],
            )
            return int(cur.fetchone()[0])
