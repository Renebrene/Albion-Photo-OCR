"""Read-only dry-run for agreed date-scoped description/tag enrichment.

No database writes or queue operations are performed. Run explicitly against a
local *_test database with --confirm-local-test-db.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import psycopg

from app.billboard.phash import from_db
from app.refine.scoped_proposals import EnrichmentFrame, propose_enrichment

DATE_FROM = "2026-09-01"
DATE_TO = "2026-10-29"

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
           q.description,
           q.tags
    FROM public.photo_regions AS r
    JOIN public.photos AS p ON p.photo_id = r.photo_id
    JOIN public.photo_qwen AS q
      ON q.photo_id = p.photo_id AND q.status = 'DONE'
    WHERE r.kind = 'billboard'
      AND COALESCE(r.photo_taken_at, p.taken_at) >= %s::date
      AND COALESCE(r.photo_taken_at, p.taken_at) < (%s::date + interval '1 day')
    ORDER BY screen, taken_at, p.photo_id
"""


def _target() -> dict[str, str]:
    return {
        "host": os.getenv("INGEST_DB_HOST", "localhost"),
        "port": os.getenv("INGEST_DB_PORT", "5432"),
        "dbname": os.getenv("INGEST_DB_NAME", "photobase_ingest_test"),
        "user": os.getenv("INGEST_DB_USER", "lora_ingest"),
    }


def run(*, confirmed: bool) -> dict:
    target = _target()
    if target["host"].lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Refusing non-local database host")
    if not target["dbname"].endswith("_test"):
        raise ValueError("Refusing database whose name does not end in _test")
    if not confirmed:
        raise ValueError("Pass --confirm-local-test-db after verifying the target")
    if not os.getenv("INGEST_DB_PASSWORD"):
        raise ValueError("INGEST_DB_PASSWORD is not configured")

    conn = psycopg.connect(
        host=target["host"], port=target["port"], dbname=target["dbname"],
        user=target["user"], password=os.environ["INGEST_DB_PASSWORD"],
        connect_timeout=5,
        options="-c default_transaction_read_only=on -c statement_timeout=30000",
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SELECT current_database()")
                dbname = cur.fetchone()[0]
                if dbname != target["dbname"]:
                    raise ValueError("Connected database name differs from requested target")
                cur.execute(_QUERY, (DATE_FROM, DATE_TO))
                rows = cur.fetchall()
    finally:
        conn.close()

    frames = [
        EnrichmentFrame(
            photo_id=str(row[0]), taken_at=row[1], crop_dhash=from_db(row[2]),
            screen=row[3], description=row[4], tags=tuple(row[5] or []),
        )
        for row in rows
    ]
    report = propose_enrichment(frames)
    fields = Counter(field for proposal in report.proposals for field in proposal.changes)
    changes = {
        "description_fills": sum("description" in item.changes for item in report.proposals),
        "tag_updates": sum("tags" in item.changes for item in report.proposals),
    }
    return {
        "database": dbname,
        "date_mode": "capture",
        "date_from": DATE_FROM,
        "date_to_inclusive": DATE_TO,
        "billboard_qwen_rows": len(frames),
        "proposal_photos": len(report.proposals),
        "proposed_field_counts": dict(fields),
        **changes,
        "conflict_groups": len(report.conflicts),
        "ineligible_pairs": dict(Counter(item["reason"] for item in report.ineligible_pairs)),
        "sample_proposals": [
            {"changes": item.changes}
            for item in report.proposals[:20]
        ],
        "conflict_samples": [
            {"descriptions": item["descriptions"], "reason": item["reason"]}
            for item in report.conflicts[:20]
        ],
        "writes_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-local-test-db", action="store_true")
    args = parser.parse_args()
    try:
        result = run(confirmed=args.confirm_local_test_db)
    except Exception as exc:  # show safe failure only; never print connection secrets
        print(f"Dry-run aborted: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
