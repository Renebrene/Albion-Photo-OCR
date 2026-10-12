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

    raise ValueError(f"Unsupported job type: {job_type}")


def run_once() -> bool:
    """Claim and execute one job. Returns False when the queue is empty."""

    job = jobs.claim_next()

    if job is None:
        return False

    print(
        f"[worker] job {job['id']} {job['job_type']} "
        f"payload={job['payload']}",
        flush=True,
    )

    try:
        result = _execute(job)
    except Exception as exc:  # noqa: BLE001 - reported to the queue
        jobs.mark_failed(job["id"], repr(exc))
        print(f"[worker] job {job['id']} FAILED: {exc}", flush=True)
        return True

    jobs.mark_done(job["id"], result)
    print(f"[worker] job {job['id']} DONE {result}", flush=True)
    return True


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
        requeued = jobs.requeue_stale(older_than_minutes=args.requeue_stale)
        print(f"[worker] requeued stale jobs: {requeued}", flush=True)

    if not args.watch:
        processed = 0
        while run_once():
            processed += 1
        print(f"[worker] processed {processed} job(s)", flush=True)
        return

    print("[worker] watching for jobs (Ctrl+C to stop)", flush=True)
    while True:
        if args.automation:
            try:
                summary = automation.run_tick()
                if summary.get("dino_batch_id") or summary.get("qwen_jobs"):
                    print(f"[worker] automation enqueued {summary}", flush=True)
            except Exception as exc:  # noqa: BLE001 - keep the loop alive
                print(f"[worker] automation tick failed: {exc}", flush=True)

        if not run_once():
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
