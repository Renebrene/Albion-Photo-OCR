"""
Read-only PostgreSQL access for the web API.

Reuses the INGEST connection env convention (INGEST_DB_*). Only SELECTs are
issued. photo_id is always passed as a query parameter, never interpolated.
"""

from __future__ import annotations

from psycopg.types.json import Json

from app.api.schemas import (
    DinoBatchSummary,
    DinoRunSummary,
    HybridRunSummary,
    PhotoSummary,
)
from app.ingest.database import get_connection

# Address comes from the recognition pipeline (HYBRID verdict, falling back to
# the DINO best candidate); `client` comes from the parallel QWEN metadata.
_PHOTO_BASE = """
    SELECT
        p.photo_id        AS photo_id,
        p.filename        AS filename,
        p.width           AS width,
        p.height          AS height,
        p.container_format AS container_format,
        COALESCE(
            (
                SELECT h.hybrid_final_id
                FROM public.hybrid_results AS h
                WHERE h.photo_id = p.photo_id
                  AND h.status = 'DONE'
                ORDER BY h.finished_at DESC NULLS LAST,
                         h.hybrid_run_id DESC
                LIMIT 1
            ),
            (
                SELECT r.dino_best_id
                FROM public.dino_runs AS r
                WHERE r.photo_id = p.photo_id
                  AND r.status = 'DONE'
                  AND r.dino_best_id IS NOT NULL
                ORDER BY r.finished_at DESC NULLS LAST,
                         r.run_id DESC
                LIMIT 1
            )
        ) AS address,
        q.client AS client,
        q.brand AS brand,
        q.category AS category,
        p.created_at AS created_at,
        p.taken_at AS taken_at,
        p.size_bytes AS size_bytes
    FROM public.photos AS p
    LEFT JOIN public.photo_qwen AS q ON q.photo_id = p.photo_id
"""

# The recognised id (t.address) is resolved to the directory names in an outer
# query: the id is computed above, so it cannot be joined inside the same
# SELECT. Photos without a mapping read back with NULL names.
_PHOTO_DERIVED = """
    SELECT
        t.*,
        d.legal_address AS legal_address,
        d.simple_address AS simple_address
    FROM (""" + _PHOTO_BASE + """) AS t
    LEFT JOIN public.address_fingerprints AS f
           ON f.fingerprint_id = t.address
          AND f.active
    LEFT JOIN public.address_directory AS d
           ON d.address_id = f.address_id
          AND d.active
"""

_PHOTO_SELECT = (
    "SELECT photo_id, filename, width, height, container_format, "
    "address, client, brand, category, created_at, taken_at, size_bytes, "
    "legal_address, simple_address "
    "FROM (" + _PHOTO_DERIVED + ") AS t"
)


def _photo_row(row) -> PhotoSummary:
    return PhotoSummary(
        photo_id=row[0],
        filename=row[1],
        width=row[2],
        height=row[3],
        container_format=row[4],
        address=row[5],
        client=row[6],
        brand=row[7],
        category=row[8],
        created_at=row[9],
        taken_at=row[10],
        size_bytes=row[11],
        legal_address=row[12],
        simple_address=row[13],
    )


