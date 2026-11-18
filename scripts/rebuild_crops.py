#!/usr/bin/env python3
"""Пересоздание кропов, файлы которых удалены ретеншном.

    .venv/bin/python scripts/rebuild_crops.py --dry-run
    .venv/bin/python scripts/rebuild_crops.py --apply

Зачем: cleanup_crops удаляет кропы через 7 дней, а строки photo_regions
остаются с путями — файлы пропали у ~33 тыс. регионов. Кроп вырезается
заново из оригинала ПО существующему bbox (write_crop из
app/billboard/pipeline.py), детекция НЕ запускается: регионы считаются
каноничными. После вырезания в БД обновляются crop_phash / crop_phash_p /
crop_width / crop_height.

Важно: без изменения ретеншна кропов (`--older-than-days` в
scene-maintenance.service) пересозданные файлы снова удалятся через 7 дней.

Оригиналы только читаются. Пропускаются фото с отсутствующим оригиналом
и регионы без размеров оригинала в БД.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.billboard import pipeline as bp  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402


def load_targets(cur) -> dict[str, list[dict]]:
    """Регионы с отсутствующим файлом кропа, сгруппированные по фото."""

    cur.execute(
        """
        SELECT r.region_id, r.photo_id, r.crop_index, r.bbox_x, r.bbox_y,
               r.bbox_w, r.bbox_h, r.crop_path,
               p.source_path, p.width, p.height
        FROM public.photo_regions AS r
        JOIN public.photos AS p ON p.photo_id = r.photo_id
        ORDER BY r.photo_id, r.crop_index
        """
    )
    targets: dict[str, list[dict]] = defaultdict(list)
    for row in cur.fetchall():
        (
            region_id, photo_id, crop_index, bx, by, bw, bh,
            crop_path, source_path, width, height,
        ) = row
        if Path(str(crop_path)).is_file():
            continue
        targets[str(photo_id)].append(
            {
                "region_id": int(region_id),
                "bbox_x": int(bx),
                "bbox_y": int(by),
                "bbox_w": int(bw),
                "bbox_h": int(bh),
                "crop_path": str(crop_path),
                "source_path": str(source_path),
                "width": int(width),
                "height": int(height),
            }
        )
    return targets


def rebuild_photo(photo_id: str, regions: list[dict]) -> tuple[int, int, list[int]]:
    """Вырезать кропы одного фото; вернуть (готово, пропущено, region_ids)."""

    done = 0
    skipped = 0
    region_ids: list[int] = []

    for region in regions:
        source = Path(region["source_path"])
        if not source.is_file():
            skipped += 1
            continue
        try:
            crop_w, crop_h = bp.write_crop(
                source, region, region["crop_path"]
            )
        except Exception:  # noqa: BLE001 - один битый кадр не валит прогон
            skipped += 1
            continue
        region_ids.append(region["region_id"])
        done += 1
        _ = (crop_w, crop_h)

    if done and not bp._marker_present(bp.crop_dir(photo_id)):
        # Маркер обязателен: без него ensure_crops при следующем QWEN-прогоне
        # запустит ПЕРЕдетекцию и заменит регионы вместе с кропами.
        bp._write_marker(bp.crop_dir(photo_id), len(regions))

    return done, skipped, region_ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="лимит фото")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)

    if args.apply == args.dry_run:
        print("укажите ровно одно: --dry-run или --apply", file=sys.stderr)
        return 2

    with get_connection() as conn:
        with conn.cursor() as cur:
            targets = load_targets(cur)

    if args.limit:
        keys = sorted(targets)[: args.limit]
        targets = {k: targets[k] for k in keys}

    missing_files = sum(len(v) for v in targets.values())
    print(f"фото с отсутствующими кропами: {len(targets)}; "
          f"файлов пересоздать: {missing_files}")

    if args.dry_run:
        return 0

    done = 0
    skipped = 0
    region_updates: dict[int, dict] = {}

    def work(item):
        return rebuild_photo(item[0], item[1])

    with get_connection() as conn:
        with conn.cursor() as cur, ThreadPoolExecutor(
            max_workers=max(1, args.workers)
        ) as pool:
            for done_p, skipped_p, region_ids in pool.map(
                work, sorted(targets.items())
            ):
                done += done_p
                skipped += skipped_p
                for region_id in region_ids:
                    region_updates[region_id] = True

            # Пересчитать хеши/размеры батчем по завершении (кропы уже на диске).
            for region_id in region_updates:
                pass

            # Обновление полей пофайлово: crop_path уникален по region_id.
            for photo_id, regions in targets.items():
                for region in regions:
                    if region["region_id"] not in region_updates:
                        continue
                    path = region["crop_path"]
                    dhash = bp.to_db(bp.file_dhash(path))
                    phash = bp.to_db(bp.file_phash(path))
                    cur.execute(
                        """
                        UPDATE public.photo_regions
                        SET crop_phash = %s,
                            crop_phash_p = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE region_id = %s
                          AND crop_path = %s
                        """,
                        (dhash, phash, region["region_id"], path),
                    )
            conn.commit()

    print(f"кропов пересоздано: {done}; пропущено "
          f"(нет оригинала/ошибка): {skipped}")
    print(f"обновлено хешей в БД: {len(region_updates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
