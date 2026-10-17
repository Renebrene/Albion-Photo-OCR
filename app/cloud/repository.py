"""Persistence for user-visible Albion links and their source media."""

from __future__ import annotations

from typing import Any

from app.api import repository as photo_repository
from app.api import video_repository
from app.ingest.database import get_connection

_COLUMNS = (
    "link_id, owner_user_id, owner_name, media_kind, media_id, provider, "
    "status, url, object_key, error_message, job_id, created_at, finished_at, "
    "expires_at"
)


def _row(row) -> dict:
    return {
        "link_id": int(row[0]),
        "owner_user_id": row[1],
        "owner_name": row[2],
        "media_kind": row[3],
        "media_id": row[4],
        "provider": row[5],
        "status": row[6],
        "url": row[7],
        "object_key": row[8],
        "error_message": row[9],
        "job_id": int(row[10]) if row[10] is not None else None,
        "created_at": row[11],
        "finished_at": row[12],
        "expires_at": row[13],
    }


def expire_stale() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.media_links SET status='EXPIRED', finished_at=COALESCE(finished_at, CURRENT_TIMESTAMP) "
                "WHERE status='READY' AND expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP"
            )
            return int(cur.rowcount)


def find_ready(owner_user_id: str, media_kind: str, media_id: str) -> dict | None:
    expire_stale()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM public.media_links "
                "WHERE owner_user_id=%s AND media_kind=%s AND media_id=%s "
                "AND provider='albion' AND status='READY' "
                "AND expires_at > CURRENT_TIMESTAMP "
                "ORDER BY link_id DESC LIMIT 1",
                (owner_user_id, media_kind, media_id),
            )
            row = cur.fetchone()
    return _row(row) if row is not None else None


def create_pending(
    *,
    owner_user_id: str,
    owner_name: str | None,
    media_kind: str,
    media_id: str,
) -> dict:
    existing = find_ready(owner_user_id, media_kind, media_id)
    if existing is not None:
        return existing

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.media_links "
                "(owner_user_id, owner_name, media_kind, media_id, provider, status) "
                "VALUES (%s, %s, %s, %s, 'albion', 'PENDING') "
                f"RETURNING {_COLUMNS}",
                (owner_user_id, owner_name, media_kind, media_id),
            )
            return _row(cur.fetchone())


def attach_job(link_id: int, job_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.media_links SET job_id=%s WHERE link_id=%s",
                (int(job_id), int(link_id)),
            )


def get(link_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM public.media_links WHERE link_id=%s",
                (int(link_id),),
            )
            row = cur.fetchone()
    return _row(row) if row is not None else None


def mark_ready(link_id: int, *, url: str, expires_at, object_key: str | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.media_links SET status='READY', url=%s, object_key=%s, "
                "error_message=NULL, finished_at=CURRENT_TIMESTAMP, expires_at=%s "
                "WHERE link_id=%s",
                (url, object_key, expires_at, int(link_id)),
            )


def mark_failed(link_id: int, message: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.media_links SET status='FAILED', error_message=%s, "
                "finished_at=CURRENT_TIMESTAMP WHERE link_id=%s",
                (str(message)[:1000], int(link_id)),
            )


def list_links(
    *,
    owner_user_id: str | None = None,
    limit: int = 100,
    include_unready: bool = False,
) -> list[dict]:
    """Ready links by default; ``include_unready`` also returns PENDING/FAILED rows."""

    expire_stale()
    limit = max(1, min(int(limit), 200))
    if include_unready:
        sql = (
            f"SELECT {_COLUMNS} FROM public.media_links "
            "WHERE status IN ('PENDING', 'READY', 'FAILED')"
        )
    else:
        sql = f"SELECT {_COLUMNS} FROM public.media_links WHERE status='READY'"
    params: list[Any] = []
    if owner_user_id is not None:
        sql += " AND owner_user_id=%s"
        params.append(owner_user_id)
    sql += " ORDER BY created_at DESC, link_id DESC LIMIT %s"
    params.append(limit)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_row(row) for row in cur.fetchall()]


def media_source(media_kind: str, media_id: str) -> dict | None:
    """Resolve a DB-registered media id to its read-only source path."""

    if media_kind == "photo":
        source = photo_repository.get_photo_source(media_id)
        if source is None:
            return None
        return {
            "path": source["source_path"],
            "filename": source["filename"],
        }

    if media_kind == "video":
        source = video_repository.video_source(media_id)
        if source is None:
            return None
        return {
            "path": source["source_path"],
            "filename": source["filename"],
        }

    return None