def list_photos(
    *,
    limit: int,
    cursor: str | None = None,
    query: str | None = None,
    addresses: list[str] | None = None,
    clients: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
    collection_id: int | None = None,
    ids: list[str] | None = None,
) -> tuple[list[PhotoSummary], str | None]:
    """
    Return one page of registered photos ordered by photo_id.

    `addresses` are recognition results (HYBRID/DINO) and `clients` are the
    QWEN metadata; both accept several values with OR semantics (matching the
    legacy multi-select panels). `query` searches several fields at once
    (filename, client, brand, category, description, address), mirroring the
    legacy global search. date_from/date_to filter by the upload date
    (photos.created_at) or, with date_mode="capture", by the EXIF capture
    date (photos.taken_at; photos without one are not matched). Fetches
    limit + 1 rows to detect a further page.
    """

    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be 'upload' or 'capture'")

    date_column = "t.taken_at" if date_mode == "capture" else "t.created_at"

    sql = _PHOTO_SELECT
    clauses: list[str] = []
    params: list[object] = []

    if cursor:
        clauses.append("t.photo_id > %s")
        params.append(cursor)

    if query:
        like = f"%{query}%"
        # Split by relation so each predicate can use its trigram GIN index
        # (schema/014): a multi-relation OR spanning photos and photo_qwen
        # cannot be pushed into index scans, but a UNION of per-table lookups
        # can (BitmapOr on photo_qwen). `address` is a computed column and
        # stays as a plain ILIKE on the outer query.
        clauses.append(
            "(t.photo_id IN ("
            "  SELECT photo_id FROM public.photos WHERE filename ILIKE %s "
            "  UNION "
            "  SELECT photo_id FROM public.photo_qwen "
            "  WHERE (client ILIKE %s OR brand ILIKE %s "
            "         OR category ILIKE %s OR description ILIKE %s)"
            ") OR t.address ILIKE %s)"
        )
        params.extend([like] * 6)

    if addresses:
        likes = [f"%{value}%" for value in addresses]
        clauses.append(
            "(" + " OR ".join(["t.address ILIKE %s"] * len(likes)) + ")"
        )
        params.extend(likes)

    if clients:
        # Match either the raw QWEN client or any alias mapping to a
        # canonical value that matches (client_aliases).
        parts = []
        for value in clients:
            like = f"%{value}%"
            parts.append(
                "(t.client ILIKE %s OR t.client IN ("
                "SELECT alias FROM public.client_aliases "
                "WHERE canonical ILIKE %s))"
            )
            params.extend([like, like])
        clauses.append("(" + " OR ".join(parts) + ")")

    if date_from:
        clauses.append(f"{date_column} >= %s::date")
        params.append(date_from)

    if date_to:
        clauses.append(f"{date_column} < (%s::date + interval '1 day')")
        params.append(date_to)

    if collection_id is not None:
        clauses.append(
            "t.photo_id IN ("
            "SELECT member_value FROM public.collection_members "
            "WHERE collection_id = %s AND member_type = 'photo')"
        )
        params.append(collection_id)

    if ids:
        clauses.append("t.photo_id = ANY(%s)")
        params.append(list(ids))

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    sql += " ORDER BY t.photo_id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [_photo_row(row) for row in rows]

    next_cursor = items[-1].photo_id if has_next and items else None

    return items, next_cursor


def qwen_status_counts() -> dict:
    """photo_qwen row counts grouped by status."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, count(*) FROM public.photo_qwen GROUP BY status"
            )
            return {row[0]: int(row[1]) for row in cur.fetchall()}


def photo_ids_with_qwen_status(status: str) -> list[str]:
    """photo_ids whose QWEN row has the given status (ordered)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id FROM public.photo_qwen "
                "WHERE status = %s ORDER BY photo_id",
                (status,),
            )
            return [row[0] for row in cur.fetchall()]


def get_photo(photo_id: str) -> PhotoSummary | None:
    """Return one registered photo, or None when it does not exist."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _PHOTO_SELECT + " WHERE t.photo_id = %s",
                (photo_id,),
            )
            row = cur.fetchone()

    return _photo_row(row) if row is not None else None


def all_photo_ids() -> list[str]:
    """Return every registered photo_id, ordered."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT photo_id FROM public.photos ORDER BY photo_id")
            return [row[0] for row in cur.fetchall()]


