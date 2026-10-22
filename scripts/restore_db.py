"""Restore a custom-format pg_dump into an explicitly named database.

Safety rules:
  * the target database must be named explicitly;
  * restoring into the currently configured production database requires
    `--allow-production` as well as `--confirm`;
  * the .sha256 file next to the backup is verified when present;
  * `--dry-run` prints the command and changes nothing.

The target database must already exist and be empty/disposable. This script
does not create databases: creating a role/database needs superuser rights.

Example (restore drill):
    .venv/bin/python scripts/restore_db.py \\
        --backup ~/scene-fingerprint-backups/photobase_20261022_023000.dump \\
        --target-db photobase_restore_test --confirm
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

DB_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PGHOST", env.get("INGEST_DB_HOST", "localhost"))
    env.setdefault("PGPORT", env.get("INGEST_DB_PORT", "5432"))
    env.setdefault("PGUSER", env.get("INGEST_DB_USER", "lora_ingest"))
    if env.get("INGEST_DB_PASSWORD") and not env.get("PGPASSWORD"):
        env["PGPASSWORD"] = env["INGEST_DB_PASSWORD"]
    return env


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--target-db", required=True)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--allow-production", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args(argv)

    if not DB_NAME_RE.fullmatch(args.target_db):
        print("target database name is not allowed", file=sys.stderr)
        return 2

    backup = args.backup.expanduser().resolve()
    if not backup.is_file():
        print(f"backup not found: {backup}", file=sys.stderr)
        return 2

    sidecar = backup.with_suffix(backup.suffix + ".sha256")
    if sidecar.is_file():
        expected = sidecar.read_text().strip().split()[0]
        actual = _sha256(backup)
        if expected != actual:
            print("backup checksum mismatch", file=sys.stderr)
            return 2

    env = _env()
    production = env.get("INGEST_DB_NAME") or env.get("PGDATABASE")
    if production and args.target_db == production and not args.allow_production:
        print(
            "refusing to restore into the configured production database; "
            "use --allow-production after a verified backup",
            file=sys.stderr,
        )
        return 2

    command = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        f"--jobs={max(1, int(args.jobs))}",
        "--dbname",
        args.target_db,
        str(backup),
    ]

    if args.dry_run:
        print(" ".join(command))
        return 0

    if not args.confirm:
        print(
            "restore is destructive for the target database; pass --confirm",
            file=sys.stderr,
        )
        return 2

    try:
        subprocess.run(command, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"restore failed: {exc}", file=sys.stderr)
        return 1

    print(f"restored {backup.name} into {args.target_db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
