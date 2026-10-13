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

from pathlib import Path

from app.ingest.database import (
    check_identity_batch,
    insert_photos,
    known_source_files,
)
from app.ingest.pipeline import DEFAULT_WORKERS, run


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
    }
