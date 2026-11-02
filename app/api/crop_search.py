"""Search stored billboard crops by perceptual hash.

The uploaded layout is treated as a crop: its dHash is compared with every
saved ``photo_regions.crop_phash``. QWEN metadata search stays an independent
source of candidates; results are combined with OR (see media_search.run).
"""

from __future__ import annotations

from pathlib import Path

from app.billboard.phash import distance, file_dhash, file_phash
from app.ingest.database import get_connection

MAX_HASH_MATCHES = 50
# Same-frame threshold from docs/series_merge.md; kept visible in the result.
SAME_FRAME_DISTANCE = 6


def search_by_hash(image_path: str | Path, *, limit: int = MAX_HASH_MATCHES) -> dict:
    """Return the nearest saved crops for one query image."""

    query_hash = file_dhash(image_path)
    query_phash = file_phash(image_path)
    if query_hash is None:
        return {
            "query_hash": None,
            "query_phash": None,
            "matches": [],
            "count": 0,
        }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.photo_id,
                       r.region_id,
                       r.crop_index,
                       r.crop_phash,
                       r.crop_phash_p,
                       r.crop_path,
                       COALESCE(
                           ov.address_id,
                           (
                               SELECT af.address_id
                               FROM public.hybrid_results AS h
                               JOIN public.address_fingerprints AS af
                                 ON af.fingerprint_id = h.hybrid_final_id
                                AND af.active
                               WHERE h.photo_id = r.photo_id
                                 AND h.status = 'DONE'
                               ORDER BY h.finished_at DESC NULLS LAST,
                                        h.hybrid_run_id DESC
                               LIMIT 1
                           )
                       ) AS address_id,
                       ad.legal_address,
                       ad.simple_address
                FROM public.photo_regions AS r
                LEFT JOIN public.photo_address_overrides AS ov
                       ON ov.photo_id = r.photo_id
                LEFT JOIN public.address_directory AS ad
                       ON ad.address_id = COALESCE(
                           ov.address_id,
                           (
                               SELECT af.address_id
                               FROM public.hybrid_results AS h
                               JOIN public.address_fingerprints AS af
                                 ON af.fingerprint_id = h.hybrid_final_id
                                AND af.active
                               WHERE h.photo_id = r.photo_id
                                 AND h.status = 'DONE'
                               ORDER BY h.finished_at DESC NULLS LAST,
                                        h.hybrid_run_id DESC
                               LIMIT 1
                           )
                       )
                WHERE r.kind = 'billboard'
                  AND r.crop_phash IS NOT NULL
                """
            )
            rows = cur.fetchall()

    def unsigned(value: object) -> int:
        current = int(value)
        # Both hashes are stored as signed BIGINT; the hash itself is unsigned.
        return current + (1 << 64) if current < 0 else current

    scored = []
    for row in rows:
        if row[3] is None:
            continue

        dhash_distance = distance(query_hash, unsigned(row[3]))
        phash_distance = (
            distance(query_phash, unsigned(row[4]))
            if query_phash is not None and row[4] is not None
            else None
        )
        combined = (
            round((dhash_distance + phash_distance) / 2)
            if phash_distance is not None
            else dhash_distance
        )
        scored.append((combined, dhash_distance, phash_distance, row))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2] if item[2] is not None else 64,
            str(item[3][0]),
            int(item[3][2] or 0),
        )
    )

    matches = []
    for combined, dhash_distance, phash_distance, row in scored[:limit]:
        (photo_id, region_id, crop_index, _hash, _phash, crop_path,
         address_id, legal, simple) = row
        matches.append(
            {
                "photo_id": str(photo_id),
                "region_id": int(region_id),
                "crop_index": int(crop_index or 0),
                "distance": int(combined),
                "dhash_distance": int(dhash_distance),
                "phash_distance": int(phash_distance) if phash_distance is not None else None,
                "same_frame": combined <= SAME_FRAME_DISTANCE,
                "address_id": int(address_id) if address_id is not None else None,
                "address": legal or simple,
                "crop_path": str(crop_path or ""),
            }
        )

    return {
        "query_hash": int(query_hash),
        "query_phash": int(query_phash) if query_phash is not None else None,
        "same_frame_distance": SAME_FRAME_DISTANCE,
        "matches": matches,
        "count": len(scored),
    }
