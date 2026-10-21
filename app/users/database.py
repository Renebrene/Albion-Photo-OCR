"""
Users and server-side sessions (public.users / public.sessions).

Passwords are hashed with app.users.security; session ids are opaque random
tokens stored in PostgreSQL.
"""

from __future__ import annotations

import secrets

from app.ingest.database import get_connection
from app.users.security import hash_password

_USER_COLUMNS = (
    "user_id, name, color, role, active, password_hash, created_at"
)

DEFAULT_SESSION_TTL_HOURS = 24 * 7


def _row_to_user(row, *, include_hash: bool = False) -> dict:
    user = {
        "user_id": int(row[0]),
        "name": row[1],
        "color": row[2],
        "role": row[3],
        "active": bool(row[4]),
        "created_at": row[6],
    }

    if include_hash:
        user["password_hash"] = row[5]

    return user


def list_users(*, active_only: bool = False) -> list[dict]:
    sql = f"SELECT {_USER_COLUMNS} FROM public.users"  # noqa: S608
    if active_only:
        sql += " WHERE active"
    sql += " ORDER BY lower(name)"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [_row_to_user(row) for row in cur.fetchall()]


def get_user(user_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_USER_COLUMNS} FROM public.users WHERE user_id = %s",  # noqa: S608
                (user_id,),
            )
            row = cur.fetchone()

    return _row_to_user(row) if row is not None else None


def get_user_by_name(name: str) -> dict | None:
    """Internal: includes password_hash for authentication."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Логин без учёта регистра: «гость» и «Гость» — один аккаунт.
            # Точное совпадение имени всё равно выигрывает, если вдруг
            # существуют два написания.
            cur.execute(
                f"SELECT {_USER_COLUMNS} FROM public.users "  # noqa: S608
                "WHERE LOWER(name) = LOWER(%s) "
                "ORDER BY (name = %s) DESC, user_id LIMIT 1",
                (name, name),
            )
            row = cur.fetchone()

    return _row_to_user(row, include_hash=True) if row is not None else None


# The two seeded accounts (schema/010). They must keep working - one
# administers the installation, the other is the shared read-only login - so
# neither may be archived, whatever else is edited.
BUILTIN_USER_NAMES = frozenset({"администратор", "гость"})


def is_builtin_user(user: dict) -> bool:
    """True for the seeded accounts, which cannot be archived."""

    return (user.get("name") or "").strip().casefold() in BUILTIN_USER_NAMES


def create_user(
    *,
    name: str,
    role: str = "Менеджер",
    color: str | None = None,
    password: str | None = None,
) -> dict:
    password_hash = hash_password(password) if password else None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.users (name, role, color, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id
                """,
                (name, role, color, password_hash),
            )
            user_id = int(cur.fetchone()[0])

    return get_user(user_id)


def update_user(
    user_id: int,
    *,
    name: str | None = None,
    color: str | None = None,
    role: str | None = None,
    active: bool | None = None,
) -> dict | None:
    sets: list[str] = []
    params: list[object] = []

    if name is not None:
        sets.append("name = %s")
        params.append(name)
    if color is not None:
        sets.append("color = %s")
        params.append(color)
    if role is not None:
        sets.append("role = %s")
        params.append(role)
    if active is not None:
        sets.append("active = %s")
        params.append(active)

    if not sets:
        return get_user(user_id)

    params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE public.users SET {', '.join(sets)} "  # noqa: S608
                "WHERE user_id = %s",
                params,
            )

    return get_user(user_id)


def set_password(user_id: int, password: str | None) -> None:
    password_hash = hash_password(password) if password else None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.users SET password_hash = %s WHERE user_id = %s",
                (password_hash, user_id),
            )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def create_session(
    user_id: int,
    *,
    ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
) -> str:
    session_id = secrets.token_urlsafe(32)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.sessions (session_id, user_id, expires_at)
                VALUES (
                    %s, %s,
                    CURRENT_TIMESTAMP + (%s || ' hours')::interval
                )
                """,
                (session_id, user_id, str(int(ttl_hours))),
            )

    return session_id


def get_session(session_id: str) -> dict | None:
    """Return the active user for a session, or None when invalid/expired."""

    if not session_id:
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.user_id, u.name, u.color, u.role, u.active,
                       u.password_hash, u.created_at
                FROM public.sessions AS s
                JOIN public.users AS u ON u.user_id = s.user_id
                WHERE s.session_id = %s
                  AND s.expires_at > CURRENT_TIMESTAMP
                  AND u.active
                """,
                (session_id,),
            )
            row = cur.fetchone()

    return _row_to_user(row) if row is not None else None


def delete_session(session_id: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.sessions WHERE session_id = %s",
                (session_id,),
            )
            return cur.rowcount == 1


def delete_user_sessions(user_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.sessions WHERE user_id = %s",
                (user_id,),
            )
