"""Удалить кропы, которые уже не нужны для распознавания.

Кроп — временный файл: он нужен QWEN только на время анализа и удаляется сразу
после успешного сохранения описания. Этот скрипт убирает накопленные кропы от
прошлых запусков (только для фото со статусом QWEN DONE и без активного задания).

    .venv/bin/python scripts/cleanup_crops.py --dry-run
    .venv/bin/python scripts/cleanup_crops.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.billboard.pipeline import discard_crop  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.region_id, r.photo_id, r.crop_path
                FROM public.photo_regions AS r
                JOIN public.photo_qwen AS q ON q.photo_id = r.photo_id
                WHERE q.status = 'DONE'
                  AND r.crop_path IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM public.job_queue AS j
                      WHERE j.job_type = 'QWEN_PHOTO'
                        AND j.status IN ('PENDING', 'RUNNING')
                        AND j.payload ->> 'photo_id' = r.photo_id
                  )
                ORDER BY r.region_id
                """
            )
            rows = cur.fetchall()

    removed = 0
    missing = 0
    failed = 0

    for region_id, photo_id, crop_path in rows:
        path = Path(crop_path)

        if not path.is_file():
            missing += 1
            continue

        if args.dry_run:
            print(f"[dry-run] {region_id} {photo_id} → {path}")
            removed += 1
            continue

        if discard_crop(path):
            removed += 1
        else:
            failed += 1

    print(
        f"candidates: {len(rows)} · removed: {removed} · "
        f"already missing: {missing} · failed: {failed}"
        + (" (dry-run)" if args.dry_run else "")
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
