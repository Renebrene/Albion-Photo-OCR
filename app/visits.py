"""
Посещения: учёт входов и выходов пользователей (schema/033).

Одна строка на событие; имя хранится снимком, поэтому список посещений
переживает переименование или архивацию пользователя. Это лёгкая операция и
не должна ломать вход, если запись не удалась — вызывающий код глушит ошибку.
"""

from __future__ import annotations

from app.ingest.database import get_connection


def record_visit(
    *,
    user_id: int | None,
    user_name: str,
    event: str = "login",
) -> None:
    """Записать событие входа/выхода; event ∈ {login, logout}."""

    if event not in ("login", "logout"):
        raise ValueError("event must be 'login' or 'logout'")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.user_visits (user_id, user_name, event)
                VALUES (%s, %s, %s)
                """,
                (user_id, str(user_name)[:200], event),
            )


def list_visits(*, limit: int = 100) -> list[dict]:
    """Последние посещения (по убыванию времени)."""

    limit = max(1, min(int(limit), 500))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT visit_id, user_id, user_name, event, created_at
                FROM public.user_visits
                ORDER BY visit_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "visit_id": int(row[0]),
            "user_id": int(row[1]) if row[1] is not None else None,
            "user_name": row[2],
            "event": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]
