"""
Read-only PostgreSQL access for the web API.

Reuses the INGEST connection env convention (INGEST_DB_*). Only SELECTs are
issued. photo_id is always passed as a query parameter, never interpolated.
"""

from __future__ import annotations

from psycopg.types.json import Json

from app.api import fingerprints
from app.api.config import display_source_directory
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
        q.status AS qwen_status,
        (q.description IS NOT NULL AND btrim(q.description) <> '')
            AS qwen_described,
        p.created_at AS created_at,
        p.taken_at AS taken_at,
        p.size_bytes AS size_bytes,
        p.source_path AS source_path
    FROM public.photos AS p
    LEFT JOIN public.photo_qwen AS q ON q.photo_id = p.photo_id
"""

# The recognised id (t.address) is resolved to the directory names in an outer
# query: the id is computed above, so it cannot be joined inside the same
# SELECT. Photos without a mapping read back with NULL names.
_PHOTO_DERIVED = """
    SELECT
        t.*,
        COALESCE(od.legal_address, d.legal_address) AS legal_address,
        COALESCE(od.simple_address, d.simple_address) AS simple_address
    FROM (""" + _PHOTO_BASE + """) AS t
    LEFT JOIN public.address_fingerprints AS f
           ON f.fingerprint_id = t.address
          AND f.active
    LEFT JOIN public.address_directory AS d
           ON d.address_id = f.address_id
          AND d.active
    LEFT JOIN public.photo_address_overrides AS ov
           ON ov.photo_id = t.photo_id
    LEFT JOIN public.address_directory AS od
           ON od.address_id = ov.address_id
          AND od.active
