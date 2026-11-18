#!/usr/bin/env python3
"""Повторная детекция щитов по фото без регионов.

Порог уверенности детектора поднят... точнее, снижен с 0.4 до 0.30
(settings_store: billboard_score), поэтому фото, где детекция вернула
0 регионов (щит был, но бокс не прошёл порог), детектируются повторно.

    .venv/bin/python scripts/enqueue_redetect_low_threshold.py --dry-run
    .venv/bin/python scripts/enqueue_redetect_low_threshold.py --apply

Целевое множество: QWEN_PHOTO DONE + нет строк в photo_regions.
Проверяется существование исходного файла; дедупликация активных
BILLBOARD_DETECT по фото встроена в enqueue_billboard_detect.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402
from app.jobs.database import enqueue_billboard_detect  # noqa: E402


def load_targets() -> tuple[list[dict], int]:
    """Фото с DONE QWEN и без регионов + счётчик пропущенных без файла."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id, p.source_path
                FROM public.photos AS p
                WHERE EXISTS (
                    SELECT 1 FROM public.job_queue AS j
                    WHERE j.job_type = 'QWEN_PHOTO'
                      AND j.status = 'DONE'
                      AND j.payload ->> 'photo_id' = p.photo_id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM public.photo_regions AS r
                    WHERE r.photo_id = p.photo_id
                )
                ORDER BY p.photo_id
                """
            )
            rows = cur.fetchall()

    targets: list[dict] = []
    missing = 0
    for photo_id, source_path in rows:
        if source_path and Path(str(source_path)).is_file():
            targets.append(
                {"photo_id": str(photo_id), "source_path": str(source_path)}
            )
        else:
            missing += 1
    return targets, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    if args.apply == args.dry_run:
        print("укажите ровно одно: --dry-run или --apply", file=sys.stderr)
        return 2

    targets, missing = load_targets()
    print(
        f"фото без регионов при DONE QWEN: {len(targets)}; "
        f"без файла на диске: {missing}"
    )

    if args.dry_run:
        return 0

    queued = 0
    deduped = 0
    for item in targets:
        job_id = enqueue_billboard_detect(item["photo_id"])
        if job_id is None:
            deduped += 1
        else:
            queued += 1
    print(f"поставлено: {queued}; пропущено активных: {deduped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