def list_addresses(*, limit: int = 1000) -> list[dict]:
    """
    Distinct addresses (recognition result) with photo counts.

    Used by the side panel that mirrors the legacy UI.
    """

    sql = (
        "SELECT address, count(*) AS count FROM (" + _PHOTO_SELECT + ") AS t "
        "WHERE address IS NOT NULL AND address <> '' "
        "GROUP BY address ORDER BY address LIMIT %s"
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return [
                {"address": row[0], "count": int(row[1])}
                for row in cur.fetchall()
            ]


def list_clients(*, limit: int = 1000) -> list[dict]:
    """
    Distinct QWEN clients with photo counts.

    Aliased raw values are folded into their canonical client (client_aliases).
    """

    sql = (
        "SELECT COALESCE(a.canonical, t.client) AS client, count(*) AS count "
        "FROM (" + _PHOTO_SELECT + ") AS t "
        "LEFT JOIN public.client_aliases AS a ON a.alias = t.client "
        "WHERE t.client IS NOT NULL AND t.client <> '' "
        "GROUP BY COALESCE(a.canonical, t.client) "
        "ORDER BY lower(COALESCE(a.canonical, t.client)) LIMIT %s"
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return [
                {"client": row[0], "count": int(row[1])}
                for row in cur.fetchall()
            ]


# ---------------------------------------------------------------------------
# Client aliases (QWEN client name normalization)
# ---------------------------------------------------------------------------


def list_client_aliases() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT alias, canonical FROM public.client_aliases "
                "ORDER BY lower(alias)"
            )
            return [
                {"alias": row[0], "canonical": row[1]}
                for row in cur.fetchall()
            ]


def upsert_client_alias(alias: str, canonical: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.client_aliases (alias, canonical)
                VALUES (%s, %s)
                ON CONFLICT (alias) DO UPDATE
                    SET canonical = EXCLUDED.canonical
                """,
                (alias, canonical),
            )

    return {"alias": alias, "canonical": canonical}


def delete_client_alias(alias: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.client_aliases WHERE alias = %s",
                (alias,),
            )
            return cur.rowcount == 1


# ---------------------------------------------------------------------------
# Collections / bookmarks
# ---------------------------------------------------------------------------


def _collection_row(row) -> dict:
    return {
        "collection_id": int(row[0]),
        "name": row[1],
        "kind": row[2],
        "client": row[3],
        "scope": row[4],
        "created_at": row[5],
        "members": int(row[6]),
    }


def list_collections() -> list[dict]:
    sql = """
        SELECT
            c.collection_id,
            c.name,
            c.kind,
            c.client,
            c.scope,
            c.created_at,
            (
                SELECT count(*)
                FROM public.collection_members AS m
                WHERE m.collection_id = c.collection_id
            ) AS members
        FROM public.collections AS c
        ORDER BY lower(c.name)
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [_collection_row(row) for row in cur.fetchall()]


def get_collection(collection_id: int) -> dict | None:
    sql = """
        SELECT
            c.collection_id, c.name, c.kind, c.client, c.scope, c.created_at,
            (
                SELECT count(*)
                FROM public.collection_members AS m
                WHERE m.collection_id = c.collection_id
            ) AS members
        FROM public.collections AS c
        WHERE c.collection_id = %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (collection_id,))
            row = cur.fetchone()

    return _collection_row(row) if row is not None else None


def create_collection(
    *,
    name: str,
    kind: str = "Моя",
    client: str | None = None,
    scope: str = "photos",
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.collections (name, kind, client, scope)
                VALUES (%s, %s, %s, %s)
                RETURNING collection_id
                """,
                (name, kind, client, scope),
            )
            collection_id = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT c.collection_id, c.name, c.kind, c.client, c.scope,
                       c.created_at, 0 AS members
                FROM public.collections AS c
                WHERE c.collection_id = %s
                """,
                (collection_id,),
            )
            return _collection_row(cur.fetchone())


def delete_collection(collection_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.collections WHERE collection_id = %s",
                (collection_id,),
            )
            return cur.rowcount == 1


def collection_member_values(
    collection_id: int,
    member_type: str = "photo",
) -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT member_value
                FROM public.collection_members
                WHERE collection_id = %s AND member_type = %s
                ORDER BY member_value
                """,
                (collection_id, member_type),
            )
            return [row[0] for row in cur.fetchall()]


def add_collection_members(
    collection_id: int,
    *,
    member_type: str,
    values: list[str],
) -> int:
    if not values:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO public.collection_members (
                    collection_id, member_type, member_value
                )
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                [(collection_id, member_type, value) for value in values],
            )
            inserted = cur.rowcount

            cur.execute(
                "UPDATE public.collections SET updated_at = CURRENT_TIMESTAMP "
                "WHERE collection_id = %s",
                (collection_id,),
            )

            return inserted


def remove_collection_members(
    collection_id: int,
    *,
    member_type: str,
    values: list[str],
) -> int:
    if not values:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM public.collection_members
                WHERE collection_id = %s
                  AND member_type = %s
                  AND member_value = ANY(%s)
                """,
                (collection_id, member_type, values),
            )
            return cur.rowcount


def get_photo_source(photo_id: str) -> dict | None:
    """
    Return the registered source path/metadata for one photo.

    The path comes from the database registration; it is never taken from
    client input.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_path, filename, container_format "
                "FROM public.photos WHERE photo_id = %s",
                (photo_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "source_path": row[0],
        "filename": row[1],
        "container_format": row[2],
    }


# ---------------------------------------------------------------------------
# DINO batches / runs and HYBRID runs (read-only status views)
# ---------------------------------------------------------------------------


def _as_dino_batch(row) -> DinoBatchSummary:
    return DinoBatchSummary(
        batch_id=row[0],
        run_type=row[1],
        status=row[2],
        total_count=row[3],
        completed_count=row[4],
        failed_count=row[5],
        created_at=row[6],
        finished_at=row[7],
    )