"""

_PHOTO_SELECT = (
    "SELECT photo_id, filename, width, height, container_format, "
    "address, client, brand, category, created_at, taken_at, size_bytes, source_path, "
    "legal_address, simple_address, qwen_status, qwen_described "
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
        source_directory=display_source_directory(row[12]) if row[12] else "",
        legal_address=row[13],
        simple_address=row[14],
        qwen_status=row[15],
        qwen_described=bool(row[16]) if row[16] is not None else None,
    )


def _photo_where(
    *,
    cursor: str | None = None,
    query: str | None = None,
    addresses: list[str] | None = None,
    clients: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
    collection_id: int | None = None,
    ids: list[str] | None = None,
    brand: str | None = None,
    tag: str | None = None,
    category: str | None = None,
    recognized_only: bool = False,
) -> tuple[str, list[object]]:
    """
    WHERE-часть запроса фото и её параметры.

    Вынесена из `list_photos`, чтобы счётчик «За период N фото» использовал
    ровно те же условия, что и сам грид: иначе подпись и выдача расходятся.
    Курсор сюда передаётся только для постраничного продолжения; счётчик
    вызывает функцию с `cursor=None`.
    """

    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be 'upload' or 'capture'")

    date_column = "t.taken_at" if date_mode == "capture" else "t.created_at"

    clauses: list[str] = []
    params: list[object] = []
    # Теги (адреса, клиенты, бренд, тег, категория) складываются по ИЛИ:
    # выбранный бренд не сужает выбранных клиентов, а добавляет их фото.
    # Свободный текст, даты и «только распознанные» остаются отдельными
    # условиями И.
    tag_clauses: list[str] = []

    if not ids and cursor:
        clauses.append("t.photo_id > %s")
        params.append(cursor)

    if query:
        like = f"%{query}%"
        # Split by relation so each predicate can use its trigram GIN index
        # (schema/014): a multi-relation OR spanning photos and photo_qwen
        # cannot be pushed into index scans, but a UNION of per-table lookups
        # can (BitmapOr on photo_qwen). `address` is a computed column and
        # stays as a plain ILIKE on the outer query. `tags` is a JSONB array
        # (schema/007); the CASE keeps jsonb_array_elements_text from raising
        # on a NULL or a non-array value that a manual edit could leave behind.
        #
        # Client and brand are also matched through the alias dictionary
        # (schema/035): typing the canonical name finds the raw spellings QWEN
        # invented (and vice versa is not needed - the raw value is stored).
        clauses.append(
            "(t.photo_id IN ("
            "  SELECT photo_id FROM public.photos WHERE filename ILIKE %s "
            "  UNION "
            "  SELECT photo_id FROM public.photo_qwen "
            "  WHERE (client ILIKE %s "
            "         OR client IN (SELECT alias FROM public.client_aliases "
            "                       WHERE kind = 'client' AND canonical ILIKE %s)"
            "         OR brand ILIKE %s "
            "         OR brand IN (SELECT alias FROM public.client_aliases "
            "                      WHERE kind = 'brand' AND canonical ILIKE %s)"
            "         OR category ILIKE %s OR description ILIKE %s "
            "         OR EXISTS (SELECT 1 FROM jsonb_array_elements_text("
            "              CASE WHEN jsonb_typeof(tags) = 'array' THEN tags END"
            "            ) AS tag WHERE tag ILIKE %s))"
            ") OR t.address ILIKE %s"
            " OR t.legal_address ILIKE %s OR t.simple_address ILIKE %s)"
        )
        params.extend([like] * 11)

    if addresses:
        # A manually corrected photo belongs ONLY to the chosen address: the
        # recognised fingerprint is ignored while an override exists.
        # Values come from the address panel, so match them exactly
        # (case-insensitive) rather than by substring: selecting 78_v33 must
        # not also pull 178_v33.
        parts = []
        for value in addresses:
            parts.append(
                "((NOT EXISTS ("
                "   SELECT 1 FROM public.photo_address_overrides AS ov"
                "   WHERE ov.photo_id = t.photo_id)"
                "  AND LOWER(t.address) = LOWER(%s))"
                " OR EXISTS ("
                "   SELECT 1 FROM public.photo_address_overrides AS ov"
                "   JOIN public.address_fingerprints AS mfp"
                "     ON mfp.address_id = ov.address_id AND mfp.active"
                "   WHERE ov.photo_id = t.photo_id"
                "     AND LOWER(mfp.fingerprint_id) = LOWER(%s)))"
            )
            params.extend([value, value])

        tag_clauses.append("(" + " OR ".join(parts) + ")")

    if clients:
        # Exact value (case-insensitive), not a substring: selecting «СТС»
        # must not also pull a client whose name merely contains «стс».
        # A raw spelling is folded through the alias dictionary to the chosen
        # canonical client. `kind = 'client'`: the dictionary also holds
        # brands, and a brand alias must not pull photos by their client.
        parts = []
        for value in clients:
            parts.append(
                "(LOWER(t.client) = LOWER(%s) OR EXISTS ("
                "SELECT 1 FROM public.client_aliases AS ca "
                "WHERE LOWER(ca.alias) = LOWER(t.client) "
                "  AND ca.kind = 'client' "
                "  AND LOWER(ca.canonical) = LOWER(%s)))"
            )
            params.extend([value, value])
        tag_clauses.append("(" + " OR ".join(parts) + ")")

    if brand:
        tag_clauses.append("LOWER(t.brand) = LOWER(%s)")
        params.append(brand)

    if category:
        tag_clauses.append("LOWER(t.category) = LOWER(%s)")
        params.append(category)

    if tag:
        tag_clauses.append(
            "EXISTS ("
            "  SELECT 1 FROM public.photo_qwen AS qq"
            "  CROSS JOIN LATERAL jsonb_array_elements_text("
            "    CASE WHEN jsonb_typeof(qq.tags) = 'array' THEN qq.tags END"
            "  ) AS item"
            "  WHERE qq.photo_id = t.photo_id"
            "    AND LOWER(item) = LOWER(%s))"
        )
        params.append(tag)

    if tag_clauses:
        clauses.append("(" + " OR ".join(tag_clauses) + ")")

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

    if recognized_only:
        # The grid shows a photo only after recognition has produced an
        # address: a DONE HYBRID verdict with a final id, or a manual override.
        # Videos live in a separate list and are not affected.
        clauses.append(
            "(EXISTS (SELECT 1 FROM public.hybrid_results AS hr"
            " WHERE hr.photo_id = t.photo_id AND hr.status = 'DONE'"
            "   AND hr.hybrid_final_id IS NOT NULL)"
            " OR EXISTS (SELECT 1 FROM public.photo_address_overrides AS ov"
            " WHERE ov.photo_id = t.photo_id))"
        )

    if not clauses:
        return "", params

    return " WHERE " + " AND ".join(clauses), params


def count_photos(
    *,
    query: str | None = None,
    addresses: list[str] | None = None,
    clients: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
    collection_id: int | None = None,
    ids: list[str] | None = None,
    brand: str | None = None,
    tag: str | None = None,
    category: str | None = None,
    recognized_only: bool = False,
) -> int:
    """Сколько фото подходит под те же фильтры, что и грид."""

    where, params = _photo_where(
        query=query,
        addresses=addresses,
        clients=clients,
        date_from=date_from,
        date_to=date_to,
        date_mode=date_mode,
        collection_id=collection_id,
        ids=ids,
        brand=brand,
        tag=tag,
        category=category,
        recognized_only=recognized_only,
    )
    sql = "SELECT count(*) FROM (" + _PHOTO_SELECT + where + ") AS filtered"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return int(cur.fetchone()[0])


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
    brand: str | None = None,
    tag: str | None = None,
    category: str | None = None,
    recognized_only: bool = False,
) -> tuple[list[PhotoSummary], str | None]:
    """
    Return one page of registered photos ordered by photo_id.

    `addresses` are recognition results (HYBRID/DINO) and `clients` are the
    QWEN metadata; both accept several values with OR semantics (matching the
    legacy multi-select panels). `query` searches several fields at once
    (filename, client, brand, category, description, tags, address) and also
    resolves client/brand through the alias dictionary, so the canonical name
    finds the raw spellings QWEN produced. date_from/date_to filter by the upload date
    (photos.created_at) or, with date_mode="capture", by the EXIF capture
    date (photos.taken_at; photos without one are not matched). Fetches
    limit + 1 rows to detect a further page.

    `ids` switches the page to the caller's own order (a ranked search): the
    page is then taken by *rank offset*, and the cursor carries that offset as
    "rank:N". A photo_id cursor cannot continue a ranked list - it would both
    skip and repeat rows - so it is ignored in that mode.
    """

    where, params = _photo_where(
        cursor=cursor,
        query=query,
        addresses=addresses,
        clients=clients,
        date_from=date_from,
        date_to=date_to,
        date_mode=date_mode,
        collection_id=collection_id,
        ids=ids,
        brand=brand,
        tag=tag,
        category=category,
        recognized_only=recognized_only,
    )
    sql = _PHOTO_SELECT + where

    order_param: list[str] | None = None
    offset = 0

    if ids:
        # Preserve the caller's order (e.g. a ranked search result) instead of
        # re-sorting by photo_id: the array position is the intended rank.
        order_param = list(ids)

        if cursor and cursor.startswith("rank:"):
            try:
                offset = max(0, int(cursor[len("rank:"):]))
            except ValueError:
                offset = 0

    if order_param is not None:
        sql += (
            " ORDER BY array_position(%s::text[], t.photo_id) "
            "LIMIT %s OFFSET %s"
        )
        params.extend([order_param, limit + 1, offset])
    else:
        sql += " ORDER BY t.photo_id LIMIT %s"
        params.append(limit + 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [_photo_row(row) for row in rows]

    if order_param is not None:
        # Rank-based cursor: the offset of the next page inside the ranked list.
        next_cursor = (
            f"rank:{offset + len(items)}" if has_next and items else None
        )
    else:
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


def qwen_stats() -> dict:
    """
    One snapshot for the QWEN card: base size, statuses and last runs.

    `photo_qwen` only has a row per described photo, so its status counts are
    *not* the base size: a photo that was never queued has no row at all. The
    card needs both numbers, hence `photos` (registered photos) next to
    `counts`.

    `processed` counts photos that HAVE a description, not rows currently in
    status DONE: a re-run flips the row to RUNNING while the previous
    description stays in place (`mark_running` does not clear it), so counting
    DONE made the counter go backwards during a re-recognition pass.

    `runs` groups finished QWEN jobs by the trigger recorded in the payload
    ("manual" / "automation" / "pipeline"; older rows default to "manual"),
    so the window can show when each kind last ran.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM public.photos")
            photos = int(cur.fetchone()[0])

            cur.execute(
                "SELECT status, count(*) FROM public.photo_qwen GROUP BY status"
            )
            counts = {row[0]: int(row[1]) for row in cur.fetchall()}

            cur.execute(
                "SELECT count(*) FROM public.photo_qwen "
                "WHERE description IS NOT NULL AND btrim(description) <> ''"
            )
            described = int(cur.fetchone()[0])

            # Какая модель дала описания: при смене модели видно, что
            # перераспознано, а что ещё держит старый результат.
            cur.execute(
                "SELECT qwen_model, count(*) FROM public.photo_qwen "
                "WHERE qwen_model IS NOT NULL AND qwen_model <> '' "
                "GROUP BY 1 ORDER BY 2 DESC, 1"
            )
            models = [
                {"model": row[0], "photos": int(row[1])}
                for row in cur.fetchall()
            ]

            # Расход облака: локальная Ollama токенов не сообщает.
            cur.execute(
                "SELECT COALESCE(SUM(prompt_tokens), 0), "
                "       COALESCE(SUM(completion_tokens), 0), "
                "       COALESCE(SUM(total_tokens), 0) "
                "FROM public.photo_qwen"
            )
            tokens_row = cur.fetchone()
            tokens = {
                "prompt": int(tokens_row[0]),
                "completion": int(tokens_row[1]),
                "total": int(tokens_row[2]),
            }

            cur.execute("SELECT count(*) FROM public.photo_qwen_history")
            history_rows = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COALESCE(payload ->> 'source', 'manual') AS source,
                       count(*) AS jobs,
                       max(finished_at) AS last_finished_at,
                       count(*) FILTER (WHERE status = 'FAILED') AS failed
                FROM public.job_queue
                WHERE job_type = 'QWEN_PHOTO'
                GROUP BY 1
                ORDER BY 1
                """
            )
            runs = [
                {
                    "source": row[0],
                    "jobs": int(row[1]),
                    "last_finished_at": row[2],
                    "failed": int(row[3]),
                }
                for row in cur.fetchall()
            ]

    return {
        "photos": photos,
        "counts": counts,
        "processed": described,
        "remaining": max(0, photos - described),
        "queued": counts.get("PENDING", 0) + counts.get("RUNNING", 0),
        "models": models,
        "tokens": tokens,
        "history_rows": history_rows,
        "runs": runs,
    }


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


def list_addresses(
    *,
    limit: int = 1000,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
) -> list[dict]:
    """
    The address filter of the photo page: one entry per fingerprint.

    The list is built from the fingerprint registry, not from the photos, so it
    is the list of fingerprints (each one is an address/shield) shown by name -
    the manual name, the alias of its address, or the technical id. A
    fingerprint stays in the panel even while no photo has been recognised as
    it; its counter says how many photos carry its verdict.

    A recognised id without a registry row is appended, so a photo can never
    become unfilterable. Archived (``active = false``) fingerprints are hidden
    from the panel even when they still have recognised photos: hiding a
    fingerprint is how the operator removes a duplicate/obsolete shield from
    «Адреса». `address` is the fingerprint id the filter sends; `name` is what
    the panel shows.
    """

    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be 'upload' or 'capture'")

    date_column = "t.taken_at" if date_mode == "capture" else "t.created_at"
    period_parts: list[str] = []
    period_params: list[object] = []

    if date_from:
        period_parts.append(f"{date_column} >= %s::date")
        period_params.append(date_from)

    if date_to:
        period_parts.append(f"{date_column} < (%s::date + interval '1 day')")
        period_params.append(date_to)

    period_sql = " AND ".join(period_parts) or "TRUE"

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Photo counts per address panel entry. A manual override moves the
            # photo to the chosen address's representative fingerprint, so the
            # counters match what the address filter returns. `period_count`
            # repeats the same count with the caller's date range; `count`
            # stays all-time and ignores the filter.
            cur.execute(
                """
                SELECT COALESCE(mapped.fingerprint_id, t.address) AS address,
                       count(*) AS count,
                       count(*) FILTER (WHERE """ + period_sql + """) AS period_count
                FROM (""" + _PHOTO_SELECT + """) AS t
                LEFT JOIN public.photo_address_overrides AS ov
                       ON ov.photo_id = t.photo_id
                LEFT JOIN LATERAL (
                    SELECT f.fingerprint_id
                    FROM public.address_fingerprints AS f
                    JOIN public.fingerprints AS reg
                      ON reg.fingerprint_id = f.fingerprint_id
                     AND reg.active
                    WHERE f.address_id = ov.address_id
                      AND f.active
                    ORDER BY f.fingerprint_id
                    LIMIT 1
                ) AS mapped ON TRUE
                WHERE COALESCE(mapped.fingerprint_id, t.address) IS NOT NULL
                  AND COALESCE(mapped.fingerprint_id, t.address) <> ''
                  AND (
                    EXISTS (
                        SELECT 1 FROM public.hybrid_results AS hr
                        WHERE hr.photo_id = t.photo_id
                          AND hr.status = 'DONE'
                          AND hr.hybrid_final_id IS NOT NULL
                    )
                    OR EXISTS (
                        SELECT 1 FROM public.photo_address_overrides AS ov2
                        WHERE ov2.photo_id = t.photo_id
                    )
                  )
                GROUP BY COALESCE(mapped.fingerprint_id, t.address)
                """,
                period_params,
            )
            counts = {
                row[0]: (int(row[1]), int(row[2]))
                for row in cur.fetchall()
            }

            # Every fingerprint, archived ones included: an archived fingerprint
            # still recognises photos, and those must keep their name.
            cur.execute(
                """
                SELECT f.fingerprint_id, f.display_name, f.active,
                       d.simple_address, d.legal_address
                FROM public.fingerprints AS f
                LEFT JOIN public.address_fingerprints AS af
                       ON af.fingerprint_id = f.fingerprint_id AND af.active
                LEFT JOIN public.address_directory AS d
                       ON d.address_id = af.address_id AND d.active
                """
            )
            rows = cur.fetchall()

    items: list[dict] = []
    listed: set[str] = set()
    inactive: set[str] = set()
    known: dict[str, str] = {}

    for row in rows:
        fingerprint_id = row[0]
        name = fingerprints.resolve_name(row[1], row[3], row[4], fingerprint_id)

        known[fingerprint_id] = name

        if not row[2]:
            # Hidden/archived fingerprints never enter the address panel, even
            # if a photo was recognised as them before they were hidden.
            inactive.add(fingerprint_id)
            continue

        listed.add(fingerprint_id)
        count, period_count = counts.get(fingerprint_id, (0, 0))
        items.append(
            {
                "address": fingerprint_id,
                "name": name,
                "simple_address": row[3],
                "legal_address": row[4],
                "count": count,
                "period_count": period_count,
            }
        )

    for fingerprint_id, (count, period_count) in counts.items():
        if fingerprint_id in listed or fingerprint_id in inactive:
            continue

        items.append(
            {
                "address": fingerprint_id,
                "name": known.get(fingerprint_id, fingerprint_id),
                "simple_address": None,
                "legal_address": None,
                "count": count,
                "period_count": period_count,
            }
        )

    # The panel shows names, so it is ordered by them.
    items.sort(key=lambda item: (item["name"].casefold(), item["address"]))

    return items[:limit]


def stats(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = "upload",
) -> dict:
    """
    Counts for the status bar at the bottom of the window.

    `photos`/`videos` and `last_*` are all-time. `period_photos`/`period_videos`
    repeat the counts with the caller's date range. `addresses` counts the
    addresses that actually received a HYBRID verdict (or a manual override),
    not every row of the address directory.
    """

    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be 'upload' or 'capture'")

    date_column = "created_at" if date_mode == "upload" else "taken_at"
    period_parts: list[str] = []
    period_params: list[object] = []

    if date_from:
        period_parts.append(f"{date_column} >= %s::date")
        period_params.append(date_from)

    if date_to:
        period_parts.append(f"{date_column} < (%s::date + interval '1 day')")
        period_params.append(date_to)

    period_sql = " AND ".join(period_parts) or "TRUE"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    (SELECT count(*) FROM public.photos),
                    (SELECT count(*) FROM public.photos WHERE """ + period_sql + """),
                    (SELECT count(DISTINCT client) FROM public.photo_qwen
                      WHERE client IS NOT NULL AND client <> ''),
                    (SELECT max(created_at) FROM public.photos)
                """,
                period_params,
            )
            row = cur.fetchone()

            # Recognised addresses: a HYBRID final id or a manual override.
            # The same mapping as the address panel keeps the footer in sync.
            cur.execute(
                """
                SELECT count(DISTINCT COALESCE(mapped.fingerprint_id, t.address))
                FROM (""" + _PHOTO_SELECT + """) AS t
                LEFT JOIN public.photo_address_overrides AS ov
                       ON ov.photo_id = t.photo_id
                LEFT JOIN LATERAL (
                    SELECT f.fingerprint_id
                    FROM public.address_fingerprints AS f
                    JOIN public.fingerprints AS reg
                      ON reg.fingerprint_id = f.fingerprint_id
                     AND reg.active
                    WHERE f.address_id = ov.address_id
                      AND f.active
                    ORDER BY f.fingerprint_id
                    LIMIT 1
                ) AS mapped ON TRUE
                WHERE COALESCE(mapped.fingerprint_id, t.address) IS NOT NULL
                  AND COALESCE(mapped.fingerprint_id, t.address) <> ''
                  AND (
                    EXISTS (
                        SELECT 1 FROM public.hybrid_results AS hr
                        WHERE hr.photo_id = t.photo_id
                          AND hr.status = 'DONE'
                          AND hr.hybrid_final_id IS NOT NULL
                    )
                    OR EXISTS (
                        SELECT 1 FROM public.photo_address_overrides AS ov2
                        WHERE ov2.photo_id = t.photo_id
                    )
                  )
                """
            )
            addresses = int(cur.fetchone()[0])

            cur.execute("SELECT to_regclass('public.video_assets')")
            has_video_table = cur.fetchone()[0] is not None

            if has_video_table:
                # Videos have no EXIF capture date: their period always uses
                # the registration time.
                video_parts: list[str] = []
                video_params: list[object] = []

                if date_from:
                    video_parts.append("created_at >= %s::date")
                    video_params.append(date_from)

                if date_to:
                    video_parts.append("created_at < (%s::date + interval '1 day')")
                    video_params.append(date_to)

                video_period_sql = " AND ".join(video_parts) or "TRUE"
                cur.execute(
                    "SELECT count(*), max(created_at), "
                    "count(*) FILTER (WHERE " + video_period_sql + ") "
                    "FROM public.video_assets",
                    video_params,
                )
                video_count, last_video_at, period_videos = cur.fetchone()
            else:
                video_count, last_video_at, period_videos = 0, None, 0

    return {
        "photos": int(row[0]),
        "videos": int(video_count),
        "period_photos": int(row[1]),
        "period_videos": int(period_videos),
        "addresses": addresses,
        "clients": int(row[2]),
        "last_photo_at": row[3],
        "last_video_at": last_video_at,
    }


