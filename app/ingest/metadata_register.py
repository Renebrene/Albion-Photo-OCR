"""
Database registration for the metadata-v1 identity scheme.

This is the parallel INGEST path: legacy rows keep their SHA-derived photo_id
and content hash, while new rows are identified by EXIF + size. The two live
side by side because ``photos.identity_hash`` is nullable and ``sha256``
became nullable in schema/048.

A metadata key can, in theory, collide (two different frames with the same
serial, second and byte size). Before a duplicate is accepted as EXISTING,
both files are hashed once and compared; a difference is reported as
CONFLICT, so no photo is silently merged.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

from app.ingest.database import get_connection
from app.ingest.integrity import calculate_sha256
from app.ingest.register import PhotoRecord


def _same_content(new_path: str, existing_path: str | None) -> bool:
    """
    Compare two files by SHA-256 (only called for identity duplicates).

    A missing existing file cannot be compared; the identity match is then
    accepted, because the alternative is refusing every re-ingest of photos
    moved to another volume.
    """

    try:
        new_sha = calculate_sha256(Path(new_path))
    except OSError:
        return False

    if not existing_path:
        return True

    try:
        old_sha = calculate_sha256(Path(existing_path))
    except OSError:
        print(
            f"[metadata-register] existing file unavailable, "
            f"identity match accepted: {existing_path}",
            file=sys.stderr,
        )
        return True

    return new_sha == old_sha


def classify_metadata(
    records: list[PhotoRecord],
) -> dict[str, list[PhotoRecord]]:
    """NEW / EXISTING / CONFLICT for metadata-v1 records (no writes)."""

    result: dict[str, list[PhotoRecord]] = {
        "NEW": [],
        "EXISTING": [],
        "CONFLICT": [],
    }

    if not records:
        return result

    photo_ids = [record.photo_id for record in records]
    hashes = [record.identity_hash for record in records if record.identity_hash]

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT photo_id, identity_hash, sha256, source_path
                    FROM public.photos
                    WHERE photo_id = ANY(%s)
                       OR identity_hash = ANY(%s)
                    """,
                    (photo_ids, hashes),
                )
                rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001 - add the migration hint
        if exc.__class__.__name__ == "UndefinedColumn":
            raise RuntimeError(
                "metadata-v1 requires schema/048_photo_identity.sql; "
                "the photos.identity_hash column is missing"
            ) from exc
        raise

    by_id = {row[0]: row for row in rows}
    by_hash = {row[1]: row for row in rows if row[1]}

    for record in records:
        same_id = by_id.get(record.photo_id)
        same_hash = by_hash.get(record.identity_hash) if record.identity_hash else None
        existing = same_id or same_hash

        if existing is None:
            result["NEW"].append(record)
            continue

        existing_id, existing_hash, _existing_sha, existing_path = existing

        if existing_hash and record.identity_hash and existing_hash != record.identity_hash:
            result["CONFLICT"].append(record)
            continue

        if existing_id != record.photo_id:
            # The same photo_id under a different identity, or the same
            # identity under a different photo_id: both indicate a collision
            # or a changed file, never a plain duplicate.
            result["CONFLICT"].append(record)
            continue

        if record.identity_hash and not _same_content(
            record.source_path, existing_path
        ):
            result["CONFLICT"].append(record)
            continue

        result["EXISTING"].append(record)

    return result


def insert_metadata_photos(records: Iterable[PhotoRecord]) -> set[str]:
    """Insert metadata-v1 rows; returns the photo_ids actually inserted."""

    inserted: set[str] = set()

    with get_connection() as conn:
        with conn.cursor() as cur:
            for record in records:
                cur.execute(
                    """
                    INSERT INTO public.photos (
                        photo_id,
                        source_path,
                        filename,
                        sha256,
                        identity_hash,
                        identity_scheme,
                        container_format,
                        frame_count,
                        width,
                        height,
                        size_bytes,
                        taken_at
                    )
                    VALUES (
                        %(photo_id)s,
                        %(source_path)s,
                        %(filename)s,
                        NULL,
                        %(identity_hash)s,
                        'metadata-v1',
                        %(container_format)s,
                        %(frame_count)s,
                        %(width)s,
                        %(height)s,
                        %(size_bytes)s,
                        %(taken_at)s
                    )
                    ON CONFLICT DO NOTHING
                    RETURNING photo_id
                    """,
                    {
                        "photo_id": record.photo_id,
                        "source_path": record.source_path,
                        "filename": record.filename,
                        "identity_hash": record.identity_hash,
                        "container_format": record.container_format,
                        "frame_count": record.frame_count,
                        "width": record.width,
                        "height": record.height,
                        "size_bytes": record.size_bytes,
                        "taken_at": record.taken_at,
                    },
                )
                row = cur.fetchone()

                if row is not None:
                    inserted.add(str(row[0]))

    return inserted


def classify_and_insert_metadata(
    records: list[PhotoRecord],
) -> dict[str, list[PhotoRecord]]:
    """
    Classify and insert, reporting conflicts instead of raising.

    Used by a folder scan: one contradictory file must not stop the rest of
    the folder. The upload path uses the strict `register_new_metadata`.
    """

    result = classify_metadata(records)

    if result["NEW"]:
        candidates = result["NEW"]
        inserted = insert_metadata_photos(candidates)
        result["NEW"] = [
            record for record in candidates if record.photo_id in inserted
        ]
        result["EXISTING"].extend(
            record for record in candidates if record.photo_id not in inserted
        )

    return result


def register_new_metadata(
    records: list[PhotoRecord],
) -> dict[str, list[PhotoRecord]]:
    """
    Register metadata-v1 records.

    CONFLICT aborts the batch before any INSERT, like the legacy path.
    Raced inserts are reclassified as EXISTING.
    """

    result = classify_metadata(records)

    if result["CONFLICT"]:
        conflicts = ", ".join(record.photo_id for record in result["CONFLICT"])
        raise ValueError(f"Metadata identity conflicts detected: {conflicts}")

    if result["NEW"]:
        candidates = result["NEW"]
        inserted = insert_metadata_photos(candidates)
        result["NEW"] = [
            record for record in candidates if record.photo_id in inserted
        ]
        result["EXISTING"].extend(
            record for record in candidates if record.photo_id not in inserted
        )

    return result
