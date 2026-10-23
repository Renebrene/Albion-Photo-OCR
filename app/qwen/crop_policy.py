"""
Which billboard crops QWEN should read.

Detection may find two billboards in one frame. Most photos need only the
largest crop; the second one is useful only where two different banners stand
next to each other. Those places are known addresses, not a property of the
photo, so the list is configuration:

    SCENE_QWEN_MULTI_CROP_ADDRESSES=193,164,211

Address ids come from the address directory. When the list is empty the old
behaviour is kept (every detected crop is analysed), so enabling the policy is
an explicit act. A photo whose address is unknown also stays on one crop — the
safe default, because the list exists precisely to mark the exceptions.
"""

from __future__ import annotations

import os

from app.ingest.database import get_connection


def multi_crop_addresses() -> set[int]:
    """Address ids that must keep both crops; empty set = policy disabled."""

    raw = os.getenv("SCENE_QWEN_MULTI_CROP_ADDRESSES", "").strip()

    if not raw:
        return set()

    result: set[int] = set()

    for part in raw.split(","):
        try:
            value = int(part.strip())
        except ValueError:
            continue

        if value > 0:
            result.add(value)

    return result


def photo_address_id(photo_id: str) -> int | None:
    """
    Address of the photo's latest verdict (HYBRID, then DINO).

    Read-only and best-effort: a missing verdict simply returns None.
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT af.address_id
                    FROM public.hybrid_results AS h
                    JOIN public.address_fingerprints AS af
                      ON af.fingerprint_id = h.hybrid_final_id AND af.active
                    JOIN public.fingerprints AS f
                      ON f.fingerprint_id = af.fingerprint_id AND f.active
                    WHERE h.photo_id = %s
                    ORDER BY h.hybrid_run_id DESC
                    LIMIT 1
                    """,
                    (photo_id,),
                )
                row = cur.fetchone()

                if row is not None:
                    return int(row[0])

                cur.execute(
                    """
                    SELECT af.address_id
                    FROM public.dino_runs AS d
                    JOIN public.address_fingerprints AS af
                      ON af.fingerprint_id = d.dino_best_id AND af.active
                    JOIN public.fingerprints AS f
                      ON f.fingerprint_id = af.fingerprint_id AND f.active
                    WHERE d.photo_id = %s
                      AND d.status = 'DONE'
                    ORDER BY d.finished_at DESC NULLS LAST, d.run_id DESC
                    LIMIT 1
                    """,
                    (photo_id,),
                )
                row = cur.fetchone()

                return int(row[0]) if row is not None else None
    except Exception:  # noqa: BLE001 - policy must never break QWEN
        return None


def select_crops(
    photo_id: str,
    crop_paths: list[str],
    *,
    addresses: set[int] | None = None,
    address_id: int | None = None,
) -> list[str]:
    """
    Keep every crop only for the configured addresses.

    *addresses* / *address_id* are injectable for tests; by default they come
    from the environment and the database.
    """

    if len(crop_paths) <= 1:
        return list(crop_paths)

    allowed = multi_crop_addresses() if addresses is None else addresses

    if not allowed:
        # Policy not configured: preserve the previous behaviour.
        return list(crop_paths)

    if address_id is None:
        address_id = photo_address_id(photo_id)

    return list(crop_paths) if address_id in allowed else list(crop_paths[:1])
