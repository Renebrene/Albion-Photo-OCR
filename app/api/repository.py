"""
Read-only PostgreSQL access for the web API.

Reuses the INGEST connection env convention (INGEST_DB_*). Only SELECTs are
issued. photo_id is always passed as a query parameter, never interpolated.
"""

from __future__ import annotations

from app.api.schemas import PhotoSummary
from app.ingest.database import get_connection

_COLUMNS = "photo_id, filename, width, height, container_format"


def list_photos(
    *,
    limit: int,
    cursor: str | None = None,
    query: str | None = None,
) -> tuple[list[PhotoSummary], str | None]:
    """
    Return one page of registered photos ordered by photo_id.

    Fetches limit + 1 rows to detect whether a further page exists.
    """

    sql = f"SELECT {_COLUMNS} FROM public.photos"  # noqa: S608 - fixed columns
    clauses: list[str] = []
    params: list[object] = []

    if cursor:
        clauses.append("photo_id > %s")
        params.append(cursor)

    if query:
        clauses.append("filename ILIKE %s")
        params.append(f"%{query}%")

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    sql += " ORDER BY photo_id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [
        PhotoSummary(
            photo_id=row[0],
            filename=row[1],
            width=row[2],
            height=row[3],
            container_format=row[4],
        )
        for row in rows
    ]

    next_cursor = items[-1].photo_id if has_next and items else None

    return items, next_cursor


def get_photo(photo_id: str) -> PhotoSummary | None:
    """Return one registered photo, or None when it does not exist."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM public.photos WHERE photo_id = %s",  # noqa: S608
                (photo_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return PhotoSummary(
        photo_id=row[0],
        filename=row[1],
        width=row[2],
        height=row[3],
        container_format=row[4],
    )
