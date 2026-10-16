"""Queue helpers for photo preview generation."""

from __future__ import annotations

from app.api.config import PREVIEW_ROOT
from app.ingest.database import get_connection, get_registered_photo
from app.jobs.database import enqueue_photo_preview
from app.preview.generator import build_preview_paths


def enqueue_registered_photo(photo_id: str) -> int | None:
    """Queue only when the id belongs to a registered photo."""

    if get_registered_photo(photo_id) is None:
        return None
    return enqueue_photo_preview(photo_id)


def run_photo_preview(photo_id: str) -> dict:
    """Generate SMALL/MIDDLE for one registered photo through the shared pipeline."""

    record = get_registered_photo(photo_id)
    if record is None:
        return {"photo_id": photo_id, "status": "SKIPPED", "reason": "photo_not_registered"}

    from app.preview.pipeline import run

    result = run([record])
    item = result.results[0]
    if not item.ready:
        details = [error for error in (item.small.error, item.middle.error) if error]
        raise RuntimeError(
            f"PREVIEW failed for {photo_id}: " + ("; ".join(details) or "preview is incomplete")
        )
    return {
        "photo_id": photo_id,
        "status": "DONE",
        "ready": True,
        "database_updated": result.database_updated,
        "database_skipped": result.database_skipped,
        "small_action": item.small.action,
        "middle_action": item.middle.action,
        "errors": [],
    }


def enqueue_missing_previews(*, limit: int = 500) -> dict:
    """Queue a bounded page of photos with missing preview rows or files."""

    if not 1 <= limit <= 5000:
        raise ValueError("limit must be between 1 and 5000")
    selected = 0
    queued = 0
    active = 0
    cursor: str | None = None
    while selected < limit:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT p.photo_id, r.small_path, r.middle_path
                       FROM public.photos AS p
                       LEFT JOIN public.photo_previews AS r ON r.photo_id=p.photo_id
                       WHERE (%s::text IS NULL OR p.photo_id > %s)
                       ORDER BY p.photo_id
                       LIMIT %s""",
                    (cursor, cursor, max(100, min(1000, limit * 4))),
                )
                rows = cur.fetchall()
        if not rows:
            break
        cursor = str(rows[-1][0])
        for photo_id, small_path, middle_path in rows:
            paths = build_preview_paths(preview_root=PREVIEW_ROOT, photo_id=str(photo_id))
            small = paths.small
            middle = paths.middle
            # Only inspect the managed deterministic paths; DB paths are ignored.
            complete = (
                bool(small_path and middle_path)
                and small.is_file()
                and middle.is_file()
                and small.stat().st_size > 0
                and middle.is_file()
                and middle.stat().st_size > 0
            )
            if complete:
                continue
            selected += 1
            job_id = enqueue_photo_preview(str(photo_id))
            if job_id is None:
                active += 1
            else:
                queued += 1
            if selected >= limit:
                break
    return {"selected": selected, "queued": queued, "already_active": active}
