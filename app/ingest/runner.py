"""
Folder-level INGEST: scan a working folder and register its new photos.

This is the entry point shared by the CLI and the worker job, so a future
filesystem watcher can reuse exactly the same code path:

    folder -> pipeline.run (skip already-registered files)
           -> identity check -> INSERT of the NEW photos

Nothing here modifies the source files and nothing runs from an HTTP request
handler: the API only enqueues the job.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

from app.ingest.database import (
    check_identity_batch,
    insert_photos,
    known_source_files,
)
from app.ingest.integrity import date_in_period, file_date
from app.ingest.pipeline import (
    DATE_MODE_CAPTURE,
    DATE_MODE_UPLOAD,
    DEFAULT_WORKERS,
    run,
    taken_at_date,
)
from app.ingest.video_integrity import check_video_file, discover_videos
from app.ingest.video_register import VideoRecord, register_video, register_video_records
from app.core.errors import redact_absolute_paths
from app.preview.queue import enqueue_registered_photo
from app.preview.video import build_video_poster, default_video_preview_root


def _check_video(path: Path) -> tuple[Path, dict]:
    return path, check_video_file(path)


def _parse_date(value: str | date | None, field: str) -> date | None:
    """Inclusive bound of a scan period; empty means "no bound"."""

    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD)") from exc


def _video_moment(path: Path, facts: dict) -> date | None:
    """Capture date of a probed video, falling back to the file's own date."""

    moment = facts.get("taken_at")
    if isinstance(moment, datetime):
        return moment.date()
    if isinstance(moment, date):
        return moment
    return file_date(path)


