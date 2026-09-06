from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from app.ingest.identity import create_identity
from app.ingest.integrity import check_file, discover_files
from app.ingest.register import PhotoRecord, register_photo
from app.ingest.result import (
    IngestResult,
    create_ingest_result,
    invalid_result,
    valid_result,
)


def default_workers() -> int:
    """Use half of the available logical CPU threads."""
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count // 2)


DEFAULT_WORKERS = default_workers()


def process_file(path: str | Path) -> PhotoRecord:
    """
    Process one physical source file through the INGEST pipeline.

    The source file is read only. Nothing is written back to it.
    """

    path = Path(path)

    integrity = check_file(path)

    if integrity["integrity_status"] != "VALID":
        raise ValueError(
            f"Integrity check failed for {path}: "
            f"{integrity['error']}"
        )

    identity = create_identity(integrity["sha256"])

    return register_photo(
        photo_id=identity.photo_id,
        source_path=integrity["source_path"],
        filename=integrity["filename"],
        sha256=identity.sha256,
        container_format=integrity["container_format"],
        frame_count=integrity["frame_count"],
        width=integrity["width"],
        height=integrity["height"],
    )

def run(
    directory: str | Path,
    workers: int = DEFAULT_WORKERS,
) -> IngestResult:
    """
    Run INGEST in parallel.

    Every discovered file produces one result.
    INVALID files do not stop processing of the remaining files.
    """

    if workers < 1:
        raise ValueError("workers must be >= 1")

    files = discover_files(directory)

    if not files:
        return create_ingest_result([])

    results = []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(process_file, path)
            for path in files
        ]

        for path, future in zip(files, futures):
            try:
                record = future.result()
                results.append(valid_result(record))
            except Exception as exc:
                results.append(
                    invalid_result(
                        source_path=str(path),
                        filename=path.name,
                        error=str(exc),
                    )
                )

    return create_ingest_result(results)
