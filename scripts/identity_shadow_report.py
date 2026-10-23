#!/usr/bin/env python
"""
Отчёт по metadata-v1 идентичности: можно ли переключать photo_id.

Скрипт только читает файлы и ничего не пишет в базу. Для каждого JPEG он
берёт ключ из EXIF (serial, дата съёмки с секундами, сотые доли) и размера
файла, строит будущий id и считает:

* сколько файлов имеют полный ключ;
* сколько получилось уникальных v2-id;
* группы повторов и — с `--with-sha` — есть ли среди них файлы с разным
  содержимым (это была бы настоящая коллизия).

Без `--with-sha` чтение ограничивается заголовком EXIF: ~0,5 мс на файл,
поэтому отчёт можно прогнать по всему архиву на NAS. С `--with-sha`
дополнительно читается весь файл (как сейчас делает INGEST).

    .venv/bin/python scripts/identity_shadow_report.py test
    .venv/bin/python scripts/identity_shadow_report.py /mnt/photos --json
    .venv/bin/python scripts/identity_shadow_report.py /mnt/photos --with-sha
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.ingest.identity_v2 import create_metadata_identity  # noqa: E402
from app.ingest.integrity import (  # noqa: E402
    SUPPORTED_EXTENSIONS,
    read_identity_metadata,
    read_taken_at,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan(root: Path, *, with_sha: bool, limit: int | None) -> dict:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if limit:
        files = files[:limit]

    by_id: dict[str, list[dict]] = defaultdict(list)
    incomplete = errors = 0
    started = time.perf_counter()

    for path in files:
        try:
            with Image.open(path) as image:
                taken_at = read_taken_at(image)
                metadata = read_identity_metadata(image)

            size = path.stat().st_size
            identity = create_metadata_identity(
                metadata["exif_serial"],
                taken_at,
                metadata["exif_subsec"],
                size,
            )
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop
            errors += 1
            print(f"[skip] {path}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue

        if not identity.complete:
            incomplete += 1

        by_id[identity.photo_id].append(
            {
                "path": str(path),
                "sha256": sha256_file(path) if with_sha else None,
                "complete": identity.complete,
            }
        )

    duplicates = {key: value for key, value in by_id.items() if len(value) > 1}
    collisions = []

    if with_sha:
        for key, items in duplicates.items():
            if len({item["sha256"] for item in items}) > 1:
                collisions.append(
                    {"v2_photo_id": key, "files": [item["path"] for item in items]}
                )

    return {
        "root": str(root),
        "with_sha": with_sha,
        "files": len(files),
        "errors": errors,
        "complete": len(files) - errors - incomplete,
        "incomplete": incomplete,
        "unique_ids": len(by_id),
        "duplicate_groups": len(duplicates),
        "duplicate_files": sum(len(value) for value in duplicates.values()),
        "collisions": len(collisions),
        "collision_samples": collisions[:10],
        "duration_sec": round(time.perf_counter() - started, 2),
        "ms_per_file": round(
            1000 * (time.perf_counter() - started) / max(1, len(files)), 2
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="папка с фотографиями")
    parser.add_argument("--with-sha", action="store_true", help="читать файл целиком")
    parser.add_argument("--limit", type=int, default=0, help="не больше N файлов")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.path)

    if not root.is_dir():
        raise SystemExit(f"не папка: {root}")

    report = scan(root, with_sha=args.with_sha, limit=args.limit or None)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"файлов: {report['files']} (ошибок чтения: {report['errors']})")
    print(f"  полный ключ:   {report['complete']}")
    print(f"  без ключа:     {report['incomplete']} (пойдут через SHA-фолбэк)")
    print(f"  уникальных id: {report['unique_ids']}")
    print(
        f"  повторы:       {report['duplicate_groups']} групп, "
        f"{report['duplicate_files']} файлов"
    )

    if args.with_sha:
        print(f"  коллизии (разное содержимое): {report['collisions']}")
        for sample in report["collision_samples"]:
            print(f"    {sample['v2_photo_id']}: {sample['files']}")

    print(
        f"\n{report['ms_per_file']} мс/файл, {report['duration_sec']} с всего"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
