#!/usr/bin/env python3
"""Fill photo_regions.crop_phash_p (pHash) for existing billboard crops.

    .venv/bin/python scripts/backfill_crop_phash_p.py --limit 500
    .venv/bin/python scripts/backfill_crop_phash_p.py          # all missing

Only the hash column is updated; files and other fields are untouched.
"""

from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor

from app.billboard.phash import file_phash, to_db
from app.ingest.database import get_connection


def _hash_one(row: tuple[int, str]) -> tuple[int, int | None]:
    region_id, path = row
    value = file_phash(path)
    return region_id, (to_db(value) if value is not None else None)


def pending(limit: int | None) -> list[tuple[int, str]]:
    sql = (
        "SELECT region_id, crop_path FROM public.photo_regions "
        "WHERE kind = 'billboard' AND crop_phash_p IS NULL "
        "AND crop_path IS NOT NULL ORDER BY region_id"
    )
    params: tuple = ()
    if limit:
        sql += " LIMIT %s"
        params = (int(limit),)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql, params)
            return [(int(row[0]), str(row[1])) for row in cur.fetchall()]


def write(updates: list[tuple[int, int]]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE public.photo_regions SET crop_phash_p = %s "
                "WHERE region_id = %s",
                [(value, region_id) for region_id, value in updates],
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="0 = все")
    parser.add_argument("--batch", type=int, default=500)
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="процессов расчёта (0 = авто: до 8)",
    )
    args = parser.parse_args()

    rows = pending(args.limit or None)
    print(f"pending: {len(rows)}")
    started = time.perf_counter()
    done = missing = 0
    workers = args.workers or min(8, max(1, (os.cpu_count() or 1) // 2))
    print(f"workers: {workers}")

    def hashed(chunk):
        if workers <= 1:
            return [_hash_one(row) for row in chunk]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(_hash_one, chunk))

    for offset in range(0, len(rows), max(1, args.batch)):
        chunk = rows[offset:offset + max(1, args.batch)]
        updates = []

        for region_id, value in hashed(chunk):
            if value is None:
                missing += 1
                continue
            updates.append((region_id, value))

        if updates:
            write(updates)
            done += len(updates)

        print(
            f"  {min(offset + len(chunk), len(rows))}/{len(rows)} "
            f"updated={done} unreadable={missing}",
            flush=True,
        )

    print(
        f"done: {done}, unreadable: {missing}, "
        f"elapsed: {time.perf_counter() - started:.1f}s"
    )


if __name__ == "__main__":
    main()
