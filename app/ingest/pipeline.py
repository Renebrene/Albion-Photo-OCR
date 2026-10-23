from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime
from pathlib import Path

from app.core.errors import redact_paths
from app.core.parallel import bounded_submit, default_window
from app.ingest.identity import create_identity
from app.ingest.identity_v2 import IDENTITY_SCHEME, active_scheme
from app.ingest.integrity import check_file, date_in_period, discover, file_date
from app.ingest.register import PhotoRecord, register_photo
from app.ingest.shadow import record_shadow
from app.ingest.result import (
    IngestResult,
    create_ingest_result,
    filtered_result,
    invalid_result,
    skipped_result,
    valid_result,
)

# Date window modes, shared with the grid filter (see api/schemas.py).
DATE_MODE_UPLOAD = "upload"
DATE_MODE_CAPTURE = "capture"


def taken_at_date(taken_at: object) -> date | None:
    """Calendar date of a stored EXIF timestamp ("YYYY-MM-DD HH:MM:SS")."""

    if not taken_at:
        return None
    raw = str(taken_at)[:10]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


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

    if active_scheme() == IDENTITY_SCHEME:
        from app.ingest.metadata_pipeline import process_file_metadata

        return process_file_metadata(path)

    integrity = check_file(path)

    if integrity["integrity_status"] != "VALID":
        raise ValueError(
            f"Integrity check failed for {path}: "
            f"{integrity['error']}"
        )

    identity = create_identity(integrity["sha256"])

    # Теневая проверка будущей схемы идентичности (SCENE_IDENTITY_SHADOW=1):
    # только локальный журнал, регистрация ниже по-прежнему идёт по SHA-256.
    record_shadow(path, identity.sha256, identity.photo_id, integrity)

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
    only_files: set[str] | None = None,
    progress=None,
    since: date | None = None,
    until: date | None = None,
    date_mode: str = DATE_MODE_UPLOAD,
) -> IngestResult:
    """
    Run INGEST in parallel over every supported file in *directory*.

    Every discovered file produces one result.
    INVALID files do not stop processing of the remaining files.

    *skip_known* is an optional lookup `(filename, size) -> bool`. A file it
    accepts is reported as SKIPPED without being read or hashed; the database
    lookup itself is left to the caller so this function stays free of any
    database dependency.

    *only_files* restricts the scan to a frozen set of relative paths (as used
    by a resumed pipeline run); a file outside the set is ignored.

    *progress* is an optional `(done, total)` callback invoked as each file is
    accounted for (skipped or processed); the caller turns it into a job
    progress record.

    *since*/*until* bound the scan to a period, *date_mode* says which date
    that period means:

    - `upload` (дата загрузки) — the file's own date. The filter runs during
      the walk, so a file outside the window is never read or hashed.
    - `capture` (дата съёмки) — the EXIF date, known only after the file has
      been decoded. Files outside the window come back as FILTERED instead of
      VALID. Already registered files are still skipped before reading, so a
      repeated capture-mode scan reads only the new files.
    """

    if workers < 1:
        raise ValueError("workers must be >= 1")
    if date_mode not in {DATE_MODE_UPLOAD, DATE_MODE_CAPTURE}:
        raise ValueError("date_mode must be 'upload' or 'capture'")

    shallow = date_mode == DATE_MODE_UPLOAD
    discovery = discover(
        directory,
        recursive=recursive,
        since=since if shallow else None,
        until=until if shallow else None,
    )
    files = discovery.files
    excluded_by_period = discovery.excluded_by_period

    if only_files is not None:
        root = Path(directory)

        def _selected(path: Path) -> bool:
            try:
                relative = str(path.relative_to(root))
            except ValueError:
                relative = path.name
            return relative in only_files or path.name in only_files

        files = [path for path in files if _selected(path)]

    if not files:
        if progress is not None:
            progress(0, 0)
        return create_ingest_result(
            [], excluded_by_period=excluded_by_period
        )

    total = len(files)
    done = 0
    results = []

    def _tick() -> None:
        nonlocal done
        done += 1
        if progress is not None:
            progress(done, total)

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
                _tick()
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
                _tick()

    if not shallow:
        # "Дата съёмки": the capture date is in the decoded file, so the
        # window can only be applied now. A file without EXIF falls back to
        # its own date, which is what the grid does for photos without
        # taken_at.
        kept: list = []
        for item in results:
            if item.status != "VALID" or item.record is None:
                kept.append(item)
                continue
            moment = taken_at_date(item.record.taken_at)
            if moment is None:
                moment = file_date(Path(item.source_path))
            if date_in_period(moment, since, until):
                kept.append(item)
            else:
                kept.append(
                    filtered_result(
                        source_path=item.source_path,
                        filename=item.filename,
                    )
                )
        results = kept

    return create_ingest_result(
        results, excluded_by_period=excluded_by_period
    )
