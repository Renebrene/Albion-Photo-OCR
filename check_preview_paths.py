#!/usr/bin/env python3
"""
Проверить длину путей к превью.
Ищет фото, для которых путь k data/previews/{size}/{photo_id}.{ext}
может превышать 64 символа (ограничение многих файловых систем).

Вызов: python check_preview_paths.py [--preview-root PATH]
"""

from pathlib import Path
import os
import sys

# Дефолтные пути
PREVIEW_ROOT = os.getenv("SCENE_PREVIEW_ROOT", "data/preview")

def path_length_check(photo_id: str, size: str) -> tuple[int, Path]:
    """Проверить длину пути к превью данного размера."""
    small_path = f"{PREVIEW_ROOT}/{size}/{photo_id}.jpg"
    return len(small_path), Path(small_path)


def main():
    print(f"Проверка путей превью (root: {PREVIEW_ROOT})")
    print("=" * 60)

    # Дефолтный порог: 255 символы для ext4, но некоторые ФС ограничивают 64-128 символов
    path_threshold = 255
    warning_threshold = 200  # Предупреждать за этим порогом

    found = []

    # Проверяем по всем папкам small и middle (и видео если нужно)
    for size in ["small", "middle"]:
        directory = Path(PREVIEW_ROOT) / size

        if not directory.exists():
            print(f"Папка {directory} не существует, пропускаю размер {size}")
            continue

        print(f"\nРазмер превью: {size}")

        # Берём первые 10 фото из директории
        preview_files = sorted(directory.glob("*.jpg"))[:10]

        for preview_file in preview_files:
            photo_id = preview_file.stem  # Имя без расширения

            # Полный путь относительно корня проекта
            root_path = Path.cwd() / path_length_check(photo_id, size)[1]
            full_path_len = len(str(root_path))

            status = "OK"
            if full_path_len > warning_threshold:
                status = f"WARNING ({warning_threshold})"
            elif full_path_len >= path_threshold:
                status = f"ERROR ({path_threshold})"

            print(f"  {photo_id[:30]}... -> {full_path_len} символов [{status}]")


if __name__ == "__main__":
    main()
