#!/usr/bin/env python
"""
Backfill photos.size_bytes / photos.taken_at for already-registered photos.

Migration 018 adds the two columns empty; rows registered before it keep NULL
until this script re-reads their source file. Source files are only ever read
(opened), never modified, and only EXIF metadata is touched - no hashing, so
the run is cheap even for a large corpus.

Usage:
    python scripts/backfill_photo_metadata.py [--dry-run] [--limit N]

The database credentials come from the environment (INGEST_DB_*); the script
falls back to the documented service env file like scripts/set_password.py.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow running the script directly from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DEFAULT_ENV_FILE = Path.home() / ".config" / "scene-fingerprint.env"


def load_env_file(path: Path) -> list[str]:
    """Load KEY=VALUE lines from *path* into os.environ (existing keys win)."""

    loaded: list[str] = []

    if not path.is_file():
        return loaded

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)

    return loaded


def read_metadata(path: Path) -> tuple[int, str | None]:
    """
    (size_bytes, taken_at) of one source file.

    taken_at is None when the file carries no usable EXIF date; the caller
    still stores the size, so a second run does not re-read the file.
    """

    from PIL import Image

    from app.ingest.integrity import read_taken_at

    size_bytes = path.stat().st_size

    try:
        with Image.open(path) as image:
            return size_bytes, read_taken_at(image)
    except Exception:
        # Not decodable (or EXIF unreadable): the size is still worth storing.
        return size_bytes, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill photos.size_bytes / photos.taken_at"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing anything",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="process at most N photos",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=f"env file to fall back to (default: {DEFAULT_ENV_FILE})",
    )
    args = parser.parse_args()

    if not os.getenv("INGEST_DB_PASSWORD"):
        load_env_file(args.env_file)

    if not os.getenv("INGEST_DB_PASSWORD"):
        print(
            "error: INGEST_DB_PASSWORD is not set (export it or provide the "
            "deployment env file)",
            file=sys.stderr,
        )
        return 2

    from app.core.errors import redact_absolute_paths
    from app.ingest.database import get_connection

    sql = (
        "SELECT photo_id, source_path FROM public.photos "
        "WHERE size_bytes IS NULL OR taken_at IS NULL "
        "ORDER BY photo_id"
    )
    params: list[object] = []

    if args.limit:
        sql += " LIMIT %s"
        params.append(args.limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    checked = updated = missing = failed = 0
    updates: list[tuple[int, str | None, str]] = []

    for photo_id, source_path in rows:
        checked += 1
        path = Path(source_path)

        if not path.is_file():
            missing += 1
            continue

        try:
            size_bytes, taken_at = read_metadata(path)
        except Exception as exc:
            failed += 1
            print(f"error {photo_id}: {redact_absolute_paths(str(exc))}")
            continue

        updates.append((size_bytes, taken_at, photo_id))

    if not args.dry_run and updates:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    UPDATE public.photos
                    SET size_bytes = %s,
                        taken_at = COALESCE(taken_at, %s)
                    WHERE photo_id = %s
                    """,
                    updates,
                )
        updated = len(updates)

    with_dates = sum(1 for _, taken_at, _ in updates if taken_at)

    print(
        f"checked={checked} updated={updated if not args.dry_run else 0}"
        f" (would update {len(updates)}) with_capture_date={with_dates}"
        f" missing_files={missing} failed={failed}"
        + (" [dry-run]" if args.dry_run else "")
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
