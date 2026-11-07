#!/usr/bin/env python3
"""Reset only recognition/queue state before a full DINO/HYBRID re-run.

Preserved deliberately:
    photos, photo_previews, photo_qwen, photo_qwen_history, photo_regions,
    fingerprints, address_directory, users, settings.

Removed:
    dino_candidates, dino_runs, dino_batches, hybrid_results, hybrid_runs,
    job_queue, job_queue_archive, pipeline_runs, run_history,
    photo_address_overrides.

    .venv/bin/python scripts/reset_recognition_for_reingest.py --dry-run
    .venv/bin/python scripts/reset_recognition_for_reingest.py --apply --confirm RESET
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402

TRUNCATE_TABLES = (
    "dino_candidates",
    "dino_runs",
    "dino_batches",
    "hybrid_results",
    "hybrid_runs",
    "job_queue_archive",
    "pipeline_run_stages",
    "pipeline_runs",
    "run_history_jobs",
    "run_history",
    "photo_address_overrides",
)
# job_queue is referenced by video_derivatives(job_id) ON DELETE SET NULL, so
# TRUNCATE is not allowed; DELETE preserves that one unrelated video row.
DELETE_TABLES = ("job_queue",)
TABLES = TRUNCATE_TABLES + DELETE_TABLES
PRESERVED = (
    "photos",
    "photo_previews",
    "photo_qwen",
    "photo_qwen_history",
    "photo_regions",
    "fingerprints",
    "address_directory",
    "address_fingerprints",
)


def counts() -> dict[str, int]:
    result = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in TABLES + PRESERVED:
                cur.execute(f"SELECT count(*) FROM public.{table}")
                result[table] = int(cur.fetchone()[0])
    return result


def active_jobs() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM public.job_queue "
                "WHERE status IN ('PENDING','RUNNING','PAUSED')"
            )
            return int(cur.fetchone()[0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args(argv)

    if args.apply and args.confirm != "RESET":
        print("refusing; pass --apply --confirm RESET", file=sys.stderr)
        return 2
    if args.apply and args.dry_run:
        print("choose either --dry-run or --apply", file=sys.stderr)
        return 2

    before = counts()
    active = active_jobs()
    report = {
        "dry_run": not args.apply,
        "active_jobs": active,
        "before": before,
        "tables": list(TABLES),
        "preserved": list(PRESERVED),
        "backup": False,
    }

    if not args.apply:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if active:
        print(
            f"refusing: {active} active jobs; stop workers first",
            file=sys.stderr,
        )
        return 2

    if not args.no_backup:
        subprocess.run(
            [sys.executable, "scripts/backup_db.py", "--json"],
            check=True,
        )
        report["backup"] = True

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE "
                + ", ".join(
                    f"public.{table}" for table in TRUNCATE_TABLES
                )
                + " RESTART IDENTITY"
            )
            cur.execute("DELETE FROM public.job_queue")
        conn.commit()

    report["after"] = counts()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