def get_photo_address_override(photo_id: str) -> dict | None:
    """Manual legal-address override of one photo (None when not set)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT o.address_id, d.legal_address, d.simple_address,
                       o.updated_at
                FROM public.photo_address_overrides AS o
                JOIN public.address_directory AS d
                  ON d.address_id = o.address_id
                WHERE o.photo_id = %s
                """,
                (photo_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "address_id": int(row[0]),
        "legal_address": row[1],
        "simple_address": row[2],
        "updated_at": row[3],
    }


def set_photo_address_override(photo_id: str, address_id: int) -> dict | None:
    """Create or replace the manual address of one photo."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photo_address_overrides (photo_id, address_id)
                VALUES (%s, %s)
                ON CONFLICT (photo_id)
                DO UPDATE SET
                    address_id = EXCLUDED.address_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING address_id
                """,
                (photo_id, int(address_id)),
            )
            row = cur.fetchone()

    return get_photo_address_override(photo_id) if row is not None else None


def clear_photo_address_override(photo_id: str) -> bool:
    """Remove the manual override; recognition data stays untouched."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM public.photo_address_overrides
                WHERE photo_id = %s
                RETURNING photo_id
                """,
                (photo_id,),
            )
            return cur.fetchone() is not None


def suggest_terms(term: str, *, limit: int = 8) -> list[dict]:
    """
    Search-bar suggestions from existing QWEN values.

    Matches tags, clients, brands and categories by substring (ILIKE) or
    trigram similarity (pg_trgm), so a slightly misspelled word still finds a
    real tag. Prefix matches rank first, then similarity, then usage count.
    """

    like = f"%{term}%"
    prefix = f"{term}%"

    sql = """
        WITH values AS (
            SELECT 'tag' AS kind, tag AS value
            FROM public.photo_qwen AS q
            CROSS JOIN LATERAL jsonb_array_elements_text(
                CASE WHEN jsonb_typeof(q.tags) = 'array' THEN q.tags END
            ) AS tag
            WHERE tag <> ''
            UNION ALL
            SELECT 'client', client FROM public.photo_qwen
            WHERE client IS NOT NULL AND client <> ''
            UNION ALL
            SELECT 'brand', brand FROM public.photo_qwen
            WHERE brand IS NOT NULL AND brand <> ''
            UNION ALL
            SELECT 'category', category FROM public.photo_qwen
            WHERE category IS NOT NULL AND category <> ''
            UNION ALL
            SELECT 'address', simple_address FROM public.address_directory
            WHERE active AND simple_address <> ''
            UNION ALL
            SELECT 'address', legal_address FROM public.address_directory
            WHERE active AND legal_address <> ''
        )
        SELECT value, min(kind) AS kind, count(*) AS uses
        FROM values
        WHERE value ILIKE %s OR value %% %s
        GROUP BY value
        ORDER BY (lower(value) LIKE lower(%s)) DESC,
                 similarity(value, %s) DESC,
                 uses DESC,
                 lower(value)
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (like, term, prefix, term, limit))
            return [
                {"value": row[0], "kind": row[1], "uses": int(row[2])}
                for row in cur.fetchall()
            ]


def list_clients(*, limit: int = 100) -> list[dict]:
    """
    Distinct QWEN clients with photo counts.

    Aliased raw values are folded into their canonical client (client_aliases).
    """

    sql = (
        "SELECT COALESCE(a.canonical, t.client) AS client, count(*) AS count "
        "FROM (" + _PHOTO_SELECT + ") AS t "
        "LEFT JOIN public.client_aliases AS a "
        "       ON a.alias = t.client AND a.kind = 'client' "
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


def list_client_aliases(kind: str = "client") -> list[dict]:
    """
    One alias dictionary. `kind` is 'client' or 'brand' (schema/035).

    Brands are normalised exactly like clients: QWEN invents strings for both.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT alias, canonical, kind FROM public.client_aliases "
                "WHERE kind = %s ORDER BY lower(alias)",
                (kind,),
            )
            return [
                {"alias": row[0], "canonical": row[1], "kind": row[2]}
                for row in cur.fetchall()
            ]


