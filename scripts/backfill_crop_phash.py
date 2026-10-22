#!/usr/bin/env python
"""
Заполнить хеши кропов у регионов, обработанных до появления «Уточнения».

У фото, описанных до этапа, кропы были удалены сразу после QWEN (старая
политика), поэтому `photo_regions.crop_phash` у них пуст. Кроп заново резать
не нужно: bbox региона известен, а содержимое экрана есть на MIDDLE preview —
хеш считается по нему (так же делались замеры в docs/series_merge.md).

    .venv/bin/python scripts/backfill_crop_phash.py --dry-run
    .venv/bin/python scripts/backfill_crop_phash.py --json
    .venv/bin/python scripts/backfill_crop_phash.py --limit 500

Скрипт меняет только `crop_phash`; время съёмки уже заполнено миграцией 046.
Повторный запуск безопасен: берутся только регионы с пустым хешем.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from app.api.config import PREVIEW_ROOT  # noqa: E402
from app.billboard.phash import image_dhash, to_db  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from app.preview.generator import build_preview_paths  # noqa: E402


def _frames(limit: int | None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.region_id, r.photo_id, r.bbox_x, r.bbox_y, r.bbox_w, r.bbox_h,
                       p.width, p.height, COALESCE(r.photo_taken_at, p.taken_at)
                FROM public.photo_regions AS r
                JOIN public.photos AS p ON p.photo_id = r.photo_id
                WHERE r.crop_phash IS NULL
                  AND r.kind = 'billboard'
                  AND p.width IS NOT NULL AND p.height IS NOT NULL
                ORDER BY r.region_id
                """
                + ("LIMIT %s" if limit else ""),
                (limit,) if limit else (),
            )
            return cur.fetchall()


def _crop_phash(row) -> int | None:
    """Хеш области щита, вырезанной из MIDDLE preview по координатам оригинала."""

    region_id, photo_id, x, y, width, height, original_w, original_h, _ = row

    path = build_preview_paths(preview_root=PREVIEW_ROOT, photo_id=str(photo_id)).middle

    if not path.is_file():
        return None

    try:
        with Image.open(path) as image:
            frame = image.convert("RGB")
            scale_x = frame.width / original_w
            scale_y = frame.height / original_h

            box = (
                max(0, int(x * scale_x)),
                max(0, int(y * scale_y)),
                min(frame.width, int((x + width) * scale_x)),
                min(frame.height, int((y + height) * scale_y)),
            )

            if box[2] - box[0] < 8 or box[3] - box[1] < 8:
                return None

            return to_db(image_dhash(frame.crop(box)))
    except Exception:  # noqa: BLE001 - битый/отсутствующий preview не повод падать
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Заполнить crop_phash у регионов")
    parser.add_argument("--dry-run", action="store_true", help="только посчитать")
    parser.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    parser.add_argument("--limit", type=int, default=0, help="не больше N регионов")
    args = parser.parse_args(argv)

    rows = _frames(args.limit or None)

    updated = 0
    missing_preview = 0
    failed = 0

    for row in rows:
        value = _crop_phash(row)

        if value is None:
            missing_preview += 1
            continue

        if args.dry_run:
            updated += 1
            continue

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE public.photo_regions SET crop_phash = %s "
                        "WHERE region_id = %s AND crop_phash IS NULL",
                        (value, row[0]),
                    )
            updated += 1
        except Exception:  # noqa: BLE001
            failed += 1

    report = {
        "dry_run": args.dry_run,
        "candidates": len(rows),
        "updated": updated,
        "no_preview": missing_preview,
        "failed": failed,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        action = "будет заполнено" if args.dry_run else "заполнено"
        print(f"регионов без хеша: {len(rows)}")
        print(f"{action}: {updated}")
        if missing_preview:
            print(f"нет preview: {missing_preview}")
        if failed:
            print(f"ошибок записи: {failed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
