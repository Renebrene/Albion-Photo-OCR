#!/usr/bin/env python
"""
Заполнить identity_hash у существующих фото (перед включением metadata-v1).

Скрипт читает только EXIF и размер файла: содержимое не хешируется и не
декодируется. photo_id, sha256 и исходники не меняются — заполняется только
новая колонка identity_hash (schema/048).

Зачем: после переключения регистрации новый файл ищется по identity_hash.
Если у старых строк колонка пуста, повторный ингест того же файла создаст
дубль. Backfill закрывает эту дыру заранее.

    .venv/bin/python scripts/backfill_photo_identity.py --dry-run
    .venv/bin/python scripts/backfill_photo_identity.py
    .venv/bin/python scripts/backfill_photo_identity.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.ingest.database import get_connection  # noqa: E402
from app.ingest.identity_v2 import create_metadata_identity  # noqa: E402
from app.ingest.integrity import (  # noqa: E402
    read_identity_metadata,
    read_taken_at,
)


def identity_of(path: Path, size_bytes: int):
    with Image.open(path) as image:
        taken_at = read_taken_at(image)
        metadata = read_identity_metadata(image)

    return create_metadata_identity(
        metadata["exif_serial"],
        taken_at,
        metadata["exif_subsec"],
        size_bytes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, source_path, sha256
                FROM public.photos
                WHERE identity_hash IS NULL
                ORDER BY photo_id
                """
                + (" LIMIT %s" if args.limit else ""),
                (args.limit,) if args.limit else (),
            )
            rows = cur.fetchall()

            cur.execute(
                """
                SELECT photo_id, identity_hash, sha256
                FROM public.photos
                WHERE identity_hash IS NOT NULL
                """
            )
            by_hash = {row[1]: row for row in cur.fetchall()}

    report = {
        "dry_run": bool(args.dry_run),
        "candidates": len(rows),
        "updated": 0,
        "incomplete": 0,
        "missing": 0,
        "conflicts": 0,
        "conflict_samples": [],
        "errors": 0,
    }

    for photo_id, source_path, sha256 in rows:
        path = Path(source_path)

        try:
            if not path.is_file():
                report["missing"] += 1
                continue

            identity = identity_of(path, path.stat().st_size)
        except Exception as exc:  # noqa: BLE001 - one file must not stop a run
            report["errors"] += 1
            print(f"[skip] {photo_id}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue

        if not identity.complete:
            report["incomplete"] += 1
            continue

        existing = by_hash.get(identity.identity_hash)

        if existing is not None and existing[0] != photo_id:
            # Same metadata key already belongs to another row. Only a real
            # collision is a problem; byte-identical copies share the sha too.
            if existing[2] != sha256:
                report["conflicts"] += 1
                if len(report["conflict_samples"]) < 10:
                    report["conflict_samples"].append(
                        {
                            "photo_id": photo_id,
                            "other_photo_id": existing[0],
                            "identity_hash": identity.identity_hash,
                        }
                    )
                continue

        if args.dry_run:
            report["updated"] += 1
            by_hash[identity.identity_hash] = (photo_id, identity.identity_hash, sha256)
            continue

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE public.photos
                        SET identity_hash = %s
                        WHERE photo_id = %s
                          AND identity_hash IS NULL
                        """,
                        (identity.identity_hash, photo_id),
                    )

                    if cur.rowcount:
                        report["updated"] += 1
                        by_hash[identity.identity_hash] = (
                            photo_id,
                            identity.identity_hash,
                            sha256,
                        )
        except Exception as exc:  # noqa: BLE001 - UniqueViolation is a collision
            report["errors"] += 1
            print(f"[skip] {photo_id}: {type(exc).__name__}: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["conflicts"] else 0

    print(f"кандидатов: {report['candidates']}")
    print(
        f"  заполнено: {report['updated']}"
        + (" (dry-run)" if args.dry_run else "")
    )
    print(f"  без полного ключа: {report['incomplete']}")
    print(f"  файл недоступен: {report['missing']}")
    print(f"  коллизии: {report['conflicts']}")
    print(f"  ошибки: {report['errors']}")

    for sample in report["conflict_samples"]:
        print(
            f"    {sample['photo_id']} и {sample['other_photo_id']}: "
            f"{sample['identity_hash']}"
        )

    return 1 if report["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
