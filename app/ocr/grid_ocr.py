from __future__ import annotations

import argparse
import multiprocessing as mp
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
from paddleocr import PaddleOCR


# ============================================================
# Настройки
# ============================================================

GRID_ROWS = 10
GRID_COLS = 10

# Перекрытие соседних областей.
# 0.15 = 15%
OVERLAP = 0.15


# ============================================================
# Данные
# ============================================================

@dataclass
class Tile:
    index: int
    row: int
    col: int
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class OCRText:
    tile: Tile
    text: str
    confidence: float


# ============================================================
# OCR для worker-процесса
# ============================================================

_worker_ocr = None


def init_worker():
    """
    Каждый отдельный процесс создаёт собственный экземпляр OCR.
    """

    global _worker_ocr

    _worker_ocr = PaddleOCR(
        lang="ru",
        use_gpu=False,
    )


# ============================================================
# Создание сетки
# ============================================================

def create_tiles(
    width: int,
    height: int,
) -> list[Tile]:

    tiles = []

    tile_w = width / GRID_COLS
    tile_h = height / GRID_ROWS

    index = 0

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):

            base_x1 = int(col * tile_w)
            base_y1 = int(row * tile_h)

            base_x2 = int((col + 1) * tile_w)
            base_y2 = int((row + 1) * tile_h)

            extra_x = int(tile_w * OVERLAP)
            extra_y = int(tile_h * OVERLAP)

            x1 = max(
                0,
                base_x1 - extra_x,
            )

            y1 = max(
                0,
                base_y1 - extra_y,
            )

            x2 = min(
                width,
                base_x2 + extra_x,
            )

            y2 = min(
                height,
                base_y2 + extra_y,
            )

            tiles.append(
                Tile(
                    index=index,
                    row=row,
                    col=col,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )
            )

            index += 1

    return tiles


# ============================================================
# OCR одного тайла
# ============================================================

def process_tile(
    args,
) -> list[OCRText]:

    image_path, tile = args

    global _worker_ocr

    results = []

    try:
        result = _worker_ocr.ocr(
            str(image_path),
            cls=True,
        )

        if not result:
            return results

        if not result[0]:
            return results

        for line in result[0]:

            if not line or len(line) < 2:
                continue

            bbox = line[0]
            text_info = line[1]

            if not text_info or len(text_info) < 2:
                continue

            text = str(text_info[0])
            confidence = float(text_info[1])

            results.append(
                OCRText(
                    tile=tile,
                    text=text,
                    confidence=confidence,
                )
            )

    except Exception as exc:

        print(
            f"[TILE {tile.index:03d}] "
            f"OCR ERROR: {exc}",
            flush=True,
        )

    return results


# ============================================================
# Создание физических файлов тайлов
# ============================================================

def prepare_tile_files(
    image,
    tiles: list[Tile],
    temp_dir: Path,
):
    temp_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths = []

    for tile in tiles:

        crop = image[
            tile.y1:tile.y2,
            tile.x1:tile.x2,
        ]

        path = (
            temp_dir
            / f"tile_{tile.index:03d}.jpg"
        )

        ok = cv2.imwrite(
            str(path),
            crop,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                92,
            ],
        )

        if not ok:
            raise RuntimeError(
                f"Cannot save tile: {path}"
            )

        paths.append(
            (
                path,
                tile,
            )
        )

    return paths


# ============================================================
# Основной GRID OCR
# ============================================================

def run_grid_ocr(
    image_path: str | Path,
    workers: int = 4,
):

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = cv2.imread(
        str(image_path)
    )

    if image is None:
        raise RuntimeError(
            f"Cannot open image: {image_path}"
        )

    height, width = image.shape[:2]

    print()
    print("=" * 70)
    print("GRID OCR")
    print("=" * 70)

    print(
        f"Image: {image_path.name}"
    )

    print(
        f"Resolution: {width} x {height}"
    )

    print(
        f"Grid: {GRID_COLS} x {GRID_ROWS}"
    )

    print(
        f"Tiles: {GRID_COLS * GRID_ROWS}"
    )

    print(
        f"Overlap: {OVERLAP * 100:.0f}%"
    )

    print(
        f"Workers: {workers}"
    )

    # --------------------------------------------------------
    # Сетка
    # --------------------------------------------------------

    tiles = create_tiles(
        width,
        height,
    )

    # --------------------------------------------------------
    # Временные файлы тайлов
    # --------------------------------------------------------

    temp_dir = (
        Path("data/ocr_grid")
        / image_path.stem
    )

    tile_files = prepare_tile_files(
        image,
        tiles,
        temp_dir,
    )

    print(
        f"Tile directory: {temp_dir}"
    )

    print()
    print("Starting OCR...")
    print()

    start = time.perf_counter()

    tasks = [
        (
            path,
            tile,
        )
        for path, tile in tile_files
    ]

    all_results: list[OCRText] = []

    # --------------------------------------------------------
    # multiprocessing
    # --------------------------------------------------------

    ctx = mp.get_context("spawn")

    with ctx.Pool(
        processes=workers,
        initializer=init_worker,
    ) as pool:

        for results in pool.imap_unordered(
            process_tile,
            tasks,
        ):

            all_results.extend(
                results
            )

            for item in results:

                print(
                    f"[TILE {item.tile.index:03d}] "
                    f"row={item.tile.row} "
                    f"col={item.tile.col} "
                    f"confidence="
                    f"{item.confidence:.3f} "
                    f"text={item.text!r}",
                    flush=True,
                )

    elapsed = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # Сортируем результаты
    # ========================================================

    all_results.sort(
        key=lambda item: (
            item.tile.index,
            -item.confidence,
        )
    )

    # ========================================================
    # Сохраняем результаты
    # ========================================================

    result_file = (
        Path("data/ocr_grid")
        / f"{image_path.stem}_results.txt"
    )

    with result_file.open(
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            f"IMAGE: {image_path}\n"
        )

        f.write(
            f"RESOLUTION: "
            f"{width}x{height}\n"
        )

        f.write(
            f"GRID: "
            f"{GRID_COLS}x{GRID_ROWS}\n"
        )

        f.write(
            f"OVERLAP: "
            f"{OVERLAP}\n"
        )

        f.write(
            f"WORKERS: "
            f"{workers}\n"
        )

        f.write(
            f"TIME: "
            f"{elapsed:.3f}\n"
        )

        f.write(
            f"TEXT REGIONS: "
            f"{len(all_results)}\n\n"
        )

        for item in all_results:

            f.write(
                f"TILE "
                f"{item.tile.index:03d} "
                f"row={item.tile.row} "
                f"col={item.tile.col} "
                f"bbox=("
                f"{item.tile.x1},"
                f"{item.tile.y1},"
                f"{item.tile.x2},"
                f"{item.tile.y2}) "
                f"confidence="
                f"{item.confidence:.4f} "
                f"text={item.text!r}\n"
            )

    # ========================================================
    # Итог
    # ========================================================

    print()
    print("=" * 70)
    print("GRID OCR FINISHED")
    print("=" * 70)

    print(
        f"Time: {elapsed:.3f} sec"
    )

    print(
        f"Text regions: "
        f"{len(all_results)}"
    )

    print(
        f"Results: "
        f"{result_file}"
    )

    print("=" * 70)

    return all_results


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "OCR image using 10x10 grid"
        )
    )

    parser.add_argument(
        "image",
        help="Input image",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help=(
            "Number of parallel OCR "
            "workers (default: 4)"
        ),
    )

    args = parser.parse_args()

    if args.workers < 1:
        parser.error(
            "--workers must be >= 1"
        )

    run_grid_ocr(
        args.image,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
