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
from pathlib import Path

from app.ingest.database import (
    check_identity_batch,
    insert_photos,
    known_source_files,
)
from app.ingest.pipeline import DEFAULT_WORKERS, run
from app.ingest.video_integrity import check_video_file, discover_video_files
from app.ingest.video_register import VideoRecord, register_video, register_video_records
from app.core.errors import redact_absolute_paths
from app.preview.queue import enqueue_registered_photo
from app.preview.video import build_video_poster, default_video_preview_root


def _check_video(path: Path) -> tuple[Path, dict]:
    return path, check_video_file(path)


def _ingest_videos(
    directory: str | Path,
    *,
    workers: int,
    recursive: bool,
    only_files: set[str] | None = None,
) -> dict:
    """Probe and register source videos separately from the photo pipeline."""

    paths = discover_video_files(directory, recursive=recursive)

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
        }

    checked: list[tuple[Path, dict]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        # executor.map preserves the sorted discovery order and bounds the
        # number of concurrent ffprobe/decoder processes to INGEST workers.
        checked.extend(pool.map(_check_video, paths))

    records: list[VideoRecord] = []
    errors: list[dict[str, str]] = []
    invalid = 0
    for path, facts in checked:
        if facts["integrity_status"] != "VALID":
            invalid += 1
            errors.append({"filename": path.name, "error": facts.get("error") or "не удалось проверить видео"})
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
    }


def ingest_directory(
    directory: str | Path,
    *,
    workers: int = DEFAULT_WORKERS,
    skip_known: bool = True,
    recursive: bool = True,
    only_files: list[str] | None = None,
    progress=None,
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
    """

    subset = set(only_files) if only_files is not None else None

    result = run(
        directory,
        workers,
        recursive=recursive,
        skip_known=known_source_files if skip_known else None,
        only_files=subset,
        progress=progress,
    )

    records = [
        item.record
        for item in result.results
        if item.status == "VALID" and item.record is not None
    ]

    classification = check_identity_batch(records)

    # Conflicts are reported, not fatal: one contradictory file must not block
    # the rest of a folder. register_new_photos() keeps the strict behaviour
    # for the upload path.
    if classification["NEW"]:
        inserted = insert_photos(classification["NEW"])

        # A parallel ingest may have inserted the same file between the
        # identity check and our INSERT. Those rows lost the race and are
        # counted as EXISTING (and never get a second preview job).
        if inserted is not None:
            raced = [
                record
                for record in classification["NEW"]
                if record.photo_id not in inserted
            ]
            classification["NEW"] = [
                record
                for record in classification["NEW"]
                if record.photo_id in inserted
            ]
            classification["EXISTING"].extend(raced)

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
        directory, workers=workers, recursive=recursive, only_files=subset
    )

    return {
        "directory": str(directory),
        "discovered": result.discovered,
        "counters": result.counters,
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
