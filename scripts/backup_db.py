"""Create a verified PostgreSQL backup with generation-based retention.

The backup is a custom-format pg_dump (restorable with pg_restore). It is
written to a temporary file, verified with `pg_restore --list`, hashed and only
then atomically published. A JSON manifest records the database name, size,
timestamp and dump version.

Retention keeps:
  * the newest --keep-daily dumps (default 14),
  * the newest dump of each ISO week (--keep-weekly, default 8),
  * the newest dump of each month (--keep-monthly, default 6).
Nothing is deleted unless it is older than the union of those sets.

Examples:
    .venv/bin/python scripts/backup_db.py --dry-run
    .venv/bin/python scripts/backup_db.py
    .venv/bin/python scripts/backup_db.py --keep-daily 7 --keep-weekly 4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

DEFAULT_DIR = Path(
    os.getenv(
        "SCENE_BACKUP_DIR",
        str(Path.home() / "albion-photobase-backups"),
    )
)


def _db_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PGHOST", env.get("INGEST_DB_HOST", "localhost"))
    env.setdefault("PGPORT", env.get("INGEST_DB_PORT", "5432"))
    env.setdefault("PGUSER", env.get("INGEST_DB_USER", "lora_ingest"))
    env.setdefault("PGDATABASE", env.get("INGEST_DB_NAME", "photobase_ingest_test"))
    if env.get("INGEST_DB_PASSWORD") and not env.get("PGPASSWORD"):
        env["PGPASSWORD"] = env["INGEST_DB_PASSWORD"]
    return env


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], env: dict[str, str]) -> None:
    subprocess.run(command, env=env, check=True)


def _backup_paths(directory: Path, dbname: str) -> list[Path]:
    return sorted(directory.glob(f"{dbname}_*.dump"))


def select_retention(
    paths: list[Path],
    *,
    keep_daily: int,
    keep_weekly: int,
    keep_monthly: int,
) -> tuple[list[Path], list[Path]]:
    """Return (keep, delete) for a list of backup paths.

    The file name must contain YYYYMMDD_HHMMSS. The newest dump is always kept.
    """

    dated = []
    for path in paths:
        try:
            stamp = path.name.split("_")[-2] + "_" + path.name.split("_")[-1].split(".")[0]
            moment = datetime.strptime(stamp, "%Y%m%d_%H%M%S")
        except (IndexError, ValueError):
            continue
        dated.append((moment, path))

    dated.sort(reverse=True)
    keep: set[Path] = set()
    seen_days: set[str] = set()
    seen_weeks: set[str] = set()
    seen_months: set[str] = set()

    for moment, path in dated:
        day = moment.strftime("%Y-%m-%d")
        week = f"{moment.isocalendar().year}-{moment.isocalendar().week:02d}"
        month = moment.strftime("%Y-%m")

        if len(seen_days) < keep_daily and day not in seen_days:
            seen_days.add(day)
            keep.add(path)
        if len(seen_weeks) < keep_weekly and week not in seen_weeks:
            seen_weeks.add(week)
            keep.add(path)
        if len(seen_months) < keep_monthly and month not in seen_months:
            seen_months.add(month)
            keep.add(path)

    if dated and not keep:
        keep.add(dated[0][1])

    delete = [path for _, path in dated if path not in keep]
    return sorted(keep), sorted(delete)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--keep-daily", type=int, default=14)
    parser.add_argument("--keep-weekly", type=int, default=8)
    parser.add_argument("--keep-monthly", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    for name, value in (("daily", args.keep_daily), ("weekly", args.keep_weekly),
                        ("monthly", args.keep_monthly)):
        if value < 0:
            print(f"--keep-{name} must be >= 0", file=sys.stderr)
            return 2

    env = _db_env()
    dbname = env["PGDATABASE"]
    directory = args.out_dir.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)

    existing = _backup_paths(directory, dbname)
    keep, delete = select_retention(
        existing,
        keep_daily=args.keep_daily,
        keep_weekly=args.keep_weekly,
        keep_monthly=args.keep_monthly,
    )

    report = {
        "dry_run": args.dry_run,
        "database": dbname,
        "directory": str(directory),
        "created": None,
        "size": None,
        "sha256": None,
        "kept": len(keep),
        "deleted": 0,
        "candidates": [path.name for path in delete],
    }

    if args.dry_run:
        report["would_delete"] = [path.name for path in delete]
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0

    stamp = _timestamp()
    target = directory / f"{dbname}_{stamp}.dump"
    temp = directory / f".{target.name}.tmp"

    try:
        _run(
            [
                "pg_dump",
                "-Fc",
                "--no-owner",
                "--no-privileges",
                "-f",
                str(temp),
            ],
            env,
        )
        _run(["pg_restore", "--list", str(temp)], env)

        digest = _sha256(temp)
        os.replace(temp, target)
        target.with_suffix(target.suffix + ".sha256").write_text(digest + "\n")
        manifest = {
            "database": dbname,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file": target.name,
            "size": target.stat().st_size,
            "sha256": digest,
            "pg_dump": "custom",
        }
        target.with_suffix(target.suffix + ".json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        )
        report.update(
            created=target.name,
            size=target.stat().st_size,
            sha256=digest,
        )
    except Exception as exc:
        temp.unlink(missing_ok=True)
        print(f"backup failed: {exc}", file=sys.stderr)
        return 1

    for path in delete:
        try:
            path.unlink(missing_ok=True)
            path.with_suffix(path.suffix + ".sha256").unlink(missing_ok=True)
            path.with_suffix(path.suffix + ".json").unlink(missing_ok=True)
            report["deleted"] += 1
        except OSError as exc:
            print(f"could not remove {path.name}: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"backup: {target} ({report['size']} bytes) · "
            f"kept: {report['kept']} · deleted: {report['deleted']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
