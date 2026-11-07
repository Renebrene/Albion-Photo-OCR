#!/usr/bin/env python3
"""Read-only/dry-run reconciliation of the new photo corpus with the DB.

The current production identity scheme is ``metadata-v1`` (EXIF serial +
capture time + subsecond + byte size).  Most files can therefore be matched
without reading their content:

1. by the same relative path under the old and new roots;
2. otherwise by metadata identity (renamed/moved copies);
3. only files with incomplete metadata fall back to content SHA-256.

The script never deletes photos, QWEN rows or previews.  In ``--apply`` mode
it only updates ``source_path``/``filename``/``size_bytes`` and inserts new
photos.  Missing originals are reported for a separate preview cleanup.

    .venv/bin/python scripts/reconcile_new_corpus.py --dry-run
    .venv/bin/python scripts/reconcile_new_corpus.py --apply --confirm RECONCILE
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection, insert_photos  # noqa: E402
from app.ingest.metadata_pipeline import process_file_metadata  # noqa: E402
from app.ingest.metadata_register import insert_metadata_photos  # noqa: E402

OUT = Path("data/experiments/reconcile_new_corpus")
REPORT = Path(f"data/reports/reconcile_new_corpus_{date.today():%Y%m%d}.md")
DEFAULT_ROOT = Path("/media/alexice/TEST/новаябазафото")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
OLD_MARKERS = ("/БАЗАФОТО/", "/новаябазафото/")


def discover_images(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def relative_old(source_path: str) -> str | None:
    text = str(source_path or "")
    for marker in OLD_MARKERS:
        if marker in text:
            return text.split(marker, 1)[1]
    return None


def load_photos() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, source_path, filename, size_bytes,
                       sha256, identity_hash, identity_scheme
                FROM public.photos
                """
            )
            return [
                {
                    "photo_id": str(row[0]),
                    "source_path": str(row[1]),
                    "filename": str(row[2]),
                    "size_bytes": int(row[3]) if row[3] is not None else None,
                    "sha256": str(row[4]) if row[4] else None,
                    "identity_hash": str(row[5]) if row[5] else None,
                    "identity_scheme": str(row[6]),
                }
                for row in cur.fetchall()
            ]


def process_many(paths: list[Path], workers: int) -> list[tuple[Path, object | None, str | None]]:
    def one(path: Path):
        try:
            return path, process_file_metadata(path), None
        except Exception as exc:  # noqa: BLE001 - one bad file, not the run
            return path, None, str(exc)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(one, paths))


def backup() -> None:
    subprocess.run(
        [sys.executable, "scripts/backup_db.py", "--json"],
        check=True,
    )


