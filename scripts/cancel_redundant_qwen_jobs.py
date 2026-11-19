#!/usr/bin/env python3
"""Отмена дублирующих QWEN-заданий в активном прогоне.

    .venv/bin/python scripts/cancel_redundant_qwen_jobs.py --dry-run
    .venv/bin/python scripts/cancel_redundant_qwen_jobs.py --apply

Цель: PENDING-задания QWEN_PHOTO, у которых фото уже имеет непустое
описание (photo_qwen) И все его регионы описаны (qwen_status='DONE').
Такие задания перезаписывают годные описания (владелец: «сбилось
описание и уточнение», 19.11.2026). Перезапись оправдана только когда
есть незакрытые регионы (например, после понижения порога детекции).

Отмена статуса безопасна: строки job_queue остаются (аудит, ретеншн
по --done-days чистит их как CANCELLED), описания не трогаются.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402

BATCH = 2000


def redundant_predicate_sql() -> str:
    return """
        j.job_type = 'QWEN_PHOTO'
        AND j.status = 'PENDING'
        AND EXISTS (
            SELECT 1 FROM public.photo_qwen q
            WHERE q.photo_id = j.payload->>'photo_id'
              AND q.description IS NOT NULL
              AND btrim(q.description) <> ''
        )
        AND NOT EXISTS (
            SELECT 1 FROM public.photo_regions r
            WHERE r.photo_id = j.payload->>'photo_id'
              AND r.qwen_status IS DISTINCT FROM 'DONE'
        )
    """


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    if args.apply == args.dry_run:
        print("укажите ровно одно: --dry-run или --apply", file=sys.stderr)
        return 2

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT count(*) FROM public.job_queue j
                WHERE {redundant_predicate_sql()}
                """
            )
            total = cur.fetchone()[0]
            print(f"дублирующих PENDING-заданий: {total}")

            if args.dry_run:
                return 0

            cancelled = 0
            while True:
                cur.execute(
                    f"""
                    SELECT j.id FROM public.job_queue j
                    WHERE {redundant_predicate_sql()}
                    ORDER BY j.id
                    LIMIT {BATCH}
                    FOR UPDATE SKIP LOCKED
                    """
                )
                ids = [row[0] for row in cur.fetchall()]
                if not ids:
                    break
                cur.execute(
                    """
                    UPDATE public.job_queue
                    SET status = 'CANCELLED'
                    WHERE id = ANY(%s)
                    """,
                    (ids,),
                )
                cancelled += len(ids)
                conn.commit()
                print(f"отменено: {cancelled}/{total}", flush=True)

    print(f"итог: отменено {cancelled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
