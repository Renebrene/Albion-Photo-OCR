#!/usr/bin/env python3
"""Экспорт billboard-регионов в YOLO-датасет для дообучения YOLO-World.

    .venv/bin/python scripts/export_yolo_dataset.py --dry-run
    .venv/bin/python scripts/export_yolo_dataset.py --min-score 0.6 --val-split 5

Только чтение оригиналов: изображения подключаются символическими ссылками
(копирование — флагом --copy). Разбивка train/val детерминированная — по
хешу photo_id, поэтому повторный запуск даёт тот же сплит.

Выход (по умолчанию data/yolo/billboard_v1):
    images/{train,val}/<photo_id>.<ext>   — ссылка/копия оригинала
    labels/{train,val}/<photo_id>.txt     — строки "0 cx cy w h" (нормализовано)
    dataset.yaml                          — конфиг ultralytics (1 класс billboard)

Скалярный порог --min-score отсекает шум нулевого прогона (рекомендация —
0.6; хвост 0.4–0.6 годится для ручной проверки).

Пропускаются: фото с отсутствующим/недоступным оригиналом, регионы с
боксом вне границ изображения (подрезаются в границах, вырожденные —
отбрасываются), регионы без width/height оригинала в БД.
"""

from __future__ import annotations

import argparse
import os
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402

CLASS_ID = 0  # v1: один класс billboard; поле kind регионов на будущее


def val_bucket(photo_id: str, val_split: float) -> bool:
    """Детерминированный сплит: hash(photo_id) % 100 < val_split*100."""
    bucket = zlib.crc32(photo_id.encode("utf-8")) % 10000
    return bucket < int(val_split * 10000)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-score", type=float, default=0.6)
    parser.add_argument("--out", type=Path, default=Path("data/yolo/billboard_v1"))
    parser.add_argument("--val-split", type=float, default=0.05)
    parser.add_argument("--copy", action="store_true",
                        help="копировать оригиналы вместо символических ссылок")
    parser.add_argument("--limit", type=int, default=0, help="лимит фото (для пробы)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    out = args.out.resolve()
    if not args.dry_run:
        for sub in ("images/train", "images/val", "labels/train", "labels/val"):
            (out / sub).mkdir(parents=True, exist_ok=True)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.photo_id, r.bbox_x, r.bbox_y, r.bbox_w, r.bbox_h,
                   r.score, p.source_path, p.width, p.height
            FROM public.photo_regions AS r
            JOIN public.photos AS p ON p.photo_id = r.photo_id
            WHERE r.score >= %s
            ORDER BY r.photo_id
            """,
            (args.min_score,),
        )
        rows = cur.fetchall()

    by_photo: dict[str, list[tuple]] = {}
    source_by_photo: dict[str, str] = {}
    sizes_by_photo: dict[str, tuple[int, int]] = {}
    for _pid, bx, by, bw, bh, _score, source_path, width, height in rows:
        by_photo.setdefault(str(_pid), []).append(
            (int(bx), int(by), int(bw), int(bh), float(_score))
        )
        source_by_photo[str(_pid)] = str(source_path)
        sizes_by_photo[str(_pid)] = (int(width), int(height))

    photo_ids = sorted(by_photo)
    if args.limit:
        photo_ids = photo_ids[: args.limit]

    stats: dict[str, int] = {
        "photos": 0, "boxes": 0, "boxes_clipped": 0, "boxes_dropped": 0,
        "train": 0, "val": 0, "skipped_missing": 0, "skipped_size": 0,
    }
    skipped_paths: list[str] = []

    for photo_id in photo_ids:
        source = source_by_photo[photo_id]
        width, height = sizes_by_photo[photo_id]
        if not width or not height:
            stats["skipped_size"] += 1
            continue

        src = Path(source)
        if not src.is_file():
            stats["skipped_missing"] += 1
            if len(skipped_paths) < 10:
                skipped_paths.append(source)
            continue

        split = "val" if val_bucket(photo_id, args.val_split) else "train"
        stats[split] += 1
        stats["photos"] += 1

        lines: list[str] = []
        for bx, by, bw, bh, _score in by_photo[photo_id]:
            x0 = max(0, min(bx, width))
            y0 = max(0, min(by, height))
            x1 = max(0, min(bx + bw, width))
            y1 = max(0, min(by + bh, height))
            w = x1 - x0
            h = y1 - y0
            if w <= 0 or h <= 0:
                stats["boxes_dropped"] += 1
                continue
            if (x0, y0) != (bx, by) or (x1, y1) != (bx + bw, by + bh):
                stats["boxes_clipped"] += 1
            cx = (x0 + w / 2) / width
            cy = (y0 + h / 2) / height
            lines.append(
                f"{CLASS_ID} {cx:.6f} {cy:.6f} {w / width:.6f} {h / height:.6f}"
            )
            stats["boxes"] += 1

        if args.dry_run or not lines:
            if not lines:
                stats["boxes_dropped"] += len(by_photo[photo_id])
            continue

        img_name = f"{photo_id}{src.suffix.lower() or '.jpg'}"
        img_dst = out / "images" / split / img_name
        label_dst = out / "labels" / split / f"{photo_id}.txt"

        if args.copy:
            import shutil
            if not img_dst.exists():
                shutil.copy2(src, img_dst)
        else:
            if not img_dst.exists():
                os.symlink(src.resolve(), img_dst)

        label_dst.write_text("\n".join(lines) + "\n", encoding="utf-8")

    yaml_path = out / "dataset.yaml"
    if not args.dry_run:
        yaml_path.write_text(
            f"path: {out}\n"
            f"train: images/train\n"
            f"val: images/val\n"
            f"names:\n  {CLASS_ID}: billboard\n",
            encoding="utf-8",
        )

    print(f"фото с боксами: {len(photo_ids)}")
    print(f"экспортировано: {stats['photos']} (train {stats['train']} / "
          f"val {stats['val']}), боксов: {stats['boxes']}")
    print(f"боксов подрезано: {stats['boxes_clipped']}, "
          f"отброшено (вне кадра): {stats['boxes_dropped']}")
    print(f"пропущено: оригинал недоступен {stats['skipped_missing']}, "
          f"нет размеров {stats['skipped_size']}")
    if skipped_paths:
        for path in skipped_paths:
            print("  пример пропуска:", path)
    print(f"датасет: {out if not args.dry_run else '(dry-run)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
