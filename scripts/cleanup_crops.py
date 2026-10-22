"""Retention cleanup for temporary billboard crops.

Algorithm
---------
1. Crops are kept after a successful QWEN: a separate series pass
   (docs/series_merge.md) groups frames of one screen by the crop hash. They
   are removed only by age — ``--older-than-days`` (default 7) — so the pass
   has time to run; if it does not run within that window, the crops go.
2. Crops of FAILED or not-yet-described photos follow the same age rule: a
   retry does not have to re-detect the billboard.
3. Directories under SCENE_CROPS_ROOT that do not belong to a known
   photo_regions row are orphans; they are removed only after the same age
   threshold.
4. Active jobs (PENDING/RUNNING/PAUSED) always win: such a photo is skipped.
5. Only paths inside the managed crop root are touched; `discard_crop()` also
   removes the marker and the empty directory after the last crop.

Examples
--------
    .venv/bin/python scripts/cleanup_crops.py --dry-run
    .venv/bin/python scripts/cleanup_crops.py --older-than-days 7 --json
    .venv/bin/python scripts/cleanup_crops.py --max-delete 5000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.billboard import pipeline as billboard_pipeline  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402

ACTIVE_STATUSES = ("PENDING", "RUNNING", "PAUSED")
ACTIVE_JOB_TYPES = ("QWEN_PHOTO", "BILLBOARD_DETECT", "QWEN_CROP")


def _crop_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.glob("crop_*.jpg") if path.is_file()
    )


def _age_cutoff(days: int) -> float:
    return time.time() - max(0, int(days)) * 86400


def _directory_mtime(directory: Path) -> float:
    try:
        return directory.stat().st_mtime
    except OSError:
        return 0.0


def _eligible(qwen_status: str | None, directory: Path, cutoff: float) -> bool:
    """
    Кроп удаляется только по возрасту — независимо от статуса QWEN.

    Раньше кропы DONE-фото удалялись сразу как «прочитанные». Теперь после
    описания по ним идёт прогон серий, поэтому статус ничего не ускоряет:
    иначе кропы исчезли бы до того, как прогон их увидит.
    """

    return _directory_mtime(directory) < cutoff


def _known_photos(cur) -> dict[str, str | None]:
    cur.execute(
        """
        SELECT r.photo_id, q.status
        FROM (SELECT DISTINCT photo_id FROM public.photo_regions) AS r
        LEFT JOIN public.photo_qwen AS q ON q.photo_id = r.photo_id
        """
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def _active_photos(cur) -> set[str]:
    cur.execute(
        """
        SELECT DISTINCT payload ->> 'photo_id'
        FROM public.job_queue
        WHERE status = ANY(%s)
          AND job_type = ANY(%s)
          AND payload ? 'photo_id'
        """,
        (list(ACTIVE_STATUSES), list(ACTIVE_JOB_TYPES)),
    )
    return {row[0] for row in cur.fetchall() if row[0]}


def _photo_files(photo_id: str) -> list[Path]:
    directory = billboard_pipeline.crop_dir(photo_id)
    return _crop_files(directory)


def _orphan_dirs(root: Path, known: set[str], cutoff: float) -> list[Path]:
    if not root.is_dir():
        return []

    result = []
    for directory in root.iterdir():
        if not directory.is_dir() or directory.name in known:
            continue
        try:
            resolved = directory.resolve()
            resolved.relative_to(root.resolve())
        except (OSError, ValueError):
            continue
        if _directory_mtime(directory) < cutoff:
            result.append(directory)
    return sorted(result)


def _remove_files(paths: list[Path], *, dry_run: bool, max_delete: int) -> dict:
    stats = {
        "files": 0,
        "bytes": 0,
        "missing": 0,
        "failed": 0,
        "limited": False,
    }

    for path in paths:
        if max_delete and stats["files"] >= max_delete:
            stats["limited"] = True
            break

        try:
            size = path.stat().st_size
        except OSError:
            stats["missing"] += 1
            continue

        if dry_run:
            stats["files"] += 1
            stats["bytes"] += size
            continue

        if billboard_pipeline.discard_crop(path):
            stats["files"] += 1
            stats["bytes"] += size
        else:
            stats["failed"] += 1

    return stats


def _remove_empty_orphan_dirs(directories: list[Path], *, dry_run: bool) -> int:
    removed = 0
    for directory in directories:
        if dry_run:
            removed += 1
            continue
        try:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
                removed += 1
        except OSError:
            pass
    return removed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--older-than-days", type=int, default=None,
        help="срок хранения кропов; по умолчанию — настройка этапа «Уточнение» (7 дней)",
    )
    parser.add_argument(
        "--max-delete", type=int, default=5000,
        help="hard cap of crop files per run; 0 = unlimited",
    )
    parser.add_argument(
        "--skip-orphans", action="store_true",
        help="do not scan directories without a photo_regions row",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.older_than_days is None:
        # Срок хранения задаётся в настройках этапа: если владелец увеличил
        # его, чистка обязана подождать, иначе кропы исчезнут до прогона.
        try:
            from app.refine import config as refine_config

            args.older_than_days = refine_config.retention_days()
        except Exception:  # noqa: BLE001 - без базы остаётся 7 дней
            args.older_than_days = 7

    if args.older_than_days < 0:
        print("--older-than-days must be >= 0", file=sys.stderr)
        return 2
    if args.max_delete < 0:
        print("--max-delete must be >= 0", file=sys.stderr)
        return 2

    started = time.monotonic()
    root = billboard_pipeline.CROPS_ROOT
    cutoff = _age_cutoff(args.older_than_days)
    report = {
        "dry_run": bool(args.dry_run),
        "older_than_days": args.older_than_days,
        "max_delete": args.max_delete,
        "known_candidates": 0,
        "orphan_dirs": 0,
        "files": 0,
        "bytes": 0,
        "missing": 0,
        "failed": 0,
        "limited": False,
        "empty_dirs_removed": 0,
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            known = _known_photos(cur)
            active = _active_photos(cur)

    known_ids = set(known)
    paths: list[Path] = []

    for photo_id in sorted(known_ids - active):
        directory = billboard_pipeline.crop_dir(photo_id)
        files = _photo_files(photo_id)

        if not files:
            continue

        if _eligible(known.get(photo_id), directory, cutoff):
            paths.extend(files)
            report["known_candidates"] += len(files)

    orphan_removed = 0
    if not args.skip_orphans:
        orphans = _orphan_dirs(root, known_ids, cutoff)
        report["orphan_dirs"] = len(orphans)
        for directory in orphans:
            paths.extend(_crop_files(directory))

        # Orphan directories may contain only a stale marker or an empty dir.
        # Remove those only when the age threshold is met.
        stale_empty = [
            directory for directory in orphans if not _crop_files(directory)
        ]
        orphan_removed = _remove_empty_orphan_dirs(
            stale_empty, dry_run=args.dry_run
        )

    stats = _remove_files(
        paths,
        dry_run=args.dry_run,
        max_delete=args.max_delete,
    )
    report.update(stats)
    report["empty_dirs_removed"] = orphan_removed
    report["duration_sec"] = round(time.monotonic() - started, 3)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"known files: {report['known_candidates']} · "
            f"orphan dirs: {report['orphan_dirs']} · "
            f"files removed: {report['files']} · "
            f"bytes: {report['bytes']} · "
            f"missing: {report['missing']} · failed: {report['failed']} · "
            f"empty dirs: {report['empty_dirs_removed']}"
            + (" (dry-run)" if args.dry_run else "")
            + (" [limit reached]" if report["limited"] else "")
        )

    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
