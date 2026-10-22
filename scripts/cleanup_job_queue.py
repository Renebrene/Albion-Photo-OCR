"""Retention cleanup for public.job_queue.

Algorithm
---------
1. Active rows (PENDING/RUNNING/PAUSED) are never touched.
2. DONE/CANCELLED rows older than ``--done-days`` (default 14) are eligible.
3. FAILED rows older than ``--failed-days`` (default 30) are eligible; failures
   are kept longer because they are useful for diagnostics.
4. Eligible rows are copied to ``public.job_queue_archive`` in small batches and
   deleted from ``job_queue`` in the same transaction. `run_history` and
   `run_history_jobs` are not modified: the user-visible history survives.
5. The archive itself is pruned after ``--archive-days`` (default 365).
6. `VACUUM (ANALYZE) job_queue` runs after a non-dry cleanup (unless disabled).

Safety
------
* ``--dry-run`` only counts and never writes.
* ``--max-delete`` (default 200000) is a hard cap for one run.
* Batches use ``FOR UPDATE SKIP LOCKED`` and commit one by one, so the cleanup
  does not hold a long transaction or block workers.

Examples
--------
    .venv/bin/python scripts/cleanup_job_queue.py --dry-run
    .venv/bin/python scripts/cleanup_job_queue.py --done-days 14 --failed-days 30
    .venv/bin/python scripts/cleanup_job_queue.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.ingest.database import get_connection  # noqa: E402

ACTIVE = ("PENDING", "RUNNING", "PAUSED")
FINISHED = ("DONE", "FAILED", "CANCELLED")

DEFAULT_DONE_DAYS = int(os.getenv("SCENE_JOB_RETENTION_DAYS", "14"))
DEFAULT_FAILED_DAYS = int(os.getenv("SCENE_JOB_FAILED_RETENTION_DAYS", "30"))
DEFAULT_ARCHIVE_DAYS = int(os.getenv("SCENE_JOB_ARCHIVE_DAYS", "365"))
DEFAULT_BATCH = 5000
DEFAULT_MAX_DELETE = 200_000


def _eligibility(
    done_days: int,
    failed_days: int,
    types: list[str] | None,
) -> tuple[str, list[object]]:
    sql = """
        WHERE j.status IN ('DONE', 'FAILED', 'CANCELLED')
          AND (
                (j.status IN ('DONE', 'CANCELLED')
                 AND COALESCE(j.finished_at, j.created_at)
                     < CURRENT_TIMESTAMP - (%s || ' days')::interval)
             OR (j.status = 'FAILED'
                 AND COALESCE(j.finished_at, j.created_at)
                     < CURRENT_TIMESTAMP - (%s || ' days')::interval)
          )
    """
    params: list[object] = [int(done_days), int(failed_days)]

    if types:
        sql += " AND j.job_type = ANY(%s)"
        params.append(list(types))

    return sql, params


def _count_eligible(
    cur,
    done_days: int,
    failed_days: int,
    types: list[str] | None,
) -> dict:
    where, params = _eligibility(done_days, failed_days, types)
    cur.execute(
        "SELECT j.status, count(*), "
        "       COALESCE(sum(pg_column_size(j)), 0)::bigint "
        "FROM public.job_queue AS j "
        + where
        + " GROUP BY j.status ORDER BY j.status",
        params,
    )
    return {
        status: {"rows": int(rows), "bytes": int(size)}
        for status, rows, size in cur.fetchall()
    }


def _delete_batch(
    cur,
    *,
    done_days: int,
    failed_days: int,
    types: list[str] | None,
    limit: int,
    archive: bool,
) -> int:
    where, params = _eligibility(done_days, failed_days, types)
    params.append(int(limit))

    if archive:
        cur.execute(
            """
            WITH victims AS (
                SELECT j.id
                FROM public.job_queue AS j
                """
            + where
            + """
                ORDER BY j.id
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            ),
            archived AS (
                INSERT INTO public.job_queue_archive (
                    id, job_type, status, attempts, payload_photo_id,
                    error_message, created_at, started_at, finished_at
                )
                SELECT j.id, j.job_type, j.status, j.attempts,
                       NULLIF(j.payload ->> 'photo_id', ''),
                       LEFT(j.error_message, 2000),
                       j.created_at, j.started_at, j.finished_at
                FROM public.job_queue AS j
                JOIN victims AS v ON v.id = j.id
                ON CONFLICT (id) DO NOTHING
                RETURNING id
            )
            DELETE FROM public.job_queue AS j
            USING victims AS v
            WHERE j.id = v.id
            RETURNING j.id
            """,
            params,
        )
    else:
        cur.execute(
            """
            WITH victims AS (
                SELECT j.id
                FROM public.job_queue AS j
                """
            + where
            + """
                ORDER BY j.id
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            DELETE FROM public.job_queue AS j
            USING victims AS v
            WHERE j.id = v.id
            RETURNING j.id
            """,
            params,
        )

    return len(cur.fetchall())


def _archive_available(cur) -> bool:
    cur.execute("SELECT to_regclass('public.job_queue_archive')")
    return cur.fetchone()[0] is not None


def _prune_archive(cur, days: int) -> int:
    if days <= 0:
        return 0
    cur.execute(
        "DELETE FROM public.job_queue_archive "
        "WHERE archived_at < CURRENT_TIMESTAMP - (%s || ' days')::interval",
        (int(days),),
    )
    return cur.rowcount


def _vacuum_job_queue() -> None:
    with get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("VACUUM (ANALYZE) public.job_queue")


def _positive(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--done-days", type=_positive, default=DEFAULT_DONE_DAYS)
    parser.add_argument(
        "--failed-days", type=_positive, default=DEFAULT_FAILED_DAYS
    )
    parser.add_argument(
        "--archive-days", type=_positive, default=DEFAULT_ARCHIVE_DAYS,
        help="0 keeps the archive forever",
    )
    parser.add_argument("--job-type", action="append", dest="types")
    parser.add_argument("--batch-size", type=_positive, default=DEFAULT_BATCH)
    parser.add_argument(
        "--max-delete", type=_positive, default=DEFAULT_MAX_DELETE,
        help="0 means unlimited",
    )
    parser.add_argument(
        "--no-archive", action="store_true",
        help="delete without writing job_queue_archive (development only)",
    )
    parser.add_argument("--no-vacuum", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.batch_size == 0:
        print("--batch-size must be > 0", file=sys.stderr)
        return 2
    if args.done_days == 0 and args.failed_days == 0:
        print("both retention periods are 0; refusing to delete everything",
              file=sys.stderr)
        return 2

    started = time.monotonic()
    report: dict = {
        "dry_run": bool(args.dry_run),
        "done_days": args.done_days,
        "failed_days": args.failed_days,
        "archive_days": args.archive_days,
        "job_types": args.types or None,
        "eligible": {},
        "deleted": 0,
        "archive_pruned": 0,
        "vacuum": False,
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            report["eligible"] = _count_eligible(
                cur, args.done_days, args.failed_days, args.types
            )

            if args.dry_run:
                report["duration_sec"] = round(
                    time.monotonic() - started, 3
                )
                _print(report, args.json)
                return 0

            if not args.no_archive and not _archive_available(cur):
                print(
                    "public.job_queue_archive is missing; apply "
                    "schema/044_job_queue_archive.sql or use --no-archive",
                    file=sys.stderr,
                )
                return 2

            remaining = args.max_delete or None
            batches = 0

            while True:
                limit = args.batch_size
                if remaining is not None:
                    limit = min(limit, remaining)
                    if limit <= 0:
                        break

                deleted = _delete_batch(
                    cur,
                    done_days=args.done_days,
                    failed_days=args.failed_days,
                    types=args.types,
                    limit=limit,
                    archive=not args.no_archive,
                )
                conn.commit()

                if not deleted:
                    break

                report["deleted"] += deleted
                batches += 1
                if remaining is not None:
                    remaining -= deleted

            if not args.no_archive:
                report["archive_pruned"] = _prune_archive(
                    cur, args.archive_days
                )
                conn.commit()

    if report["deleted"] and not args.no_vacuum:
        _vacuum_job_queue()
        report["vacuum"] = True

    report["batches"] = batches
    report["duration_sec"] = round(time.monotonic() - started, 3)
    _print(report, args.json)
    return 0


def _print(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return

    eligible = report["eligible"]
    rows = sum(item["rows"] for item in eligible.values())
    size = sum(item["bytes"] for item in eligible.values())
    print(
        f"eligible: {rows} rows / {size} bytes · "
        f"deleted: {report['deleted']} · "
        f"archive pruned: {report['archive_pruned']} · "
        f"vacuum: {report['vacuum']}"
        + (" (dry-run)" if report["dry_run"] else "")
    )
    for status in sorted(eligible):
        item = eligible[status]
        print(f"  {status}: {item['rows']} rows / {item['bytes']} bytes")


if __name__ == "__main__":
    raise SystemExit(main())
