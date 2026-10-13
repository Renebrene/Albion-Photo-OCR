#!/usr/bin/env python
"""
Schema migration runner (versioned, checksum-guarded).

Applies schema/001..NNN.sql in order, recording each file in
public.schema_migrations so a migration runs exactly once. Existing databases
created by db_bootstrap.sh adopt the current schema with --baseline.

Usage:
    INGEST_DB_PASSWORD=... python scripts/migrate.py --status
    INGEST_DB_PASSWORD=... python scripts/migrate.py            # apply pending
    INGEST_DB_PASSWORD=... python scripts/migrate.py --baseline # adopt existing

000_bootstrap.sql is intentionally excluded: it creates the role/database and
must be run once as a superuser (see scripts/db_bootstrap.sh).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.ingest.database import get_connection  # noqa: E402

SCHEMA_DIR = REPO_ROOT / "schema"
# 000 is the superuser bootstrap step (role + database), not a migration.
SKIP_PREFIXES = ("000_",)


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    checksum: str


def discover_migrations(schema_dir: Path = SCHEMA_DIR) -> list[Migration]:
    """Return migration files in version order (excluding bootstrap)."""

    migrations = []

    for path in sorted(schema_dir.glob("*.sql")):
        if path.name.startswith(SKIP_PREFIXES):
            continue

        migrations.append(
            Migration(
                version=path.stem,
                path=path,
                checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )

    return migrations


def plan(applied: dict[str, str], migrations: list[Migration]):
    """Split migrations into pending ones and checksum drift."""

    pending = [m for m in migrations if m.version not in applied]
    drift = [
        m
        for m in migrations
        if m.version in applied and applied[m.version] != m.checksum
    ]

    return pending, drift


def _ensure_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.schema_migrations (
            version    TEXT PRIMARY KEY,
            checksum   TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _applied(cur) -> dict[str, str]:
    cur.execute("SELECT version, checksum FROM public.schema_migrations")
    return {str(row[0]): str(row[1]) for row in cur.fetchall()}


def _record(cur, migration: Migration) -> None:
    cur.execute(
        """
        INSERT INTO public.schema_migrations (version, checksum)
        VALUES (%s, %s)
        ON CONFLICT (version) DO UPDATE SET checksum = EXCLUDED.checksum
        """,
        (migration.version, migration.checksum),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply PhotoBAse migrations")
    parser.add_argument(
        "--status",
        action="store_true",
        help="only show applied/pending migrations",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="record all current migrations as applied WITHOUT running them "
        "(adopt an existing database)",
    )
    args = parser.parse_args()

    migrations = discover_migrations()

    with get_connection() as conn:
        with conn.cursor() as cur:
            _ensure_table(cur)
            applied = _applied(cur)
            pending, drift = plan(applied, migrations)

            if drift:
                print("ERROR: checksum mismatch for already-applied migrations:")
                for migration in drift:
                    print(f"  - {migration.version}")
                print("Refusing to continue; the file changed after being applied.")
                return 2

            if args.status:
                for migration in migrations:
                    mark = "applied" if migration.version in applied else "pending"
                    print(f"  [{mark}] {migration.version}")
                print(
                    f"{len(applied)} applied, {len(pending)} pending"
                )
                return 0

            if args.baseline:
                for migration in pending:
                    _record(cur, migration)
                    print(f"  baselined {migration.version}")
                print(f"baseline recorded for {len(pending)} migration(s)")
                return 0

            if not pending:
                print("nothing to apply (schema up to date)")
                return 0

            for migration in pending:
                print(f"  applying {migration.version}")
                cur.execute(migration.path.read_text(encoding="utf-8"))
                _record(cur, migration)

            print(f"applied {len(pending)} migration(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
