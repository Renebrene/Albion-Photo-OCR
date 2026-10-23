"""
INGEST under the metadata-v1 identity scheme.

This is the parallel path selected by ``SCENE_IDENTITY_SCHEME=metadata-v1``.
It reads only the JPEG header and EXIF: no content SHA and no full decode.
A file without a complete metadata key (serial, capture time with hundredths,
size) falls back to the legacy content-SHA identity, so registration never
guesses an id from partial metadata.

The database side (schema/048) is intentionally separate: this module only
builds a record, exactly like ``pipeline.process_file`` does for the legacy
scheme. Running it without the migration fails loudly in
``metadata_register``.
"""

from __future__ import annotations

from pathlib import Path

from app.ingest.identity import create_identity
from app.ingest.identity_v2 import create_metadata_identity
from app.ingest.integrity import check_file
from app.ingest.metadata_integrity import check_file_metadata
from app.ingest.register import register_photo, register_photo_metadata
from app.ingest.shadow import record_shadow


def process_file_metadata(path: str | Path):
    """
    Process one file for metadata-v1 registration.

    Returns a PhotoRecord; the caller classifies and inserts it. The file is
    read-only throughout.
    """

    path = Path(path)
    integrity = check_file_metadata(path)

    if integrity["integrity_status"] != "VALID":
        raise ValueError(
            f"Integrity check failed for {path}: {integrity['error']}"
        )

    identity = create_metadata_identity(
        integrity.get("exif_serial"),
        integrity.get("taken_at"),
        integrity.get("exif_subsec"),
        integrity.get("size_bytes"),
    )

    if identity.complete:
        return register_photo_metadata(
            photo_id=identity.photo_id,
            source_path=integrity["source_path"],
            filename=integrity["filename"],
            identity_hash=identity.identity_hash,
            container_format=integrity["container_format"],
            frame_count=integrity["frame_count"],
            width=integrity["width"],
            height=integrity["height"],
            size_bytes=integrity["size_bytes"],
            taken_at=integrity["taken_at"],
        )

    # Incomplete metadata: the only trustworthy identity is the content SHA.
    # This is the same read the legacy scheme always performed, but it now
    # happens only for the rare file without the needed EXIF tags.
    deep = check_file(path)

    if deep["integrity_status"] != "VALID":
        raise ValueError(
            f"Integrity check failed for {path}: {deep['error']}"
        )

    legacy = create_identity(deep["sha256"])

    record_shadow(path, legacy.sha256, legacy.photo_id, deep)

    return register_photo(
        photo_id=legacy.photo_id,
        source_path=deep["source_path"],
        filename=deep["filename"],
        sha256=legacy.sha256,
        container_format=deep["container_format"],
        frame_count=deep["frame_count"],
        width=deep["width"],
        height=deep["height"],
        size_bytes=deep["size_bytes"],
        taken_at=deep["taken_at"],
    )
