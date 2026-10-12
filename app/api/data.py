"""
Module "Данные" helpers: metadata export and storage maintenance.

Read-only: only SELECTs and filesystem *stats* (no deletes, no writes).
Export covers registered photos plus their QWEN metadata; it never exposes
absolute source paths (only the filename is kept).
"""

from __future__ import annotations

import csv
import io
import json

from app.api.config import FINGERPRINTS_ROOT, PREVIEW_ROOT
from app.ingest.database import get_connection

# Columns produced by export_rows / CSV, in order.
EXPORT_COLUMNS = (
    "photo_id",
    "filename",
    "width",
    "height",
    "container_format",
    "created_at",
    "address",
    "client",
    "brand",
    "category",
    "description",
    "tags",
)

_EXPORT_SQL = """
    SELECT
        p.photo_id,
        p.filename,
        p.width,
        p.height,
        p.container_format,
        p.created_at,
        COALESCE(
            (
                SELECT h.hybrid_final_id
                FROM public.hybrid_results AS h
                WHERE h.photo_id = p.photo_id AND h.status = 'DONE'
                ORDER BY h.finished_at DESC NULLS LAST,
                         h.hybrid_run_id DESC
                LIMIT 1
            ),
            (
                SELECT r.dino_best_id
                FROM public.dino_runs AS r
                WHERE r.photo_id = p.photo_id AND r.status = 'DONE'
                  AND r.dino_best_id IS NOT NULL
                ORDER BY r.finished_at DESC NULLS LAST, r.run_id DESC
                LIMIT 1
            )
        ) AS address,
        q.client AS client,
        q.brand AS brand,
        q.category AS category,
        q.description AS description,
        q.tags AS tags
    FROM public.photos AS p
    LEFT JOIN public.photo_qwen AS q ON q.photo_id = p.photo_id
    ORDER BY p.photo_id
"""


def export_rows() -> list[dict]:
    """Registered photos + recognition/QWEN metadata, ordered by photo_id."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_EXPORT_SQL)
            rows = cur.fetchall()

    return [
        {
            "photo_id": row[0],
            "filename": row[1],
            "width": row[2],
            "height": row[3],
            "container_format": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "address": row[6],
            "client": row[7],
            "brand": row[8],
            "category": row[9],
            "description": row[10],
            "tags": row[11] if isinstance(row[11], list) else None,
        }
        for row in rows
    ]


def to_csv(rows: list[dict]) -> str:
    """Render export rows as CSV (tags serialized as a JSON string)."""

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()

    for row in rows:
        item = dict(row)
        if item.get("tags") is not None:
            item["tags"] = json.dumps(item["tags"], ensure_ascii=False)
        writer.writerow(item)

    return buffer.getvalue()


def _dir_stats(root) -> dict:
    files = 0
    total = 0

    if root.is_dir():
        for entry in root.rglob("*"):
            if entry.is_file():
                files += 1
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass

    return {"path": str(root), "files": files, "bytes": total}


def storage_stats() -> dict:
    """Counts/sizes for storage maintenance (read-only)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    (SELECT count(*) FROM public.photos),
                    (SELECT count(*) FROM public.photo_qwen),
                    (SELECT count(*) FROM public.photo_previews),
                    (SELECT count(*) FROM public.dino_batches),
                    (SELECT count(*) FROM public.hybrid_runs),
                    (SELECT count(*) FROM public.job_queue),
                    pg_database_size(current_database())
                """
            )
            row = cur.fetchone()

    return {
        "rows": {
            "photos": int(row[0]),
            "photo_qwen": int(row[1]),
            "photo_previews": int(row[2]),
            "dino_batches": int(row[3]),
            "hybrid_runs": int(row[4]),
            "job_queue": int(row[5]),
        },
        "database_bytes": int(row[6]),
        "previews": _dir_stats(PREVIEW_ROOT),
        "fingerprints": _dir_stats(FINGERPRINTS_ROOT),
    }