def upsert_client_alias(
    alias: str,
    canonical: str,
    *,
    kind: str = "client",
    actor: str | None = None,
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT canonical FROM public.client_aliases "
                "WHERE kind = %s AND alias = %s",
                (kind, alias),
            )
            row = cur.fetchone()
            old = row[0] if row is not None else None

            cur.execute(
                """
                INSERT INTO public.client_aliases (alias, canonical, kind)
                VALUES (%s, %s, %s)
                ON CONFLICT (kind, alias) DO UPDATE
                    SET canonical = EXCLUDED.canonical
                """,
                (alias, canonical, kind),
            )

            _record_alias_audit(
                cur,
                actor=actor,
                alias=alias,
                kind=kind,
                canonical_old=old,
                canonical_new=canonical,
                action="update" if old is not None else "create",
            )

    return {"alias": alias, "canonical": canonical, "kind": kind}


def delete_client_alias(
    alias: str,
    *,
    kind: str = "client",
    actor: str | None = None,
) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT canonical FROM public.client_aliases "
                "WHERE kind = %s AND alias = %s",
                (kind, alias),
            )
            row = cur.fetchone()

            if row is None:
                return False

            cur.execute(
                "DELETE FROM public.client_aliases WHERE kind = %s AND alias = %s",
                (kind, alias),
            )
            deleted = cur.rowcount == 1

            if deleted:
                _record_alias_audit(
                    cur,
                    actor=actor,
                    alias=alias,
                    kind=kind,
                    canonical_old=row[0],
                    canonical_new=None,
                    action="delete",
                )

            return deleted


