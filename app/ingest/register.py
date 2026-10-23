from __future__ import annotations

import re
from dataclasses import dataclass

from app.ingest.identity_v2 import IDENTITY_SCHEME, LEGACY_SCHEME

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class PhotoRecord:
    """
    Registered representation of one physical source photo.

    The source file itself is never modified by registration.
    For MPO files, frame 0 remains part of the original source object.
    """

    photo_id: str
    source_path: str
    filename: str

    # Content SHA-256. None for records registered under metadata-v1, which
    # deliberately does not read the file body; those carry identity_hash.
    sha256: str | None

    container_format: str
    frame_count: int

    width: int
    height: int

    # Physical size of the source file; used to skip an already-registered
    # file without hashing it again.
    size_bytes: int | None = None

    # EXIF capture date ("YYYY-MM-DD HH:MM:SS"), None when the file has none.
    taken_at: str | None = None

    # Metadata identity (schema/048). Legacy rows may carry identity_hash
    # after a backfill while their photo_id remains content-based.
    identity_hash: str | None = None
    identity_scheme: str = LEGACY_SCHEME


def register_photo(
    *,
    photo_id: str,
    source_path: str,
    filename: str,
    sha256: str,
    container_format: str,
    frame_count: int,
    width: int,
    height: int,
    size_bytes: int | None = None,
    taken_at: str | None = None,
) -> PhotoRecord:
    """
    Assemble validated results from the INGEST stages
    into one immutable photo registration record.

    This function does not access or modify the source file.
    """

    if not photo_id:
        raise ValueError("photo_id is required")

    if not source_path:
        raise ValueError("source_path is required")

    if not filename:
        raise ValueError("filename is required")

    if not sha256:
        raise ValueError("sha256 is required")

    if container_format not in {"JPEG", "MPO"}:
        raise ValueError(
            f"Unsupported container format: {container_format}"
        )

    if frame_count < 1:
        raise ValueError("frame_count must be >= 1")

    if width < 1 or height < 1:
        raise ValueError("Invalid image dimensions")

    if size_bytes is not None and size_bytes < 0:
        raise ValueError("size_bytes must be >= 0")

    return PhotoRecord(
        photo_id=photo_id,
        source_path=source_path,
        filename=filename,
        sha256=sha256,
        container_format=container_format,
        frame_count=frame_count,
        width=width,
        height=height,
        size_bytes=size_bytes,
        taken_at=taken_at,
    )


def register_photo_metadata(
    *,
    photo_id: str,
    source_path: str,
    filename: str,
    identity_hash: str,
    container_format: str,
    frame_count: int,
    width: int,
    height: int,
    size_bytes: int | None = None,
    taken_at: str | None = None,
) -> PhotoRecord:
    """
    Assemble a record registered under the metadata-v1 identity scheme.

    No content SHA is taken: the id comes from EXIF + file size. The record
    keeps identity_hash so the database can find copies without reading
    either file again.
    """

    if not photo_id:
        raise ValueError("photo_id is required")

    if not source_path or not filename:
        raise ValueError("source_path and filename are required")

    if not _HASH_RE.fullmatch(identity_hash):
        raise ValueError("identity_hash must be 64 lowercase hex characters")

    if container_format not in {"JPEG", "MPO"}:
        raise ValueError(f"Unsupported container format: {container_format}")

    if frame_count < 1:
        raise ValueError("frame_count must be >= 1")

    if width < 1 or height < 1:
        raise ValueError("Invalid image dimensions")

    if size_bytes is not None and size_bytes < 0:
        raise ValueError("size_bytes must be >= 0")

    return PhotoRecord(
        photo_id=photo_id,
        source_path=source_path,
        filename=filename,
        sha256=None,
        container_format=container_format,
        frame_count=frame_count,
        width=width,
        height=height,
        size_bytes=size_bytes,
        taken_at=taken_at,
        identity_hash=identity_hash,
        identity_scheme=IDENTITY_SCHEME,
    )
