"""
Metadata identity for photos (scheme "metadata-v1").

The current photo_id is derived from SHA-256 of the whole file, which costs a
full read. The camera already writes a key that is stable across copies and
renames: body serial, capture time with hundredths, and the exact byte size.

Measured on 1558 photos (docs/identity_shadow.md):

* `(serial, DateTimeOriginal, SubSecTimeOriginal, size)` had 29 repeated
  groups, and every group was a byte-identical copy; there were no collisions
  with different content.
* Without `size` there was already one collision with different content, so
  the size is part of the key.
* 12 files have no EXIF at all; those must keep the content-SHA identity.

This module only computes the identity. Nothing here changes registration:
the shadow mode logs both ids so the scheme can be verified on a real corpus
before it is switched on.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass

PHOTO_ID_PREFIX = "PH"
PHOTO_ID_HASH_LENGTH = 24
IDENTITY_SCHEME = "metadata-v1"
LEGACY_SCHEME = "legacy-content-sha256"


def active_scheme() -> str:
    """
    Which identity scheme INGEST uses.

    Default is the legacy content SHA: switching must be an explicit act after
    the shadow log and the schema migration (docs/identity_shadow.md). An
    unknown value is rejected instead of silently falling back.
    """

    raw = os.getenv("SCENE_IDENTITY_SCHEME", "").strip().lower()

    if raw in {"", "sha256", "legacy", "legacy-content-sha256"}:
        return LEGACY_SCHEME

    if raw in {"metadata", "metadata-v1"}:
        return IDENTITY_SCHEME

    raise ValueError(
        "SCENE_IDENTITY_SCHEME must be sha256 or metadata-v1, "
        f"got {raw!r}"
    )


@dataclass(frozen=True)
class MetadataIdentity:
    """Canonical metadata identity of one physical file."""

    identity_hash: str
    photo_id: str
    serial: str
    taken_at: str
    subsec: str
    size_bytes: int

    @property
    def complete(self) -> bool:
        """
        True when every part of the key is present.

        An incomplete key is not rejected: it is deterministic and can be
        compared in the shadow log, but the switch must fall back to the
        content SHA instead of trusting it.
        """

        return bool(self.serial and self.taken_at and self.subsec)


def canonical_payload(
    serial: object,
    taken_at: object,
    subsec: object,
    size_bytes: object,
) -> bytes:
    """
    Canonical JSON tuple: the order and formatting define the identity.

    Values are normalised to strings; the file name and directory are
    deliberately absent, so renaming or copying a file does not change its id.
    """

    payload = [
        str(serial or "").strip(),
        str(taken_at or "").strip(),
        str(subsec or "").strip(),
        int(size_bytes or 0),
    ]

    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def metadata_identity_hash(
    serial: object,
    taken_at: object,
    subsec: object,
    size_bytes: object,
) -> str:
    """SHA-256 of the canonical tuple; this is not a hash of file contents."""

    return hashlib.sha256(
        canonical_payload(serial, taken_at, subsec, size_bytes)
    ).hexdigest()


def create_metadata_identity(
    serial: object,
    taken_at: object,
    subsec: object,
    size_bytes: object,
) -> MetadataIdentity:
    """Build the id used by the metadata-v1 scheme."""

    identity_hash = metadata_identity_hash(serial, taken_at, subsec, size_bytes)

    return MetadataIdentity(
        identity_hash=identity_hash,
        photo_id=f"{PHOTO_ID_PREFIX}_{identity_hash[:PHOTO_ID_HASH_LENGTH]}",
        serial=str(serial or "").strip(),
        taken_at=str(taken_at or "").strip(),
        subsec=str(subsec or "").strip(),
        size_bytes=int(size_bytes or 0),
    )
