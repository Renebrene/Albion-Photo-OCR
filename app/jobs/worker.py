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


def _execute(job: dict) -> dict:
    job_type = job["job_type"]
    payload = job["payload"] or {}

    if job_type == "DINO_BATCH":
        from app.dino.runner import run_batch

        final = run_batch(int(payload["batch_id"]))
        return {"batch_id": final.batch_id, "status": final.status}

    if job_type == "HYBRID_RUN":
        from app.hybrid.database import get_run
        from app.hybrid.runner import run as hybrid_run

        hybrid_run_id = int(payload["hybrid_run_id"])
        hybrid_run(hybrid_run_id)
        final = get_run(hybrid_run_id)
        return {"hybrid_run_id": final.hybrid_run_id, "status": final.status}

    if job_type == "QWEN_PHOTO":
        from app.qwen.processor import run_photo

        return run_photo(str(payload["photo_id"]))

    if job_type == "NL_SEARCH":
        from app.api.nl_search import run as nl_run

        return nl_run(str(payload["query"]))

    if job_type == "INGEST_DIR":
        from app.ingest.runner import ingest_directory

        return ingest_directory(str(payload["directory"]))

    if job_type == "FINGERPRINT_BUILD":
        from app.pipeline.build import build_fingerprint

        return build_fingerprint(
            str(payload["fingerprint_id"]),
            str(payload["folder"]),
            max_photos=payload.get("max_photos"),
            replace=bool(payload.get("replace", True)),
            progress=job_control(int(job["id"])),
        )

    if job_type == "MEDIA_SEARCH":
        from app.api.media_search import delete_query
        from app.api.media_search import run as media_run

        path = str(payload["path"])

        try:
            # A video query is described frame by frame; the callback carries
            # the frame counter into the job's progress and notices a cancel.
            return media_run(
                path,
                kind=payload.get("kind"),
                progress=job_control(int(job["id"])),
            )
        finally:
            # The uploaded query file is transient by design: it exists only
            # for the duration of the job (frames of a video go with it).
            delete_query(path)

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


def run_once(types: list[str] | None = None) -> str | None:
    """
    Claim and execute one job.

    `types` limits which job types this worker takes (see claim_next). Returns
    the executed job_type, or None when nothing was claimed (so a
    `while run_once():` loop still works and callers can inspect the type).
    """

    job = jobs.claim_next(types)

    if job is None:
        return None

    print(
        f"[worker] job {job['id']} {job['job_type']} "
        f"payload={job['payload']}",
        flush=True,
    )

    try:
        result = _execute(job)
    except JobCancelled as exc:
        # The row is already CANCELLED; the result is dropped, nothing to report.
        print(f"[worker] job {job['id']} cancelled: {exc}", flush=True)
        return str(job["job_type"])
    except Exception as exc:  # noqa: BLE001 - reported to the queue
        # A job cancelled while it ran keeps its CANCELLED status: the failure
        # is not published (mark_failed refuses to touch a non-RUNNING row).
        try:
            # Store the message without absolute server paths.
            jobs.mark_failed(job["id"], redact_absolute_paths(repr(exc)))
        except ValueError:
            print(
                f"[worker] job {job['id']} was cancelled; error not recorded",
                flush=True,
            )

        print(f"[worker] job {job['id']} FAILED: {exc}", flush=True)
        return str(job["job_type"])

    try:
        jobs.mark_done(job["id"], result)
    except ValueError:
        # Cancelled mid-run: the result is discarded, the status stays CANCELLED.
        print(
            f"[worker] job {job['id']} was cancelled; result discarded",
            flush=True,
        )
        return str(job["job_type"])

    print(f"[worker] job {job['id']} DONE {result}", flush=True)
    return str(job["job_type"])


def _builder_worker(
    types: list[str],
    interval: float,
    threads: int,
    parallel: int,
    label: str,
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
        job_type = run_once(types)

        if job_type is None:
            time.sleep(interval)


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
        "--only",
        default=None,
        metavar="TYPES",
        help=(
            "Only claim these job types (comma separated), e.g. "
            "FINGERPRINT_BUILD - this is how a dedicated builder worker is run."
        ),
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help=(
            "Run N workers in this process, each claiming its own job. Use it "
            "with --only FINGERPRINT_BUILD to build several fingerprints at "
            "once (each gets cores/N torch threads)."
        ),
    )
    args = parser.parse_args()

    if args.automation:
        args.watch = True

    types = (
        [item.strip() for item in args.only.split(",") if item.strip()]
        if args.only
        else None
    )

    parallel = max(1, args.parallel)

    if parallel > 1 and args.watch and types:
        threads = max(1, (os.cpu_count() or 1) // parallel)

        print(
            f"[worker] {parallel} builder processes, types={types}, "
            f"{threads} torch threads each",
            flush=True,
        )

        context = mp.get_context("spawn")
        processes = [
            context.Process(
                target=_builder_worker,
                args=(
                    types,
                    args.interval,
                    threads,
                    parallel,
                    f"{index + 1}/{parallel}",
                ),
            )
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
        from app.dino import database as dino_db
        from app.hybrid import database as hybrid_db

        minutes = args.requeue_stale
        requeued = jobs.requeue_stale(older_than_minutes=minutes)
        dino_runs = dino_db.requeue_stale_runs(older_than_minutes=minutes)
        hybrid_runs = hybrid_db.requeue_stale_runs(older_than_minutes=minutes)

        print(
            "[worker] requeued stale: "
            f"jobs={requeued} dino_runs={dino_runs} hybrid_runs={hybrid_runs}",
            flush=True,
        )

    if not args.watch:
        processed = 0
        model_used = False

        while True:
            job_type = run_once(types)

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

        job_type = run_once(types)

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
