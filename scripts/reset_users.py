"""
Reset the built-in accounts and set their passwords.

    set -a && . ~/.config/scene-fingerprint.env && set +a
    python scripts/reset_users.py --password альбион

«Администратор» and «Гость» are the seeded accounts (schema/010). This makes
sure both exist, are active and carry the given password - the recovery path
when a password is forgotten, which is otherwise settable only through the web
window. Their sessions are dropped, so they log in again with the new password.

Other users are listed but never touched; --archive-others sends the active
ones to the archive (nothing is deleted).
"""

from __future__ import annotations

import argparse
import sys

from app.users import database as users_db

# name -> role of the accounts the installation always keeps.
SEEDED = (
    ("Администратор", "Администратор"),
    ("Гость", "Гость"),
)

SEEDED_KEYS = {name.casefold() for name, _role in SEEDED}


def _find(name: str) -> dict | None:
    wanted = name.strip().casefold()

    for user in users_db.list_users(active_only=False):
        if (user.get("name") or "").strip().casefold() == wanted:
            return user

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="reset the built-in users")
    parser.add_argument(
        "--password",
        required=True,
        help="password to set for both accounts",
    )
    parser.add_argument(
        "--archive-others",
        action="store_true",
        help="archive every other active user (nothing is deleted)",
    )
    args = parser.parse_args()

    for name, role in SEEDED:
        user = _find(name)

        if user is None:
            user = users_db.create_user(
                name=name,
                role=role,
                password=args.password,
            )
            print(f"{name}: создан ({role})")
        else:
            users_db.update_user(user["user_id"], active=True, role=role)
            users_db.set_password(user["user_id"], args.password)
            users_db.delete_user_sessions(user["user_id"])
            print(f"{name}: активен, роль {role}, пароль обновлён")

    others = [
        user
        for user in users_db.list_users(active_only=False)
        if (user.get("name") or "").strip().casefold() not in SEEDED_KEYS
    ]

    if not others:
        print("других пользователей нет")
        return 0

    print(f"\nдругие пользователи ({len(others)}):")

    for user in others:
        state = "активен" if user["active"] else "в архиве"

        if args.archive_others and user["active"]:
            users_db.update_user(user["user_id"], active=False)
            users_db.delete_user_sessions(user["user_id"])
            state = "отправлен в архив"

        print(f"  {user['name']} ({user['role']}): {state}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