def apply_updates(updates: list[tuple[str, str, str, int]]) -> int:
    if not updates:
        return 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for photo_id, source_path, filename, size_bytes in updates:
                cur.execute(
                    """
                    UPDATE public.photos
                    SET source_path = %s,
                        filename = %s,
                        size_bytes = %s
                    WHERE photo_id = %s
                    """,
                    (source_path, filename, size_bytes, photo_id),
                )
            return len(updates)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)

    if args.apply and args.dry_run:
        print("choose either --dry-run or --apply", file=sys.stderr)
        return 2
    if args.apply and args.confirm != "RECONCILE":
        print("refusing; pass --apply --confirm RECONCILE", file=sys.stderr)
        return 2
    if not args.root.is_dir():
        print(f"root not found: {args.root}", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    new_files = discover_images(args.root)
    if args.limit:
        new_files = new_files[: args.limit]
    print(f"[reconcile] new images: {len(new_files)}", flush=True)

    photos = load_photos()
    by_identity = {
        row["identity_hash"]: row
        for row in photos
        if row["identity_hash"]
    }
    by_sha = {
        row["sha256"]: row for row in photos if row["sha256"]
    }
    by_photo_id = {row["photo_id"]: row for row in photos}

    new_by_relative = {
        str(path.relative_to(args.root)).casefold(): path
        for path in new_files
    }

    reuse_path: list[tuple[dict, Path]] = []
    size_mismatch: list[tuple[dict, Path]] = []
    unmatched_old: list[dict] = []
    used_new: set[Path] = set()

    for row in photos:
        relative = relative_old(row["source_path"])
        path = new_by_relative.get(relative.casefold()) if relative else None
        if path is None:
            unmatched_old.append(row)
            continue
        used_new.add(path)
        if row["size_bytes"] is None or path.stat().st_size == row["size_bytes"]:
            reuse_path.append((row, path))
        else:
            size_mismatch.append((row, path))

    remaining = [path for path in new_files if path not in used_new]
    print(
        f"[reconcile] path matches={len(reuse_path)} "
        f"size_mismatch={len(size_mismatch)} "
        f"unmatched_old={len(unmatched_old)} "
        f"remaining_new={len(remaining)}",
        flush=True,
    )

    processed = process_many(remaining, args.workers)
    reuse_identity: list[tuple[dict, Path, object]] = []
    new_records: list[object] = []
    conflicts: list[dict] = []
    errors: list[dict] = []

    for path, record, error in processed:
        if record is None:
            errors.append({"path": str(path), "error": error})
            continue

        existing = None
        if getattr(record, "identity_hash", None):
            existing = by_identity.get(record.identity_hash)
        if existing is None and getattr(record, "sha256", None):
            existing = by_sha.get(record.sha256)
        if existing is None and record.photo_id in by_photo_id:
            existing = by_photo_id[record.photo_id]

        if existing is None:
            new_records.append(record)
        elif existing["photo_id"] == record.photo_id:
            reuse_identity.append((existing, path, record))
        else:
            # Same lifetime, different id: do not silently merge.
            conflicts.append(
                {
                    "path": str(path),
                    "new_id": record.photo_id,
                    "existing_id": existing["photo_id"],
                }
            )

    # Deduplicate new records by photo_id (two paths can share an identity).
    unique_new: dict[str, object] = {}
    duplicate_new: list[str] = []
    for record in new_records:
        if record.photo_id in unique_new:
            duplicate_new.append(record.photo_id)
        else:
            unique_new[record.photo_id] = record
    new_records = list(unique_new.values())

    # One photo_id -> exactly one path.  An exact old-path match wins over a
    # metadata-identity match; among identity duplicates the smallest path is
    # deterministic.
    update_map: dict[str, tuple[str, str, str, int]] = {}
    duplicate_paths: list[dict] = []

    for row, path in reuse_path:
        update_map[row["photo_id"]] = (
            row["photo_id"],
            str(path),
            path.name,
            path.stat().st_size,
        )

    for row, path, record in sorted(
        reuse_identity, key=lambda item: str(item[1])
    ):
        photo_id = row["photo_id"]
        if photo_id in update_map:
            duplicate_paths.append(
                {
                    "photo_id": photo_id,
                    "kept": update_map[photo_id][1],
                    "duplicate": str(path),
                }
            )
            continue
        update_map[photo_id] = (
            photo_id,
            str(path),
            path.name,
            int(record.size_bytes or path.stat().st_size),
        )

    updates = list(update_map.values())

    report = {
        "root": str(args.root),
        "new_images": len(new_files),
        "old_photos": len(photos),
        "reuse_path": len(reuse_path),
        "reuse_identity": len(reuse_identity),
        "new_photos": len(new_records),
        "size_mismatch": len(size_mismatch),
        "missing_old": len(unmatched_old),
        "conflicts": len(conflicts),
        "errors": len(errors),
        "duplicate_new": len(duplicate_new),
        "duplicate_paths": len(duplicate_paths),
        "apply": bool(args.apply),
        "updates": len(updates),
        "examples": {
            "reuse_identity": [
                {
                    "photo_id": row["photo_id"],
                    "old": row["source_path"],
                    "new": str(path),
                }
                for row, path, _record in reuse_identity[:10]
            ],
            "new_photos": [
                {
                    "photo_id": record.photo_id,
                    "path": record.source_path,
                }
                for record in new_records[:10]
            ],
            "missing_old": [
                {"photo_id": row["photo_id"], "path": row["source_path"]}
                for row in unmatched_old[:10]
            ],
            "size_mismatch": [
                {
                    "photo_id": row["photo_id"],
                    "old_size": row["size_bytes"],
                    "new_size": path.stat().st_size,
                    "path": str(path),
                }
                for row, path in size_mismatch[:10]
            ],
            "errors": errors[:30],
            "duplicate_paths": duplicate_paths[:20],
        },
    }

    if args.apply:
        if not args.no_backup:
            backup()
        changed = apply_updates(updates)
        metadata_records = [
            record
            for record in new_records
            if getattr(record, "identity_scheme", "") == "metadata-v1"
        ]
        legacy_records = [
            record
            for record in new_records
            if getattr(record, "identity_scheme", "") != "metadata-v1"
        ]
        inserted = 0
        if metadata_records:
            inserted += len(insert_metadata_photos(metadata_records))
        if legacy_records:
            inserted += len(insert_photos(legacy_records))
        report["updated"] = changed
        report["inserted"] = inserted

    with (OUT / "mapping.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["kind", "photo_id", "old_or_new_path", "new_path"])
        for row, path in reuse_path:
            writer.writerow(["reuse_path", row["photo_id"], row["source_path"], path])
        for row, path, _record in reuse_identity:
            writer.writerow(["reuse_identity", row["photo_id"], row["source_path"], path])
        for record in new_records:
            writer.writerow(["new", record.photo_id, "", record.source_path])
        for row in unmatched_old:
            writer.writerow(["missing", row["photo_id"], row["source_path"], ""])

    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Реконсиляция нового корпуса",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Режим: "
        f"{'APPLY' if args.apply else 'DRY-RUN'}.",
        "",
        f"Корень: `{args.root}`",
        "",
        "| Что | Кол-во |",
        "|---|---:|",
        f"| Новых файлов | {report['new_images']} |",
        f"| Старых фото в БД | {report['old_photos']} |",
        f"| Совпало по пути | {report['reuse_path']} |",
        f"| Совпало по identity (переименованы) | {report['reuse_identity']} |",
        f"| Новых фото | {report['new_photos']} |",
        f"| Изменился размер | {report['size_mismatch']} |",
        f"| Старых без файла (missing) | {report['missing_old']} |",
        f"| Конфликтов | {report['conflicts']} |",
        f"| Ошибок чтения | {report['errors']} |",
        f"| Дубликатов новых id | {report['duplicate_new']} |",
        f"| Дубликатов путей у одного photo_id | {report['duplicate_paths']} |",
        f"| Уникальных обновлений путей | {report['updates']} |",
        f"| Вставлено новых | {report.get('inserted', 0)} |",
        "",
        "## Примеры переименованных",
        "",
        "| photo_id | старый путь | новый путь |",
        "|---|---|---|",
    ]
    for item in report["examples"]["reuse_identity"]:
        lines.append(
            f"| {item['photo_id']} | {item['old']} | {item['new']} |"
        )
    lines += [
        "",
        "## Примеры missing",
        "",
        "| photo_id | путь |",
        "|---|---|",
    ]
    for item in report["examples"]["missing_old"]:
        lines.append(f"| {item['photo_id']} | {item['path']} |")

    lines += [
        "",
        "## Ошибки чтения",
        "",
        "| Путь | Ошибка |",
        "|---|---|",
    ]
    for item in report["examples"]["errors"]:
        lines.append(f"| {item['path']} | {item['error']} |")

    lines += [
        "",
        "## Дубли путей у одного photo_id",
        "",
        "| photo_id | оставлен | дубль |",
        "|---|---|---|",
    ]
    for item in report["examples"]["duplicate_paths"]:
        lines.append(
            f"| {item['photo_id']} | {item['kept']} | {item['duplicate']} |"
        )

    (OUT / "duplicates.json").write_text(
        json.dumps(duplicate_paths, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (OUT / "errors.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)[:3000], flush=True)
    print(f"[reconcile] report: {REPORT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
