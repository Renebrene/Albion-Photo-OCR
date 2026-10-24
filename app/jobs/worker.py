"""
Deferred job worker.

Run (one pass over the queue):
    python -m app.jobs.worker
Keep polling:
    python -m app.jobs.worker --watch

Heavy work (DINO inference, HYBRID) happens ONLY here, never inside the web
API request handlers. Jobs are claimed atomically from public.job_queue.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import time

from app.core.errors import redact_absolute_paths
from app.jobs import automation
from app.jobs import database as jobs

# A paused job keeps the worker busy, so the wait is bounded: if nobody resumes
# it in time the job fails instead of blocking the whole queue forever.
PAUSE_MAX_SECONDS = float(os.getenv("SCENE_PAUSE_MAX_SECONDS", "300"))

# Progress/control round trips to the database are throttled.
CONTROL_INTERVAL = 1.0


class JobCancelled(RuntimeError):
    """The job was cancelled while it ran; the result must be dropped."""


class JobPausedTooLong(RuntimeError):
    """Nobody resumed a paused job within PAUSE_MAX_SECONDS."""


def job_control(job_id: int):
    """
    Build the progress callback for one job.

    It writes {done, total, stage, percent} to the job row (at most once per
    second) and checks the row's status: CANCELLED stops the build at once,
    PAUSED waits for a resume (bounded by PAUSE_MAX_SECONDS).
    """

    state = {"last": 0.0}

    def callback(done: int, total: int, stage: str) -> None:
        now = time.monotonic()

        if now - state["last"] < CONTROL_INTERVAL and done < total:
            return

        state["last"] = now

        percent = round(done / total * 100, 1) if total else 0.0

        jobs.set_progress(
            job_id,
            {
                "done": done,
                "total": total,
                "stage": stage,
                "percent": percent,
            },
        )

        status = jobs.job_status(job_id)

        if status == "CANCELLED":
            raise JobCancelled("задание отменено")

        if status == "PAUSED":
            waited = 0.0
            print(f"[worker] job {job_id} paused", flush=True)

            while waited < PAUSE_MAX_SECONDS:
                time.sleep(2.0)
                waited += 2.0

                status = jobs.job_status(job_id)

                if status == "CANCELLED":
                    raise JobCancelled("задание отменено во время паузы")

                if status == "RUNNING":
                    print(f"[worker] job {job_id} resumed", flush=True)
                    break
            else:
                raise JobPausedTooLong(
                    f"пауза длилась больше {PAUSE_MAX_SECONDS:.0f} с"
                )

    return callback


def _maybe_enqueue_refine() -> None:
    """
    Поставить «Уточнение» после последнего задания QWEN.

    Этап выключен по умолчанию; ошибка постановки не должна ломать QWEN —
    описание уже сохранено, а этап можно запустить и на следующем прогоне.
    Без QWEN (выключен в прогоне и ни одного описания в базе) этап не
    ставится вовсе: сравнивать нечего.
    """

    try:
        from app.jobs import database as jobs_db
        from app.refine import config as refine_config

        if not refine_config.enabled() or not refine_config.available():
            return

        if jobs_db.active_count("QWEN_PHOTO"):
            return

        jobs_db.enqueue_refine()
    except Exception:  # noqa: BLE001 - фоновая работа, не повод падать
        pass


def _execute(job: dict) -> dict:
    job_type = job["job_type"]
    payload = job["payload"] or {}

    if job_type == "DINO_BATCH":
        from app.dino.runner import run_batch

        batch_id = int(payload["batch_id"])
        final = run_batch(
            batch_id,
            control=job_control(int(job["id"])),
            recover_running=int(job.get("attempts") or 1) > 1,
        )

        followup_errors = []

        # «Виртуальная сортировка» — один запуск DINO + HYBRID. HYBRID is
        # atomically enqueued with its domain row and linked to shared history.
        if payload.get("auto_hybrid") and final.status == "DONE":
            from app.hybrid import database as hybrid_db
            from app.runs import history

            run_history_id = payload.get("run_history_id")

            try:
                hybrid, hybrid_job_id, _new_history_id = hybrid_db.create_and_enqueue_run(
                    batch_id,
                    run_history_id=run_history_id,
                )
                if hybrid_job_id is None and hybrid.total_count:
                    raise RuntimeError(
                        f"HYBRID run {hybrid.hybrid_run_id} has no queue job"
                    )
            except Exception as exc:
                if run_history_id is not None:
                    try:
                        history.set_sort_stage(
                            int(run_history_id),
                            "HYBRID",
                            status="FAILED",
                            total=final.completed_count,
                            failed=final.completed_count,
                            required=True,
                        )
                    except Exception:
                        pass
                followup_errors.append({
                    "error": f"HYBRID enqueue failed: {type(exc).__name__}"
                })

        result = {
            "batch_id": final.batch_id,
            "status": final.status,
            "total_count": final.total_count,
            "done_count": final.completed_count,
            "failed_count": final.failed_count,
        }
        if followup_errors:
            result["errors"] = followup_errors
        return result

    if job_type == "HYBRID_RUN":
        from app.hybrid.database import get_run
        from app.hybrid.runner import run as hybrid_run

        hybrid_run_id = int(payload["hybrid_run_id"])
        hybrid_run(hybrid_run_id)
        final = get_run(hybrid_run_id)
        return {
            "hybrid_run_id": final.hybrid_run_id,
            "status": final.status,
            "done_count": final.completed_count,
            "failed_count": final.failed_count,
        }

    if job_type == "QWEN_PHOTO":
        from app.qwen.processor import run_photo

        # Разовая пересборка из карточки фото может попросить конкретного
        # провайдера/модель; обычные задания идут на текущих настройках.
        result = run_photo(
            str(payload["photo_id"]),
            provider=payload.get("provider"),
            model=payload.get("model"),
        )

        # «Уточнение» идёт только после того, как QWEN закончил целиком:
        # иначе сравнивать нечего. Ставится здесь, после каждого описания —
        # когда очередь QWEN опустеет, задание появится одно.
        _maybe_enqueue_refine()

        return result

    if job_type == "REFINE":
        from app.refine.runner import run_refine

        return run_refine(limit=int(payload.get("limit") or 5000))

    if job_type == "NL_SEARCH":
        from app.api.nl_search import run as nl_run

        return nl_run(str(payload["query"]))

    if job_type == "INGEST_DIR":
        from app.ingest.runner import ingest_directory

        control = job_control(int(job["id"]))

        return ingest_directory(
            str(payload["directory"]),
            only_files=payload.get("only_files"),
            date_from=payload.get("date_from"),
            date_to=payload.get("date_to"),
            date_mode=payload.get("date_mode") or "upload",
            progress=lambda done, total: control(done, total, "ingest"),
        )

    if job_type == "PHOTO_PREVIEW":
        from app.preview.queue import run_photo_preview

        return run_photo_preview(str(payload["photo_id"]))

    if job_type == "BILLBOARD_DETECT":
        from app.billboard.pipeline import run_detect

        return run_detect(str(payload["photo_id"]))

    if job_type == "FINGERPRINT_BUILD":
        from app.pipeline.build import build_fingerprint

        return build_fingerprint(
            str(payload["fingerprint_id"]),
            str(payload["folder"]),
            max_photos=payload.get("max_photos"),
            replace=bool(payload.get("replace", True)),
            recalculate=bool(payload.get("recalculate")),
            batch_id=payload.get("batch_id"),
            job_id=int(job["id"]),
            progress=job_control(int(job["id"])),
        )

    if job_type == "MEDIA_SEARCH":
        from app.api.media_search import delete_query
        from app.api.media_search import run as media_run
        from app.api.media_search import search as media_search

        # Ручной режим, второй шаг: поиск по уже собранным/поправленным
        # фильтрам (файла нет, QWEN не вызывается).
        if payload.get("filters") is not None:
            filters = payload["filters"]
            found = media_search(filters)
            return {"kind": "query", "mode": "query", "filters": filters, **found}

        path = str(payload["path"])

        try:
            # A video query is described frame by frame; the callback carries
            # the frame counter into the job's progress and notices a cancel.
            return media_run(
                path,
                kind=payload.get("kind"),
                progress=job_control(int(job["id"])),
                mode=payload.get("mode", "auto"),
                frame_seconds=payload.get("frame_seconds"),
            )
        finally:
            # The uploaded query file is transient by design: it exists only
            # for the duration of the job (frames of a video go with it).
            delete_query(path)

    if job_type == "MEDIA_EXPORT":
        from app.cloud.export import run_export

        return run_export(int(payload["link_id"]))

    if job_type == "VIDEO_STORYBOARD":
        from app.video.transcode import generate_storyboard

        return generate_storyboard(
            video_id=str(payload["video_id"]),
            source_sha256=str(payload["source_sha256"]),
            progress=job_control(int(job["id"])),
        )

    if job_type == "VIDEO_TRIM":
        from app.api import video_repository
        from app.video.transcode import VideoTranscodeCancelled, run_trim

        derivative_id = int(payload["derivative_id"])
        try:
            result = run_trim(
                video_id=str(payload["video_id"]),
                derivative_id=derivative_id,
                source_sha256=str(payload["source_sha256"]),
                start_seconds=float(payload["start_seconds"]),
                end_seconds=float(payload["end_seconds"]),
                job_id=int(job["id"]),
                progress=job_control(int(job["id"])),
            )
            asset_id = video_repository.register_completed_derivative(derivative_id)
            if asset_id:
                from app.api.config import VIDEO_PREVIEW_ROOT
                from app.preview.video import build_video_poster

                asset = video_repository.registered_asset_source(asset_id)
                try:
                    build_video_poster(asset_id, asset["source_path"], VIDEO_PREVIEW_ROOT, duration_seconds=asset["duration_seconds"])
                except Exception as exc:  # poster is non-critical after validated asset registration
                    print(f"[video-worker] poster generation failed for {asset_id}: {exc.__class__.__name__}", flush=True)
            return {**result, "asset_video_id": asset_id}
        except VideoTranscodeCancelled as exc:
            video_repository.update_derivative(
                derivative_id, status="CANCELLED", job_id=int(job["id"]), error_message=str(exc)
            )
            raise JobCancelled(str(exc)) from exc
        except JobCancelled:
            video_repository.update_derivative(
                derivative_id, status="CANCELLED", job_id=int(job["id"]), error_message="задание отменено"
            )
            raise
        except Exception as exc:
            video_repository.update_derivative(
                derivative_id, status="FAILED", job_id=int(job["id"]),
                error_message=redact_absolute_paths(str(exc)),
            )
            raise

    if job_type == "VIDEO_TRANSCODE":
        from app.api import video_repository
        from app.video.transcode import VideoTranscodeCancelled, run_transcode

        derivative_id = int(payload["derivative_id"])
        try:
            result = run_transcode(
                video_id=str(payload["video_id"]),
                derivative_id=derivative_id,
                profile=str(payload["profile"]),
                source_sha256=str(payload["source_sha256"]),
                job_id=int(job["id"]),
                progress=job_control(int(job["id"])),
            )
            asset_id = video_repository.register_completed_derivative(derivative_id)
            if asset_id:
                from app.api.config import VIDEO_PREVIEW_ROOT
                from app.preview.video import build_video_poster

                asset = video_repository.registered_asset_source(asset_id)
                try:
                    build_video_poster(asset_id, asset["source_path"], VIDEO_PREVIEW_ROOT, duration_seconds=asset["duration_seconds"])
                except Exception as exc:  # poster is non-critical after validated asset registration
                    print(f"[video-worker] poster generation failed for {asset_id}: {exc.__class__.__name__}", flush=True)
            return {**result, "asset_video_id": asset_id}
        except VideoTranscodeCancelled as exc:
            video_repository.update_derivative(
                derivative_id, status="CANCELLED", job_id=int(job["id"]),
                error_message=str(exc),
            )
            raise JobCancelled(str(exc)) from exc
        except JobCancelled:
            video_repository.update_derivative(
                derivative_id, status="CANCELLED", job_id=int(job["id"]),
                error_message="задание отменено",
            )
            raise
        except Exception as exc:
            video_repository.update_derivative(
                derivative_id, status="FAILED", job_id=int(job["id"]),
                error_message=redact_absolute_paths(str(exc)),
            )
            raise

    raise ValueError(f"Unsupported job type: {job_type}")


# Jobs that may load the local QWEN model; used to decide idle unload.
_MODEL_JOB_TYPES = {"QWEN_PHOTO", "NL_SEARCH", "MEDIA_SEARCH"}


def _unload_on_idle() -> bool:
    """Unload the local model after the queue drains (if configured)."""

    try:
        from app.qwen import processor as qwen

        if not qwen.resolve_settings()["unload_on_idle"]:
            return False

        return qwen.unload_model()
    except Exception as exc:  # noqa: BLE001 - never break the loop
        print(f"[worker] idle unload failed: {exc}", flush=True)
        return False


def run_once(
    types: list[str] | None = None,
    *,
    exclude_types: list[str] | None = None,
) -> str | None:
    """
    Claim and execute one job.

    `types` limits which job types this worker takes (see claim_next). Returns
    the executed job_type, or None when nothing was claimed (so a
    `while run_once():` loop still works and callers can inspect the type).
    """

    job = jobs.claim_next(types, exclude_types=exclude_types)

    if job is None:
        return None

    print(
        f"[worker] job {job['id']} {job['job_type']} "
        f"payload={job['payload']}",
        flush=True,
    )

    run_history_id = (job.get("payload") or {}).get("run_history_id")

    if run_history_id is not None:
        try:
            from app.runs import history

            history.record_job_start(int(run_history_id), int(job["id"]))
        except Exception as exc:  # noqa: BLE001 - history must not break the job
            print(f"[worker] could not mark run history started: {type(exc).__name__}", flush=True)

    try:
        result = _execute(job)
    except JobCancelled as exc:
        # The row is already CANCELLED; the result is dropped, nothing to report.
        print(f"[worker] job {job['id']} cancelled: {exc}", flush=True)
        _record_history_result(run_history_id, job, "CANCELLED", error=str(exc))
        return str(job["job_type"])
    except Exception as exc:  # noqa: BLE001 - reported to the queue
        # A job cancelled while it ran keeps its CANCELLED status: the failure
        # is not published (mark_failed refuses to touch a non-RUNNING row).
        safe_error = redact_absolute_paths(repr(exc))
        try:
            jobs.mark_failed(job["id"], safe_error)
        except ValueError:
            print(
                f"[worker] job {job['id']} was cancelled; error not recorded",
                flush=True,
            )
            _record_history_result(run_history_id, job, "CANCELLED", error=safe_error)
            return str(job["job_type"])

        print(f"[worker] job {job['id']} FAILED: {exc}", flush=True)
        _record_history_result(run_history_id, job, "FAILED", error=safe_error)
        return str(job["job_type"])

    try:
        jobs.mark_done(job["id"], result)
    except ValueError:
        # Cancelled mid-run: the result is discarded, the status stays CANCELLED.
        print(
            f"[worker] job {job['id']} was cancelled; result discarded",
            flush=True,
        )
        _record_history_result(run_history_id, job, "CANCELLED")
        return str(job["job_type"])

    _record_history_result(run_history_id, job, "DONE", result=result)
    print(f"[worker] job {job['id']} DONE {result}", flush=True)
    return str(job["job_type"])


def _record_history_result(run_history_id, job, status, *, result=None, error=None):
    if run_history_id is None:
        return
    try:
        from app.runs import history

        history.record_job_result(
            int(run_history_id),
            job_type=str(job["job_type"]),
            job_id=int(job["id"]),
            status=status,
            result=result,
            error=error,
        )
    except Exception as exc:  # noqa: BLE001 - history must never break queue work
        print(f"[worker] could not update run history: {type(exc).__name__}", flush=True)


def _builder_worker(
    types: list[str],
    interval: float,
    threads: int,
    parallel: int,
    label: str,
    exclude_types: list[str] | None = None,
) -> None:
    """One worker process in --parallel mode: claims its own jobs."""

    os.environ.setdefault("OMP_NUM_THREADS", str(threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(threads))
    # The builder sizes its descriptor thread pool from this: N builders must
    # not each claim half the cores (see default_descriptor_workers).
    os.environ["SCENE_BUILD_PARALLEL"] = str(parallel)

    try:
        import torch

        torch.set_num_threads(threads)
    except Exception:  # noqa: BLE001 - reported by the job itself
        pass

    print(f"[worker {label}] watching {types}", flush=True)

    while True:
        job_type = run_once(types, exclude_types=exclude_types)

        if job_type is None:
            time.sleep(interval)


def _video_worker(
    types: list[str],
    interval: float,
    threads: int,
    label: str,
    exclude_types: list[str] | None = None,
) -> None:
    """Video transcodes use their own CPU budget and never import torch."""

    os.environ["SCENE_VIDEO_TRANSCODE_THREADS"] = str(threads)
    os.environ.setdefault("OMP_NUM_THREADS", str(threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(threads))
    print(f"[video-worker {label}] watching {types}; ffmpeg threads={threads}", flush=True)
    while True:
        job_type = run_once(types, exclude_types=exclude_types)
        if job_type is None:
            time.sleep(interval)


def _preview_worker(
    types: list[str],
    interval: float,
    label: str,
    exclude_types: list[str] | None = None,
) -> None:
    """One PHOTO_PREVIEW worker in --parallel mode; no torch/model imports."""

    print(f"[preview-worker {label}] watching {types}", flush=True)

    while True:
        job_type = run_once(types, exclude_types=exclude_types)

        if job_type is None:
            time.sleep(interval)


def _requeue_stale_jobs(minutes: int, *, video_only: bool, preview_only: bool = False) -> dict:
    if preview_only:
        return {"jobs": jobs.requeue_stale(older_than_minutes=minutes, types=["PHOTO_PREVIEW"])}
    if video_only:
        from app.ingest.database import get_connection

        result = {"jobs": jobs.requeue_stale(
            older_than_minutes=minutes,
            types=["VIDEO_TRANSCODE", "VIDEO_TRIM", "VIDEO_STORYBOARD"],
        )}
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE public.video_derivatives AS d
                       SET status='PENDING', started_at=NULL, finished_at=NULL,
                           error_message='requeued (stale RUNNING)'
                       FROM public.job_queue AS j
                       WHERE d.job_id=j.id AND j.job_type IN ('VIDEO_TRANSCODE','VIDEO_TRIM')
                         AND j.status='PENDING' AND d.status='RUNNING'"""
                )
        return result

    result = {"jobs": jobs.requeue_stale(older_than_minutes=minutes)}
    from app.dino import database as dino_db
    from app.hybrid import database as hybrid_db

    result["dino_runs"] = dino_db.requeue_stale_runs(older_than_minutes=minutes)
    result["hybrid_runs"] = hybrid_db.requeue_stale_runs(older_than_minutes=minutes)
    return result


