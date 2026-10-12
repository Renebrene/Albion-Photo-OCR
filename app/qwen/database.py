"""
PostgreSQL access for QWEN metadata (public.photo_qwen).

Independent from DINO/HYBRID; only writes textual metadata rows.
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Json

from app.ingest.database import get_connection

_COLUMNS = (
    "photo_id, status, description, address, client, brand, category, "
    "tags, raw, qwen_model, qwen_time_sec, error_message, "
    "created_at, finished_at"
)


def _row_to_dict(row) -> dict:
    return {
        "photo_id": row[0],
        "status": row[1],
        "description": row[2],
        "address": row[3],
        "client": row[4],
        "brand": row[5],
        "category": row[6],
        "tags": row[7],
        "raw": row[8],
        "qwen_model": row[9],
        "qwen_time_sec": row[10],
        "error_message": row[11],
        "created_at": row[12],
        "finished_at": row[13],
    }


def get_photo_source(photo_id: str) -> str | None:
    """Return the registered source_path for one photo, or None."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_path FROM public.photos WHERE photo_id = %s",
                (photo_id,),
            )
            row = cur.fetchone()

    return row[0] if row is not None else None


def mark_running(photo_id: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photo_qwen (photo_id, status)
                VALUES (%s, 'RUNNING')
                ON CONFLICT (photo_id)
                DO UPDATE SET
                    status = 'RUNNING',
                    error_message = NULL,
                    finished_at = NULL
                """,
                (photo_id,),
            )


def save_success(
    photo_id: str,
    *,
    fields: dict[str, Any],
    raw: dict[str, Any],
    model: str,
    time_sec: float,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photo_qwen (
                    photo_id, status, description, address, client,
                    brand, category, tags, raw, qwen_model,
                    qwen_time_sec, finished_at
                )
                VALUES (
                    %s, 'DONE', %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (photo_id)
                DO UPDATE SET
                    status = 'DONE',
                    description = EXCLUDED.description,
                    address = EXCLUDED.address,
                    client = EXCLUDED.client,
                    brand = EXCLUDED.brand,
                    category = EXCLUDED.category,
                    tags = EXCLUDED.tags,
                    raw = EXCLUDED.raw,
                    qwen_model = EXCLUDED.qwen_model,
                    qwen_time_sec = EXCLUDED.qwen_time_sec,
                    error_message = NULL,
                    finished_at = CURRENT_TIMESTAMP
                """,
                (
                    photo_id,
                    fields.get("description"),
                    fields.get("address"),
                    fields.get("client"),
                    fields.get("brand"),
                    fields.get("category"),
                    Json(fields.get("tags") or []),
                    Json(raw),
                    model,
                    float(time_sec),
                ),
            )


def save_failure(photo_id: str, error_message: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photo_qwen (
                    photo_id, status, error_message, finished_at
                )
                VALUES (%s, 'FAILED', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (photo_id)
                DO UPDATE SET
                    status = 'FAILED',
                    error_message = EXCLUDED.error_message,
                    finished_at = CURRENT_TIMESTAMP
                """,
                (photo_id, str(error_message)),
            )


def get(photo_id: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM public.photo_qwen WHERE photo_id = %s",  # noqa: S608
                (photo_id,),
            )
            row = cur.fetchone()

    return _row_to_dict(row) if row is not None else None
