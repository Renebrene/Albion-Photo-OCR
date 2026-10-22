"""Destructive reset of PhotoBase domain data for a full re-inspection.

This is intentionally NOT part of any timer. It preserves reference data
(users, sessions, address directory, fingerprints, aliases, settings) and
removes photos/videos, recognition results, queue/history, collections and
derived files. Originals are never touched.

Safety:
  * refuses while any job is PENDING/RUNNING/PAUSED;
  * makes a verified pg_dump backup first (unless --no-backup);
  * requires the literal --confirm RESET;
  * --dry-run prints what would be removed and changes nothing.

Example:
    .venv/bin/python scripts/reset_photobase.py --dry-run
    .venv/bin/python scripts/reset_photobase.py --confirm RESET
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.ingest.database import get_connection  # noqa: E402

# All domain tables. Reference tables are deliberately absent.
DOMAIN_TABLES = (
    "job_queue_archive",
    "job_queue",
    "run_history",
    "pipeline_runs",
    "photo_qwen_history",
    "photo_qwen",
    "hybrid_results",
    "hybrid_runs",
    "dino_candidates",
    "dino_runs",
    "dino_batches",
    "photo_regions",
    "photo_address_overrides",
    "photo_previews",
    "photos",
    "video_playback_tickets",
    "video_derivatives",
    "video_assets",
    "media_links",
    "collections",
    "saved_searches",
)

REFERENCE_TABLES = (
    "users", "sessions", "address_directory", "address_fingerprints",
    "fingerprints", "fingerprint_versions", "client_aliases",
    "client_alias_audit", "app_settings", "automation_settings",
    "manager_selections", "user_visits", "schema_migrations",
)


def _active_jobs(cur) -> int:
    cur.execute(
        "SELECT count(*) FROM public.job_queue "
        "WHERE status IN ('PENDING','RUNNING','PAUSED')"
    )
    return int(cur.fetchone()[0])


def _counts(cur) -> dict:
    result = {}
    for table in ("photos", "photo_qwen", "job_queue", "run_history"):
        cur.execute(f"SELECT count(*) FROM public.{table}")
        result[table] = int(cur.fetchone()[0])
    return result


def _existing_tables(cur) -> set[str]:
    cur.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public'"
    )
    return {row[0] for row in cur.fetchall()}


def _unique_roots(roots: list[Path]) -> list[Path]:
    """Absolute unique roots; a child of another root is dropped."""

    resolved = sorted({path.expanduser().resolve() for path in roots})
    result: list[Path] = []
    for path in resolved:
        if any(parent == path or parent in path.parents for parent in result):
            continue
        result.append(path)
    return result


def _remove_tree(path: Path) -> tuple[int, int]:
    if not path.is_dir():
        return (0, 0)
    files = 0
    size = 0
    for entry in path.rglob("*"):
        if entry.is_file() and not entry.is_symlink():
            files += 1
            try:
                size += entry.stat().st_size
            except OSError:
                pass
    return (files, size)


def _clear_tree(path: Path) -> None:
    if not path.is_dir():
        return
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child, ignore_errors=False)
        else:
            child.unlink(missing_ok=True)


def _backup() -> None:
    env = os.environ.copy()
    command = [
        sys.executable,
        str(REPO / "scripts" / "backup_db.py"),
        "--json",
    ]
    subprocess.run(command, env=env, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument("--no-files", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    data_dir = Path(os.getenv("SCENE_DATA", "data")).expanduser().resolve()
    preview_root = Path(
        os.getenv("SCENE_PREVIEW_ROOT", str(data_dir / "preview"))
    ).expanduser().resolve()
    derived_roots = _unique_roots([
        preview_root,
        Path(os.getenv("SCENE_VIDEO_PREVIEW_ROOT", str(preview_root / "videos"))),
        Path(os.getenv("SCENE_CROPS_ROOT", str(data_dir / "crops"))),
        Path(os.getenv("SCENE_VIDEO_DERIVATIVES_ROOT", str(data_dir / "video_derivatives"))),
        Path(os.getenv("SCENE_VIDEO_STORYBOARD_ROOT", str(data_dir / "video_storyboard"))),
    ])
    originals = [
        Path(value).expanduser().resolve()
        for value in os.getenv("SCENE_ORIGINALS_ROOTS", "").split(",")
        if value.strip()
    ]
    for root in derived_roots:
        if root == Path(root.anchor) or root in originals:
            print(f"refusing unsafe root: {root}", file=sys.stderr)
            return 2

    report = {
        "dry_run": bool(args.dry_run),
        "domain_tables": list(DOMAIN_TABLES),
        "reference_tables": list(REFERENCE_TABLES),
        "counts": {},
        "derived_files": {},
        "deleted_files": 0,
        "deleted_bytes": 0,
        "backup": False,
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            existing = _existing_tables(cur)
            report["counts"] = _counts(cur)
            active = _active_jobs(cur)

    if args.dry_run:
        for root in derived_roots:
            files, size = _remove_tree(root)
            report["derived_files"][str(root)] = {"files": files, "bytes": size}
        _print(report, args.json)
        return 0

    if args.confirm != "RESET":
        print("refusing; pass --confirm RESET", file=sys.stderr)
        return 2
    if active:
        print(
            f"refusing: {active} active jobs; stop workers and let them finish",
            file=sys.stderr,
        )
        return 2
    if not args.no_backup:
        try:
            _backup()
            report["backup"] = True
        except subprocess.CalledProcessError:
            print("backup failed; reset aborted", file=sys.stderr)
            return 1

    for root in derived_roots:
        files, size = _remove_tree(root)
        if not args.no_files:
            _clear_tree(root)
            report["deleted_files"] += files
            report["deleted_bytes"] += size
        report["derived_files"][str(root)] = {"files": files, "bytes": size}

    tables = [table for table in DOMAIN_TABLES if table in existing]

    with get_connection() as conn:
        with conn.cursor() as cur:
            if tables:
                cur.execute(
                    "TRUNCATE TABLE "
                    + ", ".join(f"public.{table}" for table in tables)
                    + " RESTART IDENTITY CASCADE"
                )
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("VACUUM (ANALYZE)")

    _print(report, args.json)
    return 0


def _print(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return
    print("domain:", ", ".join(report["domain_tables"]))
    print("reference kept:", ", ".join(report["reference_tables"]))
    print("counts:", report["counts"])
    print(
        "derived files:",
        report["deleted_files"],
        "removed,",
        report["deleted_bytes"],
        "bytes; backup:",
        report["backup"],
    )
    for root, item in report["derived_files"].items():
        print(f"  {root}: {item['files']} files / {item['bytes']} bytes")


if __name__ == "__main__":
    raise SystemExit(main())
