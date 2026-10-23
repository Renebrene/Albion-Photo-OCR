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
    "created_at, finished_at, prompt_tokens, completion_tokens, total_tokens"
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
        "prompt_tokens": row[14],
        "completion_tokens": row[15],
        "total_tokens": row[16],
    }


def token_usage(raw: dict | None) -> tuple[int | None, int | None, int | None]:
    """
    Расход токенов из ответа провайдера, если он его сообщает.

    Облако отдаёт OpenAI-совместимый `usage`; локальная Ollama счётчиков не
    возвращает, поэтому там остаются NULL.
    """

    if not isinstance(raw, dict):
        return (None, None, None)

    usage = raw.get("usage")

    if not isinstance(usage, dict):
        return (None, None, None)

    def number(key: str) -> int | None:
        value = usage.get(key)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    return (
        number("prompt_tokens"),
        number("completion_tokens"),
        number("total_tokens"),
    )


def _archive_previous(cur, photo_id: str, replaced_by_model: str) -> None:
    """
    Сложить прежний результат в историю перед перезаписью.

    Владелец выбрал «полная перезапись + история версий»: смена модели не
    должна стирать то, что было, чтобы результаты можно было сравнить и
    вернуть.
    """

    cur.execute(
        """
        INSERT INTO public.photo_qwen_history (
            photo_id, status, description, address, client, brand, category,
            tags, raw, qwen_model, qwen_time_sec, error_message,
            prompt_tokens, completion_tokens, total_tokens, finished_at,
            replaced_by_model
        )
        SELECT
            photo_id, status, description, address, client, brand, category,
            tags, raw, qwen_model, qwen_time_sec, error_message,
            prompt_tokens, completion_tokens, total_tokens, finished_at,
            %s
        FROM public.photo_qwen
        WHERE photo_id = %s
          AND (
              COALESCE(description, '') <> ''
              OR COALESCE(client, '') <> ''
              OR COALESCE(brand, '') <> ''
              OR COALESCE(category, '') <> ''
          )
        """,
        (replaced_by_model, photo_id),
    )


def list_history(photo_id: str, *, limit: int = 20) -> list[dict]:
    """Прежние результаты распознавания этого фото, новые сверху."""

    limit = max(1, min(int(limit), 100))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT history_id, status, description, client, brand,
                       category, tags, qwen_model, qwen_time_sec,
                       error_message, total_tokens, finished_at, replaced_at,
                       replaced_by_model
                FROM public.photo_qwen_history
                WHERE photo_id = %s
                ORDER BY history_id DESC
                LIMIT %s
                """,
                (photo_id, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "history_id": int(row[0]),
            "status": row[1],
            "description": row[2],
            "client": row[3],
            "brand": row[4],
            "category": row[5],
            "tags": row[6],
            "qwen_model": row[7],
            "qwen_time_sec": row[8],
            "error_message": row[9],
            "total_tokens": row[10],
            "finished_at": row[11],
            "replaced_at": row[12],
            "replaced_by_model": row[13],
        }
        for row in rows
    ]


def list_global_history(*, limit: int = 200) -> list[dict]:
    """Recent QWEN versions across all photos, newest first."""
    limit = max(1, min(int(limit), 1000))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT h.history_id, h.photo_id, p.filename, h.status,
                       h.description, h.client, h.brand, h.category, h.tags,
                       h.qwen_model, h.total_tokens, h.replaced_at,
                       h.replaced_by_model
                FROM public.photo_qwen_history AS h
                LEFT JOIN public.photos AS p ON p.photo_id = h.photo_id
                ORDER BY h.history_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "history_id": int(row[0]),
            "photo_id": row[1],
            "filename": row[2],
            "status": row[3],
            "description": row[4],
            "client": row[5],
            "brand": row[6],
            "category": row[7],
            "tags": row[8],
            "qwen_model": row[9],
            "total_tokens": row[10],
            "replaced_at": row[11],
            "replaced_by_model": row[12],
        }
        for row in rows
    ]


def photo_ids_in_period(
    *, date_from, date_to, date_mode: str = "upload"
) -> list[str]:
    """Registered photo ids whose upload or capture date is in [from, to]."""
    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be upload or capture")
    date_column = "taken_at" if date_mode == "capture" else "created_at"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT photo_id FROM public.photos "
                f"WHERE {date_column} >= %s::date "
                f"AND {date_column} < (%s::date + interval '1 day') "
                f"ORDER BY photo_id",  # noqa: S608 - date_column is allowlisted above
                (date_from, date_to),
            )
            return [str(row[0]) for row in cur.fetchall()]


def photo_ids_missing_in_period(
    *,
    date_from,
    date_to,
    date_mode: str = "capture",
    limit: int = 1000,
) -> list[str]:
    """
    Photo ids in [from, to] that have no successful QWEN row yet.

    Non-destructive: existing descriptions are never touched. Used after a
    pipeline run that skipped QWEN, and for a targeted catch-up scan.
    """

    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be upload or capture")

    date_column = "p.taken_at" if date_mode == "capture" else "p.created_at"
    limit = max(1, min(int(limit), 5000))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT p.photo_id
                FROM public.photos AS p
                WHERE {date_column} >= %s::date
                  AND {date_column} < (%s::date + interval '1 day')
                  AND NOT EXISTS (
                      SELECT 1 FROM public.photo_qwen AS q
                      WHERE q.photo_id = p.photo_id
                        AND q.status = 'DONE'
                  )
                ORDER BY p.photo_id
                LIMIT %s
                """,  # noqa: S608 - date_column is allowlisted above
                (date_from, date_to, limit),
            )
            return [str(row[0]) for row in cur.fetchall()]


