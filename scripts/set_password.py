#!/usr/bin/env python
"""
Set a user's password (fail-closed bootstrap and recovery).

Login requires a password: seeded users have none, so an administrator must
set one before the first login.

Usage:
    INGEST_DB_PASSWORD=... python scripts/set_password.py <username>

The password is read interactively (twice) and never echoed. For automation
use --password-stdin, e.g.:
    printf '%s' "$PW" | python scripts/set_password.py admin --password-stdin
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

# Allow running the script directly from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.users import database as users_db  # noqa: E402


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
    args = parser.parse_args()

    user = users_db.get_user_by_name(args.username)

    if user is None:
        print(f"error: user not found: {args.username}", file=sys.stderr)
        return 1

    password = _read_password(args)
    users_db.set_password(user["user_id"], password)

    # Invalidate existing sessions after a password change.
    users_db.delete_user_sessions(user["user_id"])

    print(f"password set for user '{args.username}' (user_id={user['user_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
