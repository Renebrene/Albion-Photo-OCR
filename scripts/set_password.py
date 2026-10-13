#!/usr/bin/env python
"""
Set a user's password (fail-closed bootstrap and recovery).

Login requires a password: seeded users have none, so an administrator must
set one before the first login.

Usage:
    python scripts/set_password.py <username>

The database credentials come from the environment (INGEST_DB_*). When
INGEST_DB_PASSWORD is not set, the script loads the documented service env
file (~/.config/scene-fingerprint.env) if it exists, so it works out of the
box on a machine deployed with scripts/systemd units.

The password is read interactively (twice) and never echoed. For automation
use --password-stdin, e.g.:
    printf '%s' "$PW" | python scripts/set_password.py admin --password-stdin
"""

from __future__ import annotations

import argparse
import getpass
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


def _read_password(args) -> str:
    if args.password_stdin:
        password = sys.stdin.read().strip()

        if not password:
            raise SystemExit("empty password on stdin")

        return password

    password = getpass.getpass("New password: ")

    if not password:
        raise SystemExit("password must not be empty")

    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("passwords do not match")

    return password


def main() -> int:
    parser = argparse.ArgumentParser(description="Set a PhotoBAse user password")
    parser.add_argument("username", help="existing user name")
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="read the password from stdin instead of prompting",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=f"env file to fall back to (default: {DEFAULT_ENV_FILE})",
    )
    args = parser.parse_args()

    if not os.getenv("INGEST_DB_PASSWORD"):
        loaded = load_env_file(args.env_file)

        if loaded:
            print(f"loaded DB settings from {args.env_file}")

    if not os.getenv("INGEST_DB_PASSWORD"):
        print(
            "error: INGEST_DB_PASSWORD is not set.\n"
            "  export it, or make sure the deployment env file exists:\n"
            f"    set -a; . {args.env_file}; set +a",
            file=sys.stderr,
        )
        return 2

    from app.users import database as users_db

    user = users_db.get_user_by_name(args.username)

    if user is None:
        names = ", ".join(
            item["name"] for item in users_db.list_users(active_only=False)
        )
        print(
            f"error: user not found: {args.username}\n"
            f"available users: {names or '(none)'}",
            file=sys.stderr,
        )
        return 1

    password = _read_password(args)
    users_db.set_password(user["user_id"], password)

    # Invalidate existing sessions after a password change.
    users_db.delete_user_sessions(user["user_id"])

    print(f"password set for user '{args.username}' (user_id={user['user_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
