#!/usr/bin/env python
"""
Backfill image names + capture dates into existing fingerprint metadata.

Fingerprints built before schema/024 have metadata.json with `image_names` but
neither `image_meta` (name + capture date per photo) nor `source_folder`. The
measurement window needs both, and the sources are still on disk under
data/input/, so they can be filled in now - once the originals are gone, the
information is lost.

What it does, per fingerprint that lacks image_meta:

  1. matches every `image_names` entry to a file under data/input/ (the folder
     named after the fingerprint's address is preferred);
  2. reads the capture date (EXIF DateTimeOriginal, best-effort) of each match;
  3. rewrites metadata.json atomically, adding `image_meta` and `source_folder`
     - the vectors and every other key are untouched;
  4. optionally refreshes the registry (app.api.fingerprints.sync_from_disk).

Usage:
    python scripts/backfill_fingerprint_meta.py --dry-run
    python scripts/backfill_fingerprint_meta.py

Only reads the source photos; nothing is copied or modified there.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FINGERPRINTS = ROOT / "data" / "fingerprints"
DEFAULT_SOURCES = ROOT / "data" / "input"


def build_name_index(sources_root: Path) -> dict[str, list[Path]]:
    """{lowercase file name: [paths]} for every photo under the sources root."""

    index: dict[str, list[Path]] = {}

    if not sources_root.is_dir():
        return index

    for path in sources_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}:
            index.setdefault(path.name.lower(), []).append(path)

    return index


def resolve_photo(
    name: str,
    index: dict[str, list[Path]],
    *,
    preferred_folder: Path | None,
) -> Path | None:
    """Prefer the folder named after the address, else any match."""

    candidates = index.get(name.lower())

    if not candidates:
        return None

    if preferred_folder is not None:
        for candidate in candidates:
            if candidate.parent == preferred_folder:
                return candidate

    return sorted(candidates)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fingerprints", type=Path, default=DEFAULT_FINGERPRINTS)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Do not refresh the PostgreSQL registry afterwards",
    )
    args = parser.parse_args()

    if not args.fingerprints.is_dir():
        print(f"нет каталога слепков: {args.fingerprints}", file=sys.stderr)
        return 2

    index = build_name_index(args.sources)

    if not index:
        print(f"нет исходных фото в {args.sources}", file=sys.stderr)
        return 2

    print(f"исходных файлов в индексе: {sum(len(v) for v in index.values())}")

    sys.path.insert(0, str(ROOT))
    from app.core.fingerprint import image_meta

    changed: list[str] = []

    for directory in sorted(args.fingerprints.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue

        metadata_file = directory / "metadata.json"

        if not metadata_file.is_file():
            continue

        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"  {directory.name}: не читается metadata.json ({exc})")
            continue

        if metadata.get("image_meta"):
            continue

        names = metadata.get("image_names") or []

        if not names:
            print(f"  {directory.name}: список имён пуст — пропуск")
            continue

        address = directory.name.split("_")[0]
        preferred = args.sources / address
        preferred = preferred if preferred.is_dir() else None

        resolved = []
        missing = []

        for name in names:
            path = resolve_photo(str(name), index, preferred_folder=preferred)

            if path is None:
                missing.append(str(name))
            else:
                resolved.append(path)

        folder = None

        if resolved:
            parents = {path.parent for path in resolved}
            folder = parents.pop() if len(parents) == 1 else None

        print(
            f"  {directory.name}: найдено {len(resolved)}/{len(names)}, "
            f"папка={folder or 'смешанная'}"
            + (f", не найдено: {len(missing)}" if missing else "")
        )

        if args.dry_run or not resolved:
            continue

        metadata["image_meta"] = image_meta(resolved)

        if folder is not None:
            metadata["source_folder"] = str(folder)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=directory,
            prefix=".metadata-",
            suffix=".json",
            delete=False,
        ) as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temp_name = handle.name

        os.replace(temp_name, metadata_file)
        changed.append(directory.name)

    print(f"\nобновлено слепков: {len(changed)}" + (": " + ", ".join(changed) if changed else ""))

    if args.dry_run:
        print("(dry-run: файлы не изменялись)")
        return 0

    if changed and not args.no_sync:
        from app.api import fingerprints as registry

        result = registry.sync_from_disk()
        print("реестр:", {k: (len(v) if isinstance(v, list) else v) for k, v in result.items()})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
