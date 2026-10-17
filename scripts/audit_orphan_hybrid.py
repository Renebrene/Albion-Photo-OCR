"""Read-only audit of HYBRID runs that have no matching queue job.

Usage:
    .venv/bin/python scripts/audit_orphan_hybrid.py
    .venv/bin/python scripts/audit_orphan_hybrid.py --format json

This script issues SELECTs only. It never repairs, deletes, requeues, or
changes the operational database.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime

from app.ingest.database import get_connection

QUERY = """
SELECT
    h.hybrid_run_id,
    h.dino_batch_id,
    h.status AS hybrid_status,
    h.total_count AS hybrid_total,
    h.completed_count AS hybrid_done,
    h.failed_count AS hybrid_failed,
    h.created_at AS hybrid_created_at,
    b.status AS batch_status,
    b.run_type,
    b.total_count AS batch_total,
    b.completed_count AS batch_done,
    b.failed_count AS batch_failed,
    b.created_at AS batch_created_at,
    COUNT(DISTINCT d.run_id) AS actual_dino_runs,
    COUNT(DISTINCT d.run_id) FILTER (WHERE d.status = 'DONE') AS actual_dino_done,
    COUNT(DISTINCT d.run_id) FILTER (WHERE d.status = 'FAILED') AS actual_dino_failed,
    COUNT(c.run_id) AS candidate_rows,
    COUNT(DISTINCT q.id) AS hybrid_jobs,
    COUNT(DISTINCT rh.run_id) AS sort_history_rows
FROM public.hybrid_runs AS h
JOIN public.dino_batches AS b
  ON b.batch_id = h.dino_batch_id
LEFT JOIN public.dino_runs AS d
  ON d.batch_id = b.batch_id
LEFT JOIN public.dino_candidates AS c
  ON c.run_id = d.run_id
LEFT JOIN public.job_queue AS q
  ON q.job_type = 'HYBRID_RUN'
 AND q.payload ->> 'hybrid_run_id' = h.hybrid_run_id::text
LEFT JOIN public.run_history AS rh
  ON rh.kind = 'sort'
 AND rh.source_id = h.hybrid_run_id::text
WHERE h.status = 'PENDING'
  AND q.id IS NULL
GROUP BY h.hybrid_run_id, b.batch_id
ORDER BY h.hybrid_run_id
"""


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
    args = parser.parse_args()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            database, user = cur.fetchone()
            cur.execute(QUERY)
            columns = [item.name for item in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]

    summary = f"database={database} user={user} pending_orphans={len(rows)}"

    if args.format == "json":
        print(json.dumps(
            {
                "database": database,
                "user": user,
                "pending_orphans": len(rows),
                "items": rows,
            },
            ensure_ascii=False,
            indent=2,
            default=_json_value,
        ))
    elif args.format == "csv":
        print(summary, file=sys.stderr)
        writer = csv.DictWriter(sys.stdout, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    else:
        print(summary)
        for row in rows:
            print(
                "hybrid={hybrid_run_id} batch={dino_batch_id} "
                "hybrid={hybrid_status}({hybrid_done}/{hybrid_total},fail={hybrid_failed}) "
                "batch={batch_status}/{run_type}({batch_done}/{batch_total},fail={batch_failed}) "
                "actual_dino={actual_dino_runs} done={actual_dino_done} "
                "failed={actual_dino_failed} candidates={candidate_rows} "
                "history={sort_history_rows} created={hybrid_created_at}".format(**row)
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