def archive_and_clear(photo_ids: list[str], *, replaced_by_model: str) -> int:
    """Copy current QWEN rows to history, then delete them in one transaction."""
    if not photo_ids:
        return 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photo_qwen_history (
                    photo_id, status, description, address, client, brand,
                    category, tags, raw, qwen_model, qwen_time_sec,
                    error_message, prompt_tokens, completion_tokens,
                    total_tokens, finished_at, replaced_by_model
                )
                SELECT photo_id, status, description, address, client, brand,
                       category, tags, raw, qwen_model, qwen_time_sec,
                       error_message, prompt_tokens, completion_tokens,
                       total_tokens, finished_at, %s
                FROM public.photo_qwen
                WHERE photo_id = ANY(%s)
                """,
                (replaced_by_model, photo_ids),
            )
            archived = cur.rowcount
            cur.execute(
                "DELETE FROM public.photo_qwen WHERE photo_id = ANY(%s)",
                (photo_ids,),
            )
            return int(archived or 0)


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
    prompt_tokens, completion_tokens, total_tokens = token_usage(raw)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Полная перезапись — но прежний результат остаётся в истории.
            _archive_previous(cur, photo_id, model)

            cur.execute(
                """
                INSERT INTO public.photo_qwen (
                    photo_id, status, description, address, client,
                    brand, category, tags, raw, qwen_model,
                    qwen_time_sec, finished_at,
                    prompt_tokens, completion_tokens, total_tokens
                )
                VALUES (
                    %s, 'DONE', %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP, %s, %s, %s
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
                    finished_at = CURRENT_TIMESTAMP,
                    prompt_tokens = EXCLUDED.prompt_tokens,
                    completion_tokens = EXCLUDED.completion_tokens,
                    total_tokens = EXCLUDED.total_tokens
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
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                ),
            )


MANUAL_MODEL = "manual-edit"


def save_manual(
    photo_id: str,
    *,
    fields: dict[str, Any],
) -> None:
    """
    Persist a hand-edited description from the photo card.

    The previous result goes to the history (same contract as a re-run); the
    row is marked with qwen_model="manual-edit" so the UI can show it.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            _archive_previous(cur, photo_id, MANUAL_MODEL)

            cur.execute(
                """
                INSERT INTO public.photo_qwen (
                    photo_id, status, description, address, client,
                    brand, category, tags, raw, qwen_model,
                    qwen_time_sec, finished_at, error_message,
                    prompt_tokens, completion_tokens, total_tokens
                )
                VALUES (
                    %s, 'DONE', %s, %s, %s, %s, %s, %s, %s, %s,
                    0, CURRENT_TIMESTAMP, NULL, NULL, NULL, NULL
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
                    qwen_time_sec = 0,
                    error_message = NULL,
                    finished_at = CURRENT_TIMESTAMP,
                    prompt_tokens = NULL,
                    completion_tokens = NULL,
                    total_tokens = NULL
                """,
                (
                    photo_id,
                    fields.get("description"),
                    fields.get("address"),
                    fields.get("client"),
                    fields.get("brand"),
                    fields.get("category"),
                    Json(fields.get("tags") or []),
                    Json({"manual": True}),
                    MANUAL_MODEL,
                ),
            )


def apply_refined_values(
    photo_id: str,
    changes: dict[str, str],
    *,
    reason: str = "refine",
) -> bool:
    """
    Обновить отдельные поля описания после этапа «Уточнение».

    Прежняя строка уходит в историю (`photo_qwen_history`) с пометкой причины,
    поэтому результат обратим и виден в истории распознавания фото. Меняются
    только переданные поля; описание, теги и токены не трогаются.

    Возвращает True, если строка действительно обновлена.
    """

    fields = {
        key: value
        for key, value in changes.items()
        if key in {"client", "brand"} and value
    }

    if not fields:
        return False

    with get_connection() as conn:
        with conn.cursor() as cur:
            _archive_previous(cur, photo_id, reason)

            assignments = ", ".join(f"{key} = %s" for key in fields)
            params = list(fields.values()) + [photo_id]

            cur.execute(
                f"UPDATE public.photo_qwen SET {assignments} "  # noqa: S608 - ключи из фиксированного набора
                "WHERE photo_id = %s AND status = 'DONE'",
                params,
            )

            return cur.rowcount == 1


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