def _pipeline_loop(interval: float) -> None:
    """
    Dedicated supervisor loop: advance the active pipeline run, claim nothing.

    Runs in scene-pipeline-worker.service so a long-running INGEST -> QWEN run
    never occupies the shared job worker. The supervisor only enqueues/observes
    the existing job types; the actual work stays in the normal workers.
    """

    from app.supervisor import runs as pipeline_runs

    print(
        "[pipeline-worker] supervisor loop started "
        f"(interval={interval}s; INGEST -> PREVIEW -> DINO -> HYBRID -> QWEN)",
        flush=True,
    )

    while True:
        try:
            result = pipeline_runs.tick()
            if result.get("outcome") not in (None, "WAIT"):
                print(f"[pipeline-worker] {result}", flush=True)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            print(f"[pipeline-worker] tick failed: {exc}", flush=True)

        time.sleep(interval)


def resolve_parallel(
    requested: int,
    *,
    preview_only: bool,
    cpu_count: int | None = None,
) -> int:
    """
    Number of parallel worker processes.

    `--parallel 0` means "half of the logical cores" for the preview worker:
    WebP encoding is CPU-bound, and half leaves room for the API and DINO.
    Other worker types keep the old meaning (0 -> 1), except video, which has
    its own encoder-based choice.
    """

    if preview_only and int(requested) == 0:
        return max(1, (cpu_count or os.cpu_count() or 1) // 2)

    return max(1, int(requested))


def main() -> None:
    parser = argparse.ArgumentParser(description="PhotoBAse job worker")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep polling instead of processing the queue once.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Polling interval in seconds (with --watch).",
    )
    parser.add_argument(
        "--requeue-stale",
        type=int,
        default=None,
        metavar="MINUTES",
        help=(
            "Before starting, return RUNNING jobs older than MINUTES "
            "to PENDING (recovery after a crashed worker)."
        ),
    )
    parser.add_argument(
        "--automation",
        action="store_true",
        help=(
            "Also run the scheduler loop (see automation_settings). "
            "Off by default; implies --watch."
        ),
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help=(
            "Run only the resumable pipeline supervisor loop (INGEST -> PREVIEW "
            "-> DINO -> HYBRID -> QWEN): advance active runs, never claim jobs. "
            "Use it for the dedicated scene-pipeline-worker."
        ),
    )
    parser.add_argument(
        "--only",
        default=None,
        metavar="TYPES",
        help=(
            "Only claim these job types (comma separated), e.g. "
            "FINGERPRINT_BUILD - this is how a dedicated builder worker is run."
        ),
    )
    parser.add_argument(
        "--exclude",
        default=None,
        metavar="TYPES",
        help="Never claim these job types (comma separated).",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help=(
            "Run N workers in this process, each claiming its own job. "
            "For --only VIDEO_TRANSCODE, 0 auto-selects one verified NVENC worker "
            "or half the logical CPU cores for CPU encoding."
        ),
    )
    args = parser.parse_args()

    if args.automation:
        args.watch = True

    if args.pipeline:
        _pipeline_loop(args.interval)
        return

    types = (
        [item.strip() for item in args.only.split(",") if item.strip()]
        if args.only
        else None
    )
    excluded_types = (
        [item.strip() for item in args.exclude.split(",") if item.strip()]
        if args.exclude
        else None
    )
    if types is None:
        excluded_types = sorted(set(excluded_types or []) | {
            "PHOTO_PREVIEW", "VIDEO_TRANSCODE", "VIDEO_TRIM", "VIDEO_STORYBOARD",
        })

    video_only = bool(types) and all(item in {"VIDEO_TRANSCODE", "VIDEO_TRIM", "VIDEO_STORYBOARD"} for item in types)
    preview_only = types == ["PHOTO_PREVIEW"]
    if video_only:
        from app.video.transcode import choose_worker_mode

        encoder, automatic_parallel = choose_worker_mode()
        os.environ["SCENE_VIDEO_ENCODER_RESOLVED"] = encoder
        requested_parallel = args.parallel
        parallel = automatic_parallel if requested_parallel == 0 else max(1, requested_parallel)
        if encoder == "h264_nvenc":
            parallel = min(parallel, 2)
    else:
        parallel = resolve_parallel(
            args.parallel,
            preview_only=preview_only,
        )

    video_threads = max(1, (os.cpu_count() or 1) // parallel)
    if video_only:
        os.environ["SCENE_VIDEO_TRANSCODE_THREADS"] = str(video_threads)

    if preview_only and args.watch and args.requeue_stale is not None:
        _requeue_stale_jobs(args.requeue_stale, video_only=False, preview_only=True)

    if preview_only and args.watch and parallel == 1:
        print(f"[preview-worker] watching {types} (single process)", flush=True)
        while True:
            job_type = run_once(types, exclude_types=excluded_types)
            if job_type is None:
                time.sleep(args.interval)
        return

    if video_only and args.watch and args.requeue_stale is not None:
        _requeue_stale_jobs(args.requeue_stale, video_only=True)

    if video_only and args.watch and parallel == 1:
        _video_worker(
            types,
            args.interval,
            video_threads,
            "1/1",
            excluded_types,
        )
        return

    if parallel > 1 and args.watch and types:
        threads = max(1, (os.cpu_count() or 1) // parallel)
        if preview_only:
            print(
                f"[worker] {parallel} preview processes, types={types}",
                flush=True,
            )
            target = _preview_worker
            process_args = [
                (types, args.interval, f"{index + 1}/{parallel}", excluded_types)
                for index in range(parallel)
            ]
        elif video_only:
            print(
                f"[worker] {parallel} video transcode workers, encoder={os.environ['SCENE_VIDEO_ENCODER_RESOLVED']}, "
                f"{threads} CPU threads per worker",
                flush=True,
            )
            target = _video_worker
            process_args = [
                (types, args.interval, threads, f"{index + 1}/{parallel}")
                for index in range(parallel)
            ]
        else:
            print(
                f"[worker] {parallel} builder processes, types={types}, "
                f"{threads} torch threads each",
                flush=True,
            )
            target = _builder_worker
            process_args = [
                (types, args.interval, threads, parallel, f"{index + 1}/{parallel}", excluded_types)
                for index in range(parallel)
            ]

        context = mp.get_context("spawn")
        processes = [
            context.Process(target=target, args=process_args[index])
            for index in range(parallel)
        ]

        for process in processes:
            process.start()

        for process in processes:
            process.join()

        failed = [process.exitcode for process in processes if process.exitcode]

        if failed:
            raise SystemExit(f"builder(s) failed with exit codes: {failed}")

        return

    if args.requeue_stale is not None:
        recovered = _requeue_stale_jobs(
            args.requeue_stale,
            video_only=video_only,
            preview_only=preview_only,
        )
        if video_only or preview_only:
            print(f"[worker] requeued stale jobs={recovered['jobs']}", flush=True)
        else:
            print(
                "[worker] requeued stale: "
                f"jobs={recovered['jobs']} dino_runs={recovered['dino_runs']} "
                f"hybrid_runs={recovered['hybrid_runs']}",
                flush=True,
            )

    if not args.watch:
        processed = 0
        model_used = False

        while True:
            job_type = run_once(types, exclude_types=excluded_types)

            if job_type is None:
                break

            processed += 1
            model_used = model_used or job_type in _MODEL_JOB_TYPES

        if model_used and _unload_on_idle():
            print("[worker] QWEN model unloaded (queue drained)", flush=True)

        print(f"[worker] processed {processed} job(s)", flush=True)
        return

    print("[worker] watching for jobs (Ctrl+C to stop)", flush=True)
    model_used = False

    while True:
        if args.automation:
            try:
                summary = automation.run_tick()
                if summary.get("dino_batch_id") or summary.get("qwen_jobs"):
                    print(f"[worker] automation enqueued {summary}", flush=True)
            except Exception as exc:  # noqa: BLE001 - keep the loop alive
                print(f"[worker] automation tick failed: {exc}", flush=True)

        job_type = run_once(types, exclude_types=excluded_types)

        if job_type is None:
            # Queue is empty: free the local model if it was used.
            if model_used:
                model_used = False
                if _unload_on_idle():
                    print("[worker] QWEN model unloaded (idle)", flush=True)

            time.sleep(args.interval)
        elif job_type in _MODEL_JOB_TYPES:
            model_used = True


if __name__ == "__main__":
    main()
