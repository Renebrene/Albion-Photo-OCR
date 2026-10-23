"""
Shadow comparison of the two photo identities.

With ``SCENE_IDENTITY_SHADOW=1`` every newly inspected file appends one JSON
line to a local log:

* the current id (from the file content SHA-256), and
* the metadata-v1 id that would be used after the switch.

Nothing is registered differently: photo_id, sha256 and the database are
untouched. The log is how the new scheme is verified on a real corpus before
it becomes the default (docs/identity_shadow.md).

The write is a single ``os.write`` with O_APPEND: INGEST runs files in several
processes, and one short line stays atomic on POSIX. A logging failure must
never fail INGEST, so every error is swallowed and reported on stderr.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TRUTHY = {"1", "true", "yes", "on"}


def shadow_enabled() -> bool:
    """Shadow mode is off unless explicitly enabled."""

    return os.getenv("SCENE_IDENTITY_SHADOW", "0").strip().lower() in TRUTHY


def shadow_log_path() -> Path:
    """Explicit override, else <SCENE_DATA>/logs/identity_shadow.jsonl."""

    raw = os.getenv("SCENE_IDENTITY_SHADOW_LOG", "").strip()

    if raw:
        return Path(raw)

    return Path(os.getenv("SCENE_DATA", "data")) / "logs" / "identity_shadow.jsonl"


def record_shadow(
    source_path: object,
    sha256: str,
    sha_photo_id: str,
    integrity: dict,
) -> bool:
    """
    Append one comparison line; returns False when nothing was written.

    *integrity* is the dict produced by ``check_file`` (it carries
    size_bytes, taken_at, exif_serial, exif_subsec).
    """

    if not shadow_enabled():
        return False

    try:
        from app.ingest.identity_v2 import IDENTITY_SCHEME, create_metadata_identity

        identity = create_metadata_identity(
            integrity.get("exif_serial"),
            integrity.get("taken_at"),
            integrity.get("exif_subsec"),
            integrity.get("size_bytes"),
        )

        line = json.dumps(
            {
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_path": str(source_path),
                "filename": integrity.get("filename"),
                "sha256": sha256,
                "sha_photo_id": sha_photo_id,
                "v2_photo_id": identity.photo_id,
                "v2_hash": identity.identity_hash,
                "scheme": IDENTITY_SCHEME,
                "complete": identity.complete,
                "serial": identity.serial or None,
                "taken_at": identity.taken_at or None,
                "subsec": identity.subsec or None,
                "size_bytes": identity.size_bytes,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

        path = shadow_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o644,
        )

        try:
            os.write(descriptor, (line + "\n").encode("utf-8"))
        finally:
            os.close(descriptor)

        return True

    except Exception as exc:  # noqa: BLE001 - shadow must never fail INGEST
        print(
            f"[identity-shadow] skipped ({type(exc).__name__}): {exc}",
            file=sys.stderr,
        )
        return False