def _ingest_videos(
    directory: str | Path,
    *,
    workers: int,
    recursive: bool,
    only_files: set[str] | None = None,
    since: date | None = None,
    until: date | None = None,
    date_mode: str = DATE_MODE_UPLOAD,
) -> dict:
    """Probe and register source videos separately from the photo pipeline."""

    shallow = date_mode != DATE_MODE_CAPTURE
    discovery = discover_videos(
        directory,
        recursive=recursive,
        since=since if shallow else None,
        until=until if shallow else None,
    )
    paths = discovery.files
    excluded_by_period = discovery.excluded_by_period

    if only_files is not None:
        root = Path(directory)

        def _selected(path: Path) -> bool:
            try:
                relative = str(path.relative_to(root))
            except ValueError:
                relative = path.name
            return relative in only_files or path.name in only_files

        paths = [path for path in paths if _selected(path)]

    if not paths:
        return {
            "discovered": 0,
            "valid": 0,
            "invalid": 0,
            "registered": 0,
            "existing": 0,
            "conflicts": [],
            "errors": [],
            "excluded_by_period": excluded_by_period,
        }

    checked: list[tuple[Path, dict]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        # executor.map preserves the sorted discovery order and bounds the
        # number of concurrent ffprobe/decoder processes to INGEST workers.
        checked.extend(pool.map(_check_video, paths))

    records: list[VideoRecord] = []
    errors: list[dict[str, str]] = []
    invalid = 0
    filtered = 0
    for path, facts in checked:
        if facts["integrity_status"] != "VALID":
            invalid += 1
            errors.append({"filename": path.name, "error": facts.get("error") or "не удалось проверить видео"})
            continue
        if not shallow and not date_in_period(
            _video_moment(path, facts), since, until
        ):
            # "Дата съёмки": the recording time comes from the probed
            # container, so the window can only be applied after the probe.
            filtered += 1
            continue
        try:
            records.append(register_video(**facts))
        except (TypeError, ValueError) as exc:
            invalid += 1
            errors.append({"filename": path.name, "error": str(exc)})

    classification = register_video_records(records)
    preview_root = default_video_preview_root().resolve()
    source_root = Path(directory).resolve()
    posters_created = 0
    poster_errors = 0
    if preview_root == source_root or source_root in preview_root.parents:
        # Never publish generated posters inside the source tree.
        poster_errors = len(classification["NEW"])
    else:
        for record in classification["NEW"] + classification["EXISTING"]:
            poster = preview_root / f"{record.video_id}.jpg"
            if poster.is_file():
                continue
            try:
                build_video_poster(
                    record.video_id,
                    record.source_path,
                    preview_root,
                    duration_seconds=record.duration_seconds,
                )
                posters_created += 1
            except Exception:  # noqa: BLE001 - poster is non-critical to registration
                poster_errors += 1

    return {
        "discovered": len(paths),
        "valid": len(records),
        "invalid": invalid,
        "registered": len(classification["NEW"]),
        "existing": len(classification["EXISTING"]),
        "conflicts": [record.video_id for record in classification["CONFLICT"]],
        "posters_created": posters_created,
        "poster_errors": poster_errors,
        "errors": errors[:20],
        "filtered": filtered,
        "excluded_by_period": excluded_by_period,
    }


def ingest_directory(
    directory: str | Path,
    *,
    workers: int = DEFAULT_WORKERS,
    skip_known: bool = True,
    recursive: bool = True,
    only_files: list[str] | None = None,
    progress=None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_mode: str = DATE_MODE_UPLOAD,
) -> dict:
    """
    Run INGEST over *directory* and register the photos that are new.

    Returns a small summary (counters over the discovered files plus the
    identity classification). The returned dict is what the worker stores as
    the job result, so it must stay JSON-serialisable.

    *only_files* restricts photos *and* videos to a frozen snapshot (relative
    names), used when a pipeline run is resumed after being stopped.

    *progress* is an optional `(done, total)` callback for photo files (video
    probing is a separate branch and is not counted here).

    *date_from*/*date_to* (YYYY-MM-DD, inclusive) and *date_mode* are the
    scan depth by time: "upload" compares the file's own date during the walk,
    "capture" compares the EXIF capture date after the file has been read
    (see app.ingest.pipeline.run).
    """

    subset = set(only_files) if only_files is not None else None
    since = _parse_date(date_from, "date_from")
    until = _parse_date(date_to, "date_to")
    if since is not None and until is not None and until < since:
        raise ValueError("date_to must not be earlier than date_from")

    result = run(
        directory,
        workers,
        recursive=recursive,
        skip_known=known_source_files if skip_known else None,
        only_files=subset,
        progress=progress,
        since=since,
        until=until,
        date_mode=date_mode,
    )

    records = [
        item.record
        for item in result.results
        if item.status == "VALID" and item.record is not None
    ]

    # A scan can mix both schemes: a metadata record whose EXIF is incomplete
    # falls back to the content SHA. Each group is classified by its own rules.
    from app.ingest.identity_v2 import IDENTITY_SCHEME
    from app.ingest.metadata_register import classify_and_insert_metadata

    legacy_records = [
        record for record in records if record.identity_scheme != IDENTITY_SCHEME
    ]
    metadata_records = [
        record for record in records if record.identity_scheme == IDENTITY_SCHEME
    ]

    classification = {"NEW": [], "EXISTING": [], "CONFLICT": []}

    legacy = check_identity_batch(legacy_records)

    # Conflicts are reported, not fatal: one contradictory file must not block
    # the rest of a folder. register_new_photos() keeps the strict behaviour
    # for the upload path.
    if legacy["NEW"]:
        inserted = insert_photos(legacy["NEW"])

        # A parallel ingest may have inserted the same file between the
        # identity check and our INSERT. Those rows lost the race and are
        # counted as EXISTING (and never get a second preview job).
        if inserted is not None:
            raced = [
                record
                for record in legacy["NEW"]
                if record.photo_id not in inserted
            ]
            legacy["NEW"] = [
                record
                for record in legacy["NEW"]
                if record.photo_id in inserted
            ]
            legacy["EXISTING"].extend(raced)

    for key in classification:
        classification[key].extend(legacy[key])

    if metadata_records:
        metadata = classify_and_insert_metadata(metadata_records)

        for key in classification:
            classification[key].extend(metadata[key])

    preview_queued = 0
    preview_active = 0
    preview_enqueue_errors: list[dict[str, str]] = []
    for record in classification["NEW"]:
        try:
            job_id = enqueue_registered_photo(record.photo_id)
            if job_id is None:
                preview_active += 1
            else:
                preview_queued += 1
        except Exception as exc:  # noqa: BLE001 - registration remains successful
            preview_enqueue_errors.append({"photo_id": record.photo_id, "error": redact_absolute_paths(str(exc))})

    # Video validation/registration is a separate branch: video IDs live in a
    # distinct table and are never sent to the photo preview/DINO/HYBRID/QWEN
    # pipelines. Photo counters keep their existing shape for old clients.
    videos = _ingest_videos(
        directory,
        workers=workers,
        recursive=recursive,
        only_files=subset,
        since=since,
        until=until,
        date_mode=date_mode,
    )

    return {
        "directory": str(directory),
        "discovered": result.discovered,
        "counters": result.counters,
        "excluded_by_period": result.excluded_by_period,
        "registered": len(classification["NEW"]),
        "existing": len(classification["EXISTING"]),
        "conflicts": [record.photo_id for record in classification["CONFLICT"]],
        "errors": [
            {"filename": item.filename, "error": item.error}
            for item in result.results
            if item.status == "INVALID"
        ][:20],
        "videos": videos,
        "preview": {
            "queued": preview_queued,
            "already_active": preview_active,
            "enqueue_errors": preview_enqueue_errors[:20],
        },
    }