def _record_alias_audit(
    cur, *, actor, alias, kind, canonical_old, canonical_new, action
) -> None:
    cur.execute(
        """
        INSERT INTO public.client_alias_audit
            (actor, alias, kind, canonical_old, canonical_new, action)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (actor, alias, kind, canonical_old, canonical_new, action),
    )


def list_client_alias_audit(
    *, limit: int = 100, kind: str | None = None
) -> list[dict]:
    limit = max(1, min(int(limit), 500))

    sql = (
        "SELECT audit_id, actor, alias, canonical_old, canonical_new, "
        "action, created_at, COALESCE(kind, 'client') "
        "FROM public.client_alias_audit"
    )
    params: list[object] = []

    if kind is not None:
        # Старые записи не имеют kind и относятся к клиентам.
        sql += " WHERE COALESCE(kind, 'client') = %s"
        params.append(kind)

    sql += " ORDER BY audit_id DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [
        {
            "audit_id": int(row[0]),
            "actor": row[1],
            "alias": row[2],
            "canonical_old": row[3],
            "canonical_new": row[4],
            "action": row[5],
            "created_at": row[6],
            "kind": row[7],
        }
        for row in rows
    ]


def list_qwen_client_names() -> list[dict]:
    """Distinct client/brand strings QWEN produced, alphabetical, with counts."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT kind, name, count(*) AS n
                FROM (
                    SELECT 'client' AS kind, client AS name
                    FROM public.photo_qwen WHERE client IS NOT NULL AND client <> ''
                    UNION ALL
                    SELECT 'brand' AS kind, brand AS name
                    FROM public.photo_qwen WHERE brand IS NOT NULL AND brand <> ''
                ) AS t
                GROUP BY kind, name
                ORDER BY lower(name), kind
                """
            )
            return [
                {"kind": row[0], "name": row[1], "count": int(row[2])}
                for row in cur.fetchall()
            ]


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


def list_collections(user_id: str | None = None) -> list[dict]:
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
    """
    params: list[object] = []

    # A user identity scopes the list to its owner; None (service token / auth
    # disabled) keeps the system-wide view.
    if user_id is not None:
        sql += " WHERE c.user_id = %s"
        params.append(user_id)

    sql += " ORDER BY lower(c.name)"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_collection_row(row) for row in cur.fetchall()]


