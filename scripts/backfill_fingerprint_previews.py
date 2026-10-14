"""
Create preview.jpg for fingerprints that were built before previews existed.

    python scripts/backfill_fingerprint_previews.py [--force] [--root DIR]

The builder now writes a montage of the source photos next to the vectors, so
the window can show what a fingerprint was made from even after the source
folder is deleted. Fingerprints built earlier have none; this reads each
metadata.json for its source folder and the exact photos used (image_meta),
composes the montage from those files while they are still there, and reports
the ones whose sources are gone - rebuilding from a folder is the only way to
give those a preview.

Nothing is touched when a preview already exists (unless --force).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.config import settings
from app.core.fingerprint import PREVIEW_NAME, build_preview


def _source_paths(metadata: dict) -> list[Path]:
    """The files the fingerprint was built from, as long as they still exist."""

    folder = metadata.get("source_folder")

    if not folder:
        return []

    folder = Path(folder)

    if not folder.is_dir():
        return []

    meta = metadata.get("image_meta")

    names = [
        str(item.get("name"))
        for item in (meta if isinstance(meta, list) else [])
        if isinstance(item, dict) and item.get("name")
    ] or [str(name) for name in (metadata.get("image_names") or [])]

    return [folder / name for name in names if (folder / name).is_file()]


def main() -> int:
    parser = argparse.ArgumentParser(description="backfill fingerprint previews")
    parser.add_argument(
        "--root",
        default=None,
        help="fingerprints root (default: data/fingerprints)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild previews that already exist",
    )
    args = parser.parse_args()

    root = Path(args.root) if args.root else Path(settings.fingerprints_dir)

    if not root.is_dir():
        print(f"нет каталога слепков: {root}", file=sys.stderr)
        return 2

    made = skipped = missing = 0

    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue

        metadata_file = directory / "metadata.json"

        if not metadata_file.is_file():
            continue

        target = directory / PREVIEW_NAME

        if target.exists() and not args.force:
            skipped += 1
            continue

        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print(f"{directory.name}: metadata.json не читается")
            missing += 1
            continue

        paths = _source_paths(metadata)

        if not paths:
            print(
                f"{directory.name}: исходных фото нет "
                f"({metadata.get('source_folder')}) — нужна пересборка"
            )
            missing += 1
            continue

        if build_preview(paths, target) is None:
            print(f"{directory.name}: ни одно фото не удалось прочитать")
            missing += 1
            continue

        print(f"{directory.name}: превью собрано из доступных фото ({len(paths)} шт.)")
        made += 1

    print(f"\nсобрано: {made}, без превью: {missing}, пропущено (уже есть): {skipped}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
