"""Read-only report for adjacent QWEN descriptions in local test PostgreSQL.

Run explicitly with --confirm-local-test-db. The script refuses non-local host
or non-test database name and uses a read-only transaction. It never writes a
report file or updates database rows.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import psycopg

from app.billboard.phash import from_db
from app.refine.description_candidates import DescriptionFrame, analyze_adjacent_descriptions

_QUERY = """
    SELECT p.photo_id,
           COALESCE(r.photo_taken_at, p.taken_at) AS taken_at,
           r.crop_phash,
           COALESCE((
               SELECT h.hybrid_final_id
               FROM public.hybrid_results AS h
               WHERE h.photo_id = p.photo_id AND h.status = 'DONE'
               ORDER BY h.finished_at DESC NULLS LAST, h.hybrid_run_id DESC
               LIMIT 1
           ), '') AS screen,
           q.description
    FROM public.photo_regions AS r
    JOIN public.photos AS p ON p.photo_id = r.photo_id
    JOIN public.photo_qwen AS q
      ON q.photo_id = r.photo_id AND q.status = 'DONE'
    WHERE r.kind = 'billboard'
    ORDER BY screen, taken_at NULLS LAST, p.photo_id
"""


def _target() -> dict[str, str]:
    return {
        "host": os.getenv("INGEST_DB_HOST", "localhost"),
        "port": os.getenv("INGEST_DB_PORT", "5432"),
        "dbname": os.getenv("INGEST_DB_NAME", "photobase_ingest_test"),
        "user": os.getenv("INGEST_DB_USER", "lora_ingest"),
    }


def _validate_target(target: dict[str, str], confirmed: bool) -> None:
    host = target["host"].strip().lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Refusing non-local database host")
    if not target["dbname"].endswith("_test"):
        raise ValueError("Refusing database whose name does not end in _test")
    if not confirmed:
        raise ValueError("Pass --confirm-local-test-db after verifying the target")
    if not os.getenv("INGEST_DB_PASSWORD"):
        raise ValueError("INGEST_DB_PASSWORD is not configured")


def run_report(*, confirmed: bool, limit: int) -> dict:
    target = _target()
    _validate_target(target, confirmed)
    if limit < 1 or limit > 200_000:
        raise ValueError("--limit must be between 1 and 200000")

    connection = psycopg.connect(
        host=target["host"],
        port=target["port"],
        dbname=target["dbname"],
        user=target["user"],
        password=os.environ["INGEST_DB_PASSWORD"],
        connect_timeout=5,
        options="-c default_transaction_read_only=on -c statement_timeout=30000",
    )

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SELECT current_database(), inet_server_addr()::text")
                dbname, server_addr = cursor.fetchone()
                if dbname != target["dbname"]:
                    raise ValueError("Connected database name differs from the requested local test target")

                cursor.execute(_QUERY + " LIMIT %s", (limit + 1,))
                rows = cursor.fetchall()
                truncated = len(rows) > limit
                rows = rows[:limit]
    finally:
        connection.close()

    frames = [
        DescriptionFrame(
            photo_id=row[0],
            taken_at=row[1],
            crop_dhash=from_db(row[2]),
            screen=row[3],
            description=row[4],
        )
        for row in rows
    ]
    candidates = analyze_adjacent_descriptions(frames)
    return {
        "database": dbname,
        "server_addr": server_addr,
        "frames_scanned": len(frames),
        "truncated": truncated,
        "frames_with_description": sum(bool(frame.description and frame.description.strip()) for frame in frames),
        "frames_with_time": sum(frame.taken_at is not None for frame in frames),
        "frames_with_crop_dhash": sum(frame.crop_dhash is not None for frame in frames),
        "pairs_scored": len(candidates),
        "categories": dict(Counter(item.category for item in candidates)),
        "reason_counts": dict(Counter(reason for item in candidates for reason in item.reasons)),
        "high_confidence_samples": [
            {
                "left_description": item.left_description,
                "right_description": item.right_description,
                "seconds_apart": item.gap_seconds,
                "crop_dhash_distance": item.dhash_distance,
                "text_similarity": item.text_score,
            }
            for item in candidates
            if item.category == "high-confidence-candidate"
        ][:20],
        "thresholds": {
            "max_gap_seconds": 10,
            "max_crop_dhash_distance": 6,
            "min_text_length": 5,
            "min_text_similarity": 0.85,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-local-test-db", action="store_true")
    parser.add_argument("--limit", type=int, default=200_000, help="Maximum rows to fetch (default 200000)")
    args = parser.parse_args()

    try:
        result = run_report(confirmed=args.confirm_local_test_db, limit=args.limit)
    except Exception as exc:  # report sanitized errors only
        print(f"Report aborted: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
