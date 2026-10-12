"""
Small key/value settings store backed by public.app_settings.

Values are JSON. Environment variables remain the fallback defaults; a value
written here overrides them at runtime (for example the QWEN model name).
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Json

from app.ingest.database import get_connection


def get(key: str, default: Any = None) -> Any:
    """Return the stored value for *key*, or *default* when unset."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT value FROM public.app_settings WHERE key = %s",
                (key,),
            )
            row = cur.fetchone()

    return row[0] if row is not None else default


def set_value(key: str, value: Any) -> None:
    """Insert or update one setting."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.app_settings (key, value, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, Json(value)),
            )
