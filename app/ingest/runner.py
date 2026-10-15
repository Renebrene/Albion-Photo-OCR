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


def _check_video(path: Path) -> tuple[Path, dict]:
    return path, check_video_file(path)


def _ingest_videos(directory: str | Path, *, workers: int, recursive: bool) -> dict:
    """Probe and register source videos separately from the photo pipeline."""

    paths = discover_video_files(directory, recursive=recursive)
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
    return {
        "discovered": len(paths),
        "valid": len(records),
        "invalid": invalid,
        "registered": len(classification["NEW"]),
        "existing": len(classification["EXISTING"]),
        "conflicts": [record.video_id for record in classification["CONFLICT"]],
        "errors": errors[:20],
    }


def ingest_directory(
    directory: str | Path,
    *,
    workers: int = DEFAULT_WORKERS,
    skip_known: bool = True,
    recursive: bool = True,
) -> dict:
    """
    Run INGEST over *directory* and register the photos that are new.

    Returns a small summary (counters over the discovered files plus the
    identity classification). The returned dict is what the worker stores as
    the job result, so it must stay JSON-serialisable.
    """

    result = run(
        directory,
        workers,
        recursive=recursive,
        skip_known=known_source_files if skip_known else None,
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
        insert_photos(classification["NEW"])

    # Video validation/registration is a separate branch: video IDs live in a
    # distinct table and are never sent to the photo preview/DINO/HYBRID/QWEN
    # pipelines. Photo counters keep their existing shape for old clients.
    videos = _ingest_videos(directory, workers=workers, recursive=recursive)

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
    }
