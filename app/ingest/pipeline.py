from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from app.core.errors import redact_paths
from app.core.parallel import bounded_submit, default_window
from app.ingest.identity import create_identity
from app.ingest.integrity import check_file, discover_files
from app.ingest.register import PhotoRecord, register_photo
from app.ingest.result import (
    IngestResult,
    create_ingest_result,
    invalid_result,
    skipped_result,
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
        size_bytes=integrity["size_bytes"],
        taken_at=integrity["taken_at"],
    )


def known_pairs(files: list[Path]) -> list[tuple[str, int]]:
    """(filename, size) of every discovered file that can be stat()-ed."""

    pairs = []

    for path in files:
        try:
            pairs.append((path.name, path.stat().st_size))
        except OSError:
            continue

    return pairs


def run(
    directory: str | Path,
    workers: int = DEFAULT_WORKERS,
    *,
    recursive: bool = True,
    skip_known=None,
) -> IngestResult:
    """
    Run INGEST in parallel over every supported file in *directory*.

    Every discovered file produces one result.
    INVALID files do not stop processing of the remaining files.

    *skip_known* is an optional lookup `(filename, size) -> bool`. A file it
    accepts is reported as SKIPPED without being read or hashed; the database
    lookup itself is left to the caller so this function stays free of any
    database dependency.
    """

    if workers < 1:
        raise ValueError("workers must be >= 1")

    files = discover_files(directory, recursive=recursive)

    if not files:
        return create_ingest_result([])

    results = []

    if skip_known is not None:
        known = skip_known(known_pairs(files))
        pending = []

        for path in files:
            try:
                size = path.stat().st_size
            except OSError:
                pending.append(path)
                continue

            if (path.name, size) in known:
                results.append(
                    skipped_result(source_path=str(path), filename=path.name)
                )
            else:
                pending.append(path)

        files = pending

    if files:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Bounded window: do not materialise one future per discovered file.
            for path, future in bounded_submit(
                executor,
                process_file,
                files,
                window=default_window(workers),
            ):
                try:
                    record = future.result()
                    results.append(valid_result(record))
                except Exception as exc:
                    results.append(
                        invalid_result(
                            source_path=str(path),
                            filename=path.name,
                            error=redact_paths(str(exc), path),
                        )
                    )

    return create_ingest_result(results)
