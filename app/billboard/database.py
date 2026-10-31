"""
PostgreSQL access for detected billboard regions (public.photo_regions).

Regions are derived data: a repeated detection replaces the rows of one photo
in a single transaction. Crop-level QWEN results live on the same row, so the
full-frame public.photo_qwen path is never overwritten.
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Json

from app.ingest.database import get_connection

_COLUMNS = (
    "region_id, photo_id, kind, crop_index, bbox_x, bbox_y, bbox_w, bbox_h, score, "
    "detector, crop_path, crop_width, crop_height, qwen_status, qwen_fields, "
    "qwen_model, qwen_time_sec, qwen_error, created_at, updated_at"
)


def _row_to_dict(row) -> dict:
    return {
        "region_id": int(row[0]),
        "photo_id": row[1],
        "kind": row[2],
        "crop_index": int(row[3] or 0),
        "bbox_x": int(row[4]),
        "bbox_y": int(row[5]),
        "bbox_w": int(row[6]),
        "bbox_h": int(row[7]),
        "score": float(row[8]),
        "detector": row[9],
        "crop_path": row[10],
        "crop_width": int(row[11]),
        "crop_height": int(row[12]),
        "qwen_status": row[13],
        "qwen_fields": row[14],
        "qwen_model": row[15],
        "qwen_time_sec": row[16],
        "qwen_error": row[17],
        "created_at": row[18],
        "updated_at": row[19],
    }


def replace_regions(photo_id: str, regions: list[dict]) -> list[int]:
    """
    Replace all regions of one photo with *regions* (none = clear).

    Regions must already carry bbox/score/detector/crop fields.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.photo_regions WHERE photo_id = %s",
                (photo_id,),
            )

            region_ids: list[int] = []

            for region in regions:
                cur.execute(
                    """
                    INSERT INTO public.photo_regions (
                        photo_id, kind, crop_index, bbox_x, bbox_y, bbox_w, bbox_h,
                        score, detector, crop_path, crop_width, crop_height,
                        crop_phash, photo_taken_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING region_id
                    """,
                    (
                        photo_id,
                        str(region.get("kind") or "billboard"),
                        int(region.get("crop_index", len(region_ids))),
                        int(region["bbox_x"]),
                        int(region["bbox_y"]),
                        int(region["bbox_w"]),
                        int(region["bbox_h"]),
                        float(region["score"]),
                        str(region["detector"]),
                        str(region["crop_path"]),
                        int(region["crop_width"]),
                        int(region["crop_height"]),
                        region.get("crop_phash"),
                        region.get("photo_taken_at"),
                    ),
                )
                region_ids.append(int(cur.fetchone()[0]))

    return region_ids


def get_region(region_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM public.photo_regions WHERE region_id = %s",  # noqa: S608
                (int(region_id),),
            )
            row = cur.fetchone()

    return _row_to_dict(row) if row is not None else None


def get_billboard_region(photo_id: str) -> dict | None:
    """Primary/largest stored billboard region of a photo."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {_COLUMNS} FROM public.photo_regions
                WHERE photo_id = %s AND kind = 'billboard'
                ORDER BY crop_index, region_id
                LIMIT 1
                """,  # noqa: S608
                (photo_id,),
            )
            row = cur.fetchone()

    return _row_to_dict(row) if row is not None else None


def get_billboard_regions(photo_id: str) -> list[dict]:
    """All detected billboard crop rows, largest/primary first."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM public.photo_regions "
                "WHERE photo_id = %s AND kind = 'billboard' "
                "ORDER BY crop_index, region_id",  # noqa: S608
                (photo_id,),
            )
            rows = cur.fetchall()
    return [_row_to_dict(row) for row in rows]


def list_regions(photo_id: str) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {_COLUMNS} FROM public.photo_regions
                WHERE photo_id = %s
                ORDER BY crop_index, region_id
                """,  # noqa: S608
                (photo_id,),
            )
            rows = cur.fetchall()

    return [_row_to_dict(row) for row in rows]


def get_qwen_frequency_snapshot(*, date_from: str, date_to: str, use_aliases: bool = True) -> dict:
    """Crop-occurrence frequency by client/brand in an inclusive capture range."""

    alias_client = (
        "LEFT JOIN public.client_aliases AS ca "
        "ON ca.kind='client' AND LOWER(ca.alias)=LOWER(q.qwen_fields->>'client') "
        if use_aliases else ""
    )
    alias_brand = (
        "LEFT JOIN public.client_aliases AS ba "
        "ON ba.kind='brand' AND LOWER(ba.alias)=LOWER(q.qwen_fields->>'brand') "
        if use_aliases else ""
    )
    client_name = "COALESCE(ca.canonical, NULLIF(BTRIM(q.qwen_fields->>'client'), ''))" if use_aliases else "NULLIF(BTRIM(q.qwen_fields->>'client'), '')"
    brand_name = "COALESCE(ba.canonical, NULLIF(BTRIM(q.qwen_fields->>'brand'), ''))" if use_aliases else "NULLIF(BTRIM(q.qwen_fields->>'brand'), '')"
    sql = f"""
        WITH crop_observations AS (
            SELECT q.photo_id, q.crop_index,
                   {client_name} AS client_name,
                   {brand_name} AS brand_name
            FROM public.photo_regions AS q
            JOIN public.photos AS p ON p.photo_id=q.photo_id
            {alias_client}
            {alias_brand}
            WHERE q.kind='billboard' AND q.qwen_status='DONE'
              AND COALESCE(q.photo_taken_at,p.taken_at) >= %s::date
              AND COALESCE(q.photo_taken_at,p.taken_at) < (%s::date + interval '1 day')
        ), observations AS (
            SELECT 'client' AS kind, client_name AS canonical_name FROM crop_observations
            UNION ALL
            SELECT 'brand' AS kind, brand_name AS canonical_name FROM crop_observations
        )
        SELECT kind, canonical_name, count(*)
        FROM observations
        WHERE canonical_name IS NOT NULL
        GROUP BY kind, canonical_name
        ORDER BY kind, count(*) DESC, lower(canonical_name)
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql, (date_from, date_to))
            rows = cur.fetchall()
    result = {"client": [], "brand": []}
    for kind, name, count in rows:
        result[kind].append({"name": name, "count": int(count)})
    return result


def mark_qwen_running(region_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.photo_regions
                SET qwen_status = 'RUNNING',
                    qwen_error = NULL,
                    qwen_finished_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE region_id = %s
                """,
                (int(region_id),),
            )


def save_qwen_success(
    region_id: int,
    *,
    fields: dict[str, Any],
    model: str,
    time_sec: float,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.photo_regions
                SET qwen_status = 'DONE',
                    qwen_fields = %s,
                    qwen_model = %s,
                    qwen_time_sec = %s,
                    qwen_error = NULL,
                    qwen_finished_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE region_id = %s
                """,
                (Json(fields), str(model), float(time_sec), int(region_id)),
            )


def save_qwen_failure(region_id: int, error_message: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.photo_regions
                SET qwen_status = 'FAILED',
                    qwen_error = %s,
                    qwen_finished_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE region_id = %s
                """,
                (str(error_message), int(region_id)),
            )