def get_collection(collection_id: int, user_id: str | None = None) -> dict | None:
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
    params: list[object] = [collection_id]

    if user_id is not None:
        sql += " AND c.user_id = %s"
        params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()

    return _collection_row(row) if row is not None else None


def create_collection(
    *,
    name: str,
    kind: str = "Моя",
    client: str | None = None,
    scope: str = "photos",
    user_id: str | None = None,
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.collections (name, kind, client, scope, user_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING collection_id
                """,
                (name, kind, client, scope, user_id),
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


def delete_collection(collection_id: int, user_id: str | None = None) -> bool:
    sql = "DELETE FROM public.collections WHERE collection_id = %s"
    params: list[object] = [collection_id]

    if user_id is not None:
        sql += " AND user_id = %s"
        params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
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


def photo_sources(photo_ids: list[str]) -> dict[str, dict]:
    """
    {photo_id: {source_path, filename}} for the registered ids.

    One query for a whole selection: the ZIP download needs many rows at once.
    Unknown ids are simply absent from the result.
    """

    ids = [item for item in photo_ids if item]

    if not ids:
        return {}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo_id, source_path, filename "
                "FROM public.photos WHERE photo_id = ANY(%s)",
                (ids,),
            )
            rows = cur.fetchall()

    return {
        row[0]: {"source_path": row[1], "filename": row[2]}
        for row in rows
    }


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


def list_saved_searches(user_id: str | None = None) -> list[dict]:
    sql = """
        SELECT search_id, name, filters, created_at
        FROM public.saved_searches
    """
    params: list[object] = []

    if user_id is not None:
        sql += " WHERE user_id = %s"
        params.append(user_id)

    sql += " ORDER BY lower(name)"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_saved_search_row(row) for row in cur.fetchall()]


def create_saved_search(
    *,
    name: str,
    filters: dict,
    user_id: str | None = None,
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.saved_searches (name, filters, user_id)
                VALUES (%s, %s, %s)
                RETURNING search_id, name, filters, created_at
                """,
                (name, Json(filters or {}), user_id),
            )
            return _saved_search_row(cur.fetchone())


def delete_saved_search(search_id: int, user_id: str | None = None) -> bool:
    sql = "DELETE FROM public.saved_searches WHERE search_id = %s"
    params: list[object] = [search_id]

    if user_id is not None:
        sql += " AND user_id = %s"
        params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
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
