"""
Сцены в папках со снимками: отчёт о выборке 20–30 кадров.

    python scripts/scene_clusters.py --root data/input
    python scripts/scene_clusters.py --root data/input --json data/output/scenes.json

Сам отбор живёт в `app/core/scene_select.py` — его же использует сборка слепка
и замерный стенд, чтобы правила не разъезжались. Здесь только обход папок и
отчёт: сколько кадров, сколько серий почти одинаковых снимков, сколько сцен
нашлось, сколько взято в выборку и что именно выбрано (по --json).

Скрипт ничего не меняет: читает картинки и печатает результат.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.scene_select import (  # noqa: E402
    DEFAULT_DEDUP,
    DEFAULT_K_MAX,
    DEFAULT_K_MIN,
    DEFAULT_SELECT_MAX,
    DEFAULT_SELECT_MIN,
    SUPPORTED,
    select_scene_photos,
)


def folder_photos(folder: Path) -> list[Path]:
    """Кадры папки, отсортированные по имени."""

    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED
    )


def print_k_curve(result: dict, tail: int = 8) -> None:
    """Хвост кривой «k: силуэт» и выбранное k для одной папки."""

    scores = result.get("scores") or []

    if not scores:
        return

    curve = "  ".join(
        f"{item['k']}:{item['silhouette']:.3f}" for item in scores[-tail:]
    )
    silhouette = result.get("silhouette")

    print(
        f"  {result['address']:>4}  сцен={result['scenes']:>3} "
        f"(нашлось {result.get('natural_scenes', 0)})  "
        f"силуэт={f'{silhouette:.3f}' if silhouette is not None else '—'}  "
        f"хвост k→силуэт: {curve}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="сцены в папках со снимками")
    parser.add_argument("--root", type=Path, default=Path("data/input"))
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="процессов на декодирование (0 — по числу ядер)",
    )
    parser.add_argument("--dedup", type=int, default=DEFAULT_DEDUP)
    parser.add_argument("--k-min", type=int, default=DEFAULT_K_MIN)
    parser.add_argument("--k-max", type=int, default=DEFAULT_K_MAX)
    parser.add_argument(
        "--select-min",
        type=int,
        default=DEFAULT_SELECT_MIN,
        help="минимум кадров в выборке (меньше сцен — дробим мельче)",
    )
    parser.add_argument(
        "--select-max",
        type=int,
        default=DEFAULT_SELECT_MAX,
        help="максимум кадров в выборке (больше сцен — схлопываем)",
    )
    parser.add_argument(
        "--no-dhash",
        action="store_true",
        help="считать признак без dHash (pHash + цвет + яркость)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="принудительное число сцен (иначе автовыбор)",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="только эти папки (через запятую), например 78,79",
    )
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"нет папки: {args.root}", file=sys.stderr)
        return 2

    wanted = None

    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}

    folders = [
        folder
        for folder in sorted(args.root.iterdir())
        if folder.is_dir() and (wanted is None or folder.name in wanted)
    ]

    if not folders:
        print(f"в {args.root} нет подпапок", file=sys.stderr)
        return 2

    workers = args.workers or max(1, os.cpu_count() or 1)

    results = []

    print(
        f"папок: {len(folders)}, процессов: {workers}, "
        f"порог серии: {args.dedup}, диапазон сцен: {args.k_min}–{args.k_max}, "
        f"выборка: {args.select_min}–{args.select_max} кадров, "
        f"dHash: {'нет' if args.no_dhash else 'да'}, "
        f"k={'авто' if args.k is None else args.k}\n"
    )

    print(
        f"{'адрес':>8} {'фото':>5} {'кадров':>7} {'серий':>6} {'сцен':>5} "
        f"{'выборка':>7}  {'силуэт':>7}  сек"
    )

    for folder in folders:
        started = time.perf_counter()

        result = select_scene_photos(
            folder_photos(folder),
            workers=workers,
            dedup=args.dedup,
            k_min=args.k_min,
            k_max=args.k_max,
            select_min=args.select_min,
            select_max=args.select_max,
            use_dhash=not args.no_dhash,
            forced_k=args.k,
        )

        result["address"] = folder.name
        result["folder"] = str(folder)
        result["selected"] = len(result["picked"])
        result["seconds"] = round(time.perf_counter() - started, 2)
        result["error"] = None if result["hashed"] else "нет читаемых кадров"

        results.append(result)

        best = result.get("silhouette")

        print(
            f"{result['address']:>8} {result['photos']:>5} {result['hashed']:>7} "
            f"{result['series']:>6} {result['scenes']:>5} "
            f"{result['selected']:>7}  "
            f"{f'{best:.3f}' if best is not None else '—':>7}  {result['seconds']:>4}"
        )

    print("\nподбор числа сцен (хвост кривой «k: силуэт», последние 8 k):")

    for result in results:
        print_k_curve(result)

    scenes = [result["scenes"] for result in results if result["scenes"]]
    selected = [result["selected"] for result in results]
    grown = [
        result["address"] for result in results
        if result["scenes"] > result["natural_scenes"]
    ]
    shrunk = [
        result["address"] for result in results
        if result["scenes"] < result["natural_scenes"]
    ]

    if scenes:
        print(
            f"\nсцен на папку: мин {min(scenes)}, среднее "
            f"{sum(scenes) / len(scenes):.1f}, макс {max(scenes)}; "
            f"кадров в выборке: мин {min(selected)}, "
            f"среднее {sum(selected) / len(selected):.1f}, макс {max(selected)}"
        )

    if grown:
        print(f"дроблено до {args.select_min}: {', '.join(grown)}")

    if shrunk:
        print(f"схлопнуто до {args.select_max}: {', '.join(shrunk)}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"записано: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
