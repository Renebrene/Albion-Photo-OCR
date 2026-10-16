"""
Photo upload into the INGEST inbox.

Safety rules (see the project guidelines):
  * never trust the client path, MIME type or filename — the name is
    sanitized, the path is built from a fixed inbox directory;
  * bound the number and size of uploads;
  * verify the content with a real decoder (the INGEST integrity check);
  * never overwrite an existing inbox file (which may back a registered
    photo), pick a unique name instead.

The uploaded file is stored under SCENE_INBOX and then registered through the
normal INGEST pipeline (SHA-256 → photo_id), so identity semantics are the
same as for CLI ingest.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from app.core.errors import redact_absolute_paths
from app.ingest.database import register_new_photos
from app.ingest.pipeline import process_file

MAX_FILE_BYTES = int(os.getenv("SCENE_UPLOAD_MAX_BYTES", 25 * 1024 * 1024))
MAX_FILES = int(os.getenv("SCENE_UPLOAD_MAX_FILES", 20))

INBOX = Path(os.getenv("SCENE_INBOX", "data/inbox"))

_ALLOWED_SUFFIXES = {".jpg", ".jpeg"}
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_CHUNK = 1024 * 1024


def sanitize_filename(name: str | None) -> str | None:
    """Return a safe basename with an allowed image extension, or None."""

    base = os.path.basename(name or "").strip()

    if not base:
        return None

    base = _SAFE_CHARS.sub("_", base)

    if base in {"", ".", ".."}:
        return None

    if Path(base).suffix.lower() not in _ALLOWED_SUFFIXES:
        return None

    return base


def _unique_destination(filename: str) -> Path:
    """Pick an inbox path that does not overwrite an existing file."""

    INBOX.mkdir(parents=True, exist_ok=True)

    candidate = INBOX / filename

    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    index = 1

    while True:
        candidate = INBOX / f"{stem}__{index}{suffix}"

        if not candidate.exists():
            return candidate

        index += 1


def store_upload(filename: str | None, stream) -> Path:
    """
    Stream one upload into the inbox, enforcing the size limit.

    Writes to a temporary file and atomically publishes it. Raises ValueError
    on an unsafe name, an empty file or a size-limit overflow.
    """

    safe = sanitize_filename(filename)

    if safe is None:
        raise ValueError("unsupported or unsafe filename")

    destination = _unique_destination(safe)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(INBOX), prefix=".upload-", suffix=".part"
    )

    total = 0

    try:
        with os.fdopen(fd, "wb") as handle:
            while True:
                chunk = stream.read(_CHUNK)

                if not chunk:
                    break

                total += len(chunk)

                if total > MAX_FILE_BYTES:
                    raise ValueError("file exceeds the size limit")

                handle.write(chunk)

        if total == 0:
            raise ValueError("empty file")

        os.replace(tmp_path, destination)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    return destination


def ingest_upload(filename: str | None, stream) -> dict:
    """Store + register one upload. Returns a per-file result dict."""

    try:
        path = store_upload(filename, stream)
    except ValueError as exc:
        return {"filename": filename, "error": str(exc)}

    try:
        record = process_file(path)
        classification = register_new_photos([record])
    except ValueError as exc:
        # Invalid image (decoder rejected it) or identity conflict.
        return {"filename": path.name, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - reported per file
        return {"filename": path.name, "error": f"ingest failed: {exc}"}

    if record in classification["NEW"]:
        status = "NEW"
    elif record in classification["EXISTING"]:
        status = "EXISTING"
    else:
        status = "CONFLICT"

    result = {
        "filename": path.name,
        "photo_id": record.photo_id,
        "status": status,
    }
    if status == "NEW":
        try:
            from app.jobs.database import enqueue_photo_preview

            result["preview_job_id"] = enqueue_photo_preview(record.photo_id)
        except Exception as exc:  # noqa: BLE001 - photo registration already committed
            result["preview_enqueue_error"] = redact_absolute_paths(str(exc))
    return result