def list_dino_batches(
    *,
    limit: int,
    cursor: int | None = None,
) -> tuple[list[DinoBatchSummary], int | None]:
    """Return DINO batches ordered by batch_id (newest last)."""

    sql = (
        "SELECT batch_id, run_type, status, total_count, "
        "completed_count, failed_count, created_at, finished_at "
        "FROM public.dino_batches"
    )
    params: list[object] = []

    if cursor is not None:
        sql += " WHERE batch_id > %s"
        params.append(cursor)

    sql += " ORDER BY batch_id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [_as_dino_batch(row) for row in rows]
    next_cursor = items[-1].batch_id if has_next and items else None

    return items, next_cursor


def get_dino_batch(batch_id: int) -> DinoBatchSummary | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT batch_id, run_type, status, total_count, "
                "completed_count, failed_count, created_at, finished_at "
                "FROM public.dino_batches WHERE batch_id = %s",
                (batch_id,),
            )
            row = cur.fetchone()

    return _as_dino_batch(row) if row is not None else None


def list_dino_runs(
    *,
    batch_id: int,
    limit: int,
    cursor: int | None = None,
) -> tuple[list[DinoRunSummary], int | None]:
    """Return the runs of one DINO batch ordered by run_id."""

    sql = (
        "SELECT run_id, photo_id, run_type, status, dino_best_id, "
        "dino_score, dino_confidence, dino_status, dino_time_sec, "
        "error_message, finished_at "
        "FROM public.dino_runs WHERE batch_id = %s"
    )
    params: list[object] = [batch_id]

    if cursor is not None:
        sql += " AND run_id > %s"
        params.append(cursor)

    sql += " ORDER BY run_id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [
        DinoRunSummary(
            run_id=row[0],
            photo_id=row[1],
            run_type=row[2],
            status=row[3],
            dino_best_id=row[4],
            dino_score=row[5],
            dino_confidence=row[6],
            dino_status=row[7],
            dino_time_sec=row[8],
            error_message=row[9],
            finished_at=row[10],
        )
        for row in rows
    ]

    next_cursor = items[-1].run_id if has_next and items else None

    return items, next_cursor


def list_hybrid_runs(
    *,
    limit: int,
    cursor: int | None = None,
) -> tuple[list[HybridRunSummary], int | None]:
    """Return HYBRID runs ordered by hybrid_run_id."""

    sql = (
        "SELECT hybrid_run_id, dino_batch_id, status, total_count, "
        "completed_count, failed_count, created_at, finished_at "
        "FROM public.hybrid_runs"
    )
    params: list[object] = []

    if cursor is not None:
        sql += " WHERE hybrid_run_id > %s"
        params.append(cursor)

    sql += " ORDER BY hybrid_run_id LIMIT %s"
    params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [
        HybridRunSummary(
            hybrid_run_id=row[0],
            dino_batch_id=row[1],
            status=row[2],
            total_count=row[3],
            completed_count=row[4],
            failed_count=row[5],
            created_at=row[6],
            finished_at=row[7],
        )
        for row in rows
    ]

    next_cursor = items[-1].hybrid_run_id if has_next and items else None

    return items, next_cursor


# ---------------------------------------------------------------------------
# Saved searches (bookmarked GRID filters)
# ---------------------------------------------------------------------------


def _saved_search_row(row) -> dict:
    return {
        "search_id": int(row[0]),
        "name": row[1],
        "filters": row[2] or {},
        "created_at": row[3],
    }


def list_saved_searches() -> list[dict]:
    sql = """
        SELECT search_id, name, filters, created_at
        FROM public.saved_searches
        ORDER BY lower(name)
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [_saved_search_row(row) for row in cur.fetchall()]


def create_saved_search(*, name: str, filters: dict) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.saved_searches (name, filters)
                VALUES (%s, %s)
                RETURNING search_id, name, filters, created_at
                """,
                (name, Json(filters or {})),
            )
            return _saved_search_row(cur.fetchone())


def delete_saved_search(search_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.saved_searches WHERE search_id = %s",
                (search_id,),
            )
            return cur.rowcount == 1


# ---------------------------------------------------------------------------
# Per-manager UI state
# ---------------------------------------------------------------------------


def get_manager_selection(user_id: str) -> dict | None:
    """Return the stored state blob for one user, or None when absent."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT state FROM public.manager_selections WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()

    return row[0] if row is not None else None


def save_manager_selection(user_id: str, state: dict) -> None:
    """Upsert the state blob for one user."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.manager_selections (user_id, state)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                    SET state = EXCLUDED.state,
                        updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, Json(state or {})),
            )
