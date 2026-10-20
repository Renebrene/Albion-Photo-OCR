#!/usr/bin/env python3
"""
Подготовка кропов для сравнения облачных VLM — без БД и без очереди.

Скрипт не зависит от текущего стенда: читает исходники только на чтение,
находит самый крупный рекламный щит тем же YOLO-World, что и рабочий
пайплайн, и вырезает его в полном разрешении в отдельный каталог
(по умолчанию /tmp/cloud_vlm_sample). Ничего не пишет в PostgreSQL и
не запускает заданий.

Пример:
    python scripts/cloud_vlm_crops.py --input test --count 10

Результат: manifest.json со списком файлов и кропов; сам кроп — JPEG.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

DEFAULT_CLASSES = (
    "billboard",
    "digital billboard screen",
    "advertising screen",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="test",
        help="каталог с исходными фото (по умолчанию test)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="сколько кропов нужно (по умолчанию 10)",
    )
    parser.add_argument(
        "--out",
        default="/tmp/cloud_vlm_sample",
        help="каталог для кропов и manifest.json",
    )
    parser.add_argument(
        "--model",
        default="data/models/yolov8s-worldv2.pt",
        help="чекпоинт YOLO-World",
    )
    parser.add_argument("--score", type=float, default=0.4)
    parser.add_argument("--padding", type=float, default=0.02)
    parser.add_argument(
        "--max-side",
        type=int,
        default=1920,
        help="сторона копии для детекции (кроп всё равно из оригинала)",
    )
    parser.add_argument(
        "--max-crop-side",
        type=int,
        default=2048,
        help="длинная сторона сохраняемого кропа (как в рабочем пайплайне)",
    )
    parser.add_argument(
        "--scan-limit",
        type=int,
        default=120,
        help="сколько фото просмотреть максимум в поисках щитов",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="брать каждое фото: без щита — весь кадр (для сравнения моделей)",
    )
    return parser.parse_args()


def image_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def main() -> int:
    args = parse_args()

    from PIL import Image
    from ultralytics import YOLOWorld

    source = Path(args.input)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)

    files = image_files(source)
    if not files:
        raise SystemExit(f"нет изображений в {source}")

    model_path = Path(args.model)
    model = YOLOWorld(
        str(model_path) if model_path.is_file() else model_path.name
    )
    model.set_classes(list(DEFAULT_CLASSES))

    manifest: list[dict] = []

    for path in files[: args.scan_limit]:
        if len(manifest) >= args.count:
            break

        with Image.open(path) as image:
            image = image.convert("RGB")
            width, height = image.size

            scale = min(1.0, args.max_side / max(width, height))
            preview = (
                image.resize(
                    (max(1, round(width * scale)), max(1, round(height * scale))),
                    Image.LANCZOS,
                )
                if scale < 1.0
                else image
            )

            boxes = model.predict(preview, conf=args.score, verbose=False)[0].boxes
            best = None
            best_area = 0.0

            for box in boxes:
                x1, y1, x2, y2 = (float(value) for value in box.xyxy[0])
                area = (x2 - x1) * (y2 - y1)
                if area > best_area:
                    best_area = area
                    best = (x1, y1, x2, y2)

            if best is None and not args.all:
                continue

            if best is None:
                left, top, right, bottom = 0, 0, width, height
            else:
                pad_x = (best[2] - best[0]) * args.padding
                pad_y = (best[3] - best[1]) * args.padding
                left = max(0, round((best[0] - pad_x) / scale))
                top = max(0, round((best[1] - pad_y) / scale))
                right = min(width, round((best[2] + pad_x) / scale))
                bottom = min(height, round((best[3] + pad_y) / scale))

            if right - left < 32 or bottom - top < 32:
                continue

            crop = image.crop((left, top, right, bottom))
            crop.thumbnail((args.max_crop_side, args.max_crop_side), Image.LANCZOS)

            index = len(manifest) + 1
            name = f"crop_{index:02d}.jpg"
            target = output / name
            crop.save(target, "JPEG", quality=92)

            manifest.append(
                {
                    "index": index,
                    "source": str(path),
                    "crop": str(target),
                    "billboard": best is not None,
                    "source_width": width,
                    "source_height": height,
                    "crop_width": crop.width,
                    "crop_height": crop.height,
                }
            )
            print(
                f"{name}: {path.name} -> {crop.width}x{crop.height} "
                f"({'билборд' if best is not None else 'весь кадр'})",
                flush=True,
            )

    (output / "manifest.json").write_text(
        json.dumps(
            {"source": str(source), "items": manifest},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"готово: {len(manifest)} кропов в {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
