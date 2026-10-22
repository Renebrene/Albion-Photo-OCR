"""
Перцептивный хеш кропа: «тот же кадр» без сравнения картинок.

Для серий нужен дешёвый признак «на этих кадрах одно и то же изображение».
Хеш всего кадра не годится: щит занимает около 18 % площади, и хеш описывает
улицу — замер на корпусе показал, что почти одинаковые кадры несут разные
бренды. А хеш **кропа** разделяет: разница ≤ 6 → бренд совпадает в 82 %,
≥ 15 → в 14 % (docs/series_merge.md).

dHash 64 бита: изображение уменьшается до 9×8 в оттенках серого, каждый бит —
сравнение соседних пикселей. Устойчив к яркости и небольшому сдвигу, считается
за миллисекунды и не требует ни NumPy, ни модели.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

DEFAULT_SIZE = 8
# Порог из замера: при разнице ≤ 6 кадры считаются одним изображением.
DEFAULT_MAX_DISTANCE = 6


def image_dhash(image: Image.Image, size: int = DEFAULT_SIZE) -> int:
    """64-битный dHash готового изображения (PIL)."""

    if size < 1:
        raise ValueError("size must be >= 1")

    small = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    # Оттенки серого — один байт на пиксель, порядок построчный: ровно то, что
    # нужно для сравнения соседей, без промежуточного списка.
    pixels = small.tobytes()
    width = size + 1
    bits = 0

    for row in range(size):
        offset = row * width

        for column in range(size):
            left = pixels[offset + column]
            right = pixels[offset + column + 1]
            bits = (bits << 1) | (1 if left > right else 0)

    return bits


def file_dhash(path: str | Path, size: int = DEFAULT_SIZE) -> int | None:
    """dHash файла; None, если файл не читается (кроп мог не создаться)."""

    try:
        with Image.open(path) as image:
            return image_dhash(image, size)
    except Exception:  # noqa: BLE001 - хеш вспомогательный, не повод падать
        return None


def distance(left: int, right: int) -> int:
    """Расстояние Хэмминга между двумя хешами."""

    return int(left ^ right).bit_count()


def same_frame(left: int | None, right: int | None, max_distance: int = DEFAULT_MAX_DISTANCE) -> bool:
    """Один и тот же кадр по хешу (None — сравнить нельзя, считаем «нет»)."""

    if left is None or right is None:
        return False

    return distance(left, right) <= max_distance
