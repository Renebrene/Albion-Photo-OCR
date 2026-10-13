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
import time

from app.core.errors import redact_absolute_paths
from app.jobs import automation
from app.jobs import database as jobs


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

    if job_type == "MEDIA_SEARCH":
        from app.api.media_search import delete_query
        from app.api.media_search import run as media_run

        path = str(payload["path"])

        try:
            return media_run(path)
        finally:
            # The uploaded query image is transient by design: it exists only
            # for the duration of the job.
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


def run_once() -> str | None:
    """
    Claim and execute one job.

    Returns the executed job_type, or None when the queue is empty (so a
    `while run_once():` loop still works and callers can inspect the type).
    """

    job = jobs.claim_next()

    if job is None:
        return None

    print(
        f"[worker] job {job['id']} {job['job_type']} "
        f"payload={job['payload']}",
        flush=True,
    )

    try:
        result = _execute(job)
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
    args = parser.parse_args()

    if args.automation:
        args.watch = True

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
            job_type = run_once()

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

        job_type = run_once()

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
