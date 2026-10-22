"""Queue helpers for photo preview generation."""

from __future__ import annotations

from app.api.config import ORIGINALS_ROOTS, PREVIEW_ROOT
from app.api.file_access import ORIGINAL_OK, original_availability
from app.ingest.database import get_connection, get_registered_photo
from app.jobs.database import enqueue_photo_preview
from app.preview.generator import build_preview_paths

# Photos looked up per statement when a set of ids is given.
_ID_CHUNK = 500


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

    # Background branch: a ready preview is the trigger for billboard
    # detection. It is best-effort by design - a detection enqueue failure
    # must never fail PREVIEW or touch the main pipeline.
    try:
        from app.billboard.config import resolve_settings as billboard_settings
        from app.jobs.database import enqueue_billboard_detect

        if billboard_settings()["enabled"]:
            enqueue_billboard_detect(photo_id)
    except Exception:  # noqa: BLE001 - additive background work
        pass

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


def preview_files_missing(photo_id: str, small_path, middle_path) -> bool:
    """
    True when the managed SMALL/MIDDLE files for a photo are not both usable.

    Only the deterministic paths built from photo_id are inspected: a path
    stored in the database is never trusted as a file location.
    """

    paths = build_preview_paths(preview_root=PREVIEW_ROOT, photo_id=str(photo_id))
    small = paths.small
    middle = paths.middle

    try:
        return not (
            bool(small_path and middle_path)
            and small.is_file()
            and middle.is_file()
            and small.stat().st_size > 0
            and middle.stat().st_size > 0
        )
    except OSError:
        return True


def _enqueue_for_ids(photo_ids: list[str], limit: int) -> dict:
    """
    Re-create previews for an explicit set of photo_ids.

    The source folder is never scanned: the original path comes from the
    database row. A photo whose original is unavailable is reported in
    `originals_missing` instead of being queued, because such a job could
    only fail — the photo row itself is left untouched (see
    docs/preview.txt: "оригинал недоступен, используйте превью").
    """

    ordered = sorted({str(value) for value in photo_ids})
    selected = 0
    queued = 0
    active = 0
    unavailable = 0

    for start in range(0, len(ordered), _ID_CHUNK):
        chunk = ordered[start : start + _ID_CHUNK]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT p.photo_id, p.source_path, r.small_path, r.middle_path
                       FROM public.photos AS p
                       LEFT JOIN public.photo_previews AS r ON r.photo_id=p.photo_id
                       WHERE p.photo_id = ANY(%s)
                       ORDER BY p.photo_id""",
                    (chunk,),
                )
                rows = cur.fetchall()
        for photo_id, source_path, small_path, middle_path in rows:
            if not preview_files_missing(str(photo_id), small_path, middle_path):
                continue
            if original_availability(source_path, ORIGINALS_ROOTS) != ORIGINAL_OK:
                unavailable += 1
                continue
            selected += 1
            job_id = enqueue_photo_preview(str(photo_id))
            if job_id is None:
                active += 1
            else:
                queued += 1
            if selected >= limit:
                return {
                    "selected": selected,
                    "queued": queued,
                    "already_active": active,
                    "originals_missing": unavailable,
                }

    return {
        "selected": selected,
        "queued": queued,
        "already_active": active,
        "originals_missing": unavailable,
    }


def enqueue_missing_previews(
    *,
    limit: int = 500,
    photo_ids: list[str] | None = None,
) -> dict:
    """
    Queue a bounded page of photos with missing preview rows or files.

    Without *photo_ids* the whole table is walked in pages. With *photo_ids*
    only those photos are considered — this is the "пересоздать превью по
    photo_id" path used after preview files were cleared or lost; it also
    reports how many of them cannot be rebuilt because the original is gone.
    """

    if not 1 <= limit <= 5000:
        raise ValueError("limit must be between 1 and 5000")
    if photo_ids is not None:
        return _enqueue_for_ids(list(photo_ids), limit)

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
            if not preview_files_missing(str(photo_id), small_path, middle_path):
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
