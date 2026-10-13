"""
Smart search by an uploaded photo (backlog item 2, first increment: photos).

The uploaded image is transient: it is written to a dedicated working folder,
described by the local QWEN vision model and deleted as soon as the job
finishes. Nothing is added to the photo tables - only the job result keeps the
description and the matched photo_ids.

Search backend: the QWEN description of the uploaded image (description,
brand, category, client) plus its tags are matched against the stored QWEN
metadata of the base photos. No second model call is made, so the mapping from
image to search terms stays deterministic: the model that describes the query
image is the same one that described the base.

Inference never runs here: the API stores the file and enqueues MEDIA_SEARCH;
the worker calls describe() and run().
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from app.api.nl_search import MAX_PER_TERM, MAX_TOTAL

MAX_FILE_BYTES = int(os.getenv("SCENE_SEARCH_MAX_BYTES", 25 * 1024 * 1024))

# Deliberately outside SCENE_INBOX: query files are working copies, not photo
# sources, and must never look like INGEST input.
QUERY_DIR = Path(os.getenv("SCENE_SEARCH_QUERY_DIR", "data/media_search"))

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png"}

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_CHUNK = 1024 * 1024

# Stale query files (worker killed mid-job) are pruned opportunistically.
MAX_AGE_SECONDS = 24 * 3600


def sanitize_filename(name: str | None) -> str | None:
    """Return a safe basename with an allowed image extension, or None."""

    base = os.path.basename(name or "").strip()

    if not base:
        return None

    base = _SAFE_CHARS.sub("_", base)

    if base in {"", ".", ".."}:
        return None

    if Path(base).suffix.lower() not in ALLOWED_SUFFIXES:
        return None

    return base


def prune_stale() -> int:
    """Delete query files older than MAX_AGE_SECONDS; returns how many."""

    if not QUERY_DIR.is_dir():
        return 0

    removed = 0
    deadline = time.time() - MAX_AGE_SECONDS

    for entry in QUERY_DIR.iterdir():
        try:
            if entry.is_file() and entry.stat().st_mtime < deadline:
                entry.unlink()
                removed += 1
        except OSError:
            continue

    return removed


def store_query(filename: str | None, stream) -> Path:
    """
    Store one uploaded query image under QUERY_DIR.

    The name is sanitized, the size is bounded and the file is written to a
    unique path (mkstemp, mode 0600) so two uploads can never collide and a
    failed write never leaves a partial file behind. The client's own name is
    only kept as the stem: the file is a short-lived working copy.
    """

    import tempfile

    safe_name = sanitize_filename(filename)

    if safe_name is None:
        raise ValueError("unsupported image name or extension")

    QUERY_DIR.mkdir(parents=True, exist_ok=True)
    prune_stale()

    stem = Path(safe_name).stem
    suffix = Path(safe_name).suffix.lower()

    handle_fd, temp_name = tempfile.mkstemp(
        prefix=f"{stem}_",
        suffix=suffix,
        dir=QUERY_DIR,
    )
    temp_path = Path(temp_name)

    written = 0

    try:
        with os.fdopen(handle_fd, "wb") as handle:
            while True:
                chunk = stream.read(_CHUNK)

                if not chunk:
                    break

                written += len(chunk)

                if written > MAX_FILE_BYTES:
                    raise ValueError("file is too large")

                handle.write(chunk)

        if written == 0:
            raise ValueError("empty file")
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return temp_path


def verify_image(path: Path) -> None:
    """Decode the stored file; a file the decoder rejects is not a query."""

    from PIL import Image

    try:
        with Image.open(path) as image:
            image.verify()

        with Image.open(path) as image:
            image.seek(0)
            image.load()
    except Exception as exc:
        raise ValueError(f"not a decodable image: {exc}") from exc


def delete_query(path: str | Path) -> bool:
    """Remove a query file; missing files are not an error."""

    try:
        Path(path).unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def description_filters(fields: dict) -> dict:
    """
    Turn the QWEN fields of the query image into search filters.

    `q` carries the free-text description; brand/category/client are searched
    as exact metadata matches (the same columns the text search already uses).
    """

    def clean(value: object) -> str | None:
        if not isinstance(value, str):
            return None

        value = value.strip()
        return value or None

    tags = fields.get("tags")
    joined_tags = ""

    if isinstance(tags, list):
        joined_tags = ", ".join(str(tag) for tag in tags if str(tag).strip())

    return {
        "q": clean(fields.get("description")) or joined_tags or None,
        "client": clean(fields.get("client")),
        "brand": clean(fields.get("brand")),
        "category": clean(fields.get("category")),
        "address": None,
    }


def search(filters: dict, *, limit: int = MAX_PER_TERM) -> dict:
    """Run the photo search for already-built filters (read-only)."""

    from app.api import repository

    terms = [
        term
        for term in (
            filters.get("q"),
            filters.get("client"),
            filters.get("brand"),
            filters.get("category"),
        )
        if term
    ]

    seen: dict[str, None] = {}
    truncated = False

    for term in terms:
        items, next_cursor = repository.list_photos(limit=limit, query=term)

        if next_cursor is not None:
            truncated = True

        for item in items:
            seen.setdefault(item.photo_id, None)

            if len(seen) >= MAX_TOTAL:
                truncated = True
                break

        if len(seen) >= MAX_TOTAL:
            break

    return {
        "photo_ids": list(seen),
        "count": len(seen),
        "truncated": truncated,
    }


def describe(path: str | Path, *, model: str | None = None) -> dict:
    """Run the QWEN vision model over the query image (worker only)."""

    from app.qwen.processor import analyze_image, resolve_settings

    config = resolve_settings()
    fields, _raw, seconds = analyze_image(
        str(path),
        model=model or config.get("model"),
        config=config,
    )

    return {"fields": fields, "seconds": seconds}


def run(path: str | Path) -> dict:
    """
    Describe the uploaded image and search the base with that description.

    Returns a serialisable result for the job row: the QWEN fields, the
    filters derived from them and the matched photo_ids.
    """

    described = describe(path)
    fields = described["fields"]
    filters = description_filters(fields)
    result = search(filters)

    return {
        "filters": filters,
        "qwen": fields,
        "qwen_time_sec": round(float(described["seconds"]), 3),
        **result,
    }
