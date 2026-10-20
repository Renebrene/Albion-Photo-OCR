from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from app.core.config import settings
from app.core.parallel import bounded_submit, default_window
from app.ingest.register import PhotoRecord
from app.preview.database import PreviewRecord, get_preview, upsert_preview
from app.preview.generator import generate_previews
from app.preview.result import PreviewResult


def default_workers() -> int:
    """Use half of the available logical CPU threads."""
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count // 2)


def resolve_workers(workers: int | None = None) -> int:
    """
    Resolve PREVIEW worker count.

    Explicit workers value has priority.
    Settings value 0 means automatic half-CPU mode.
    """

    if workers is None:
        workers = settings.preview_workers

    if workers == 0:
        workers = default_workers()

    if workers < 1:
        raise ValueError("workers must be >= 1")

    return workers


def process_record(
    record: PhotoRecord,
    *,
    preview_root: str | Path,
    small_size: int,
    middle_size: int,
) -> PreviewResult:
    """
    Generate or validate previews for one already-registered photo.

    This function performs filesystem work only.
    PostgreSQL is intentionally handled by the parent process.
    """

    return generate_previews(
        record=record,
        preview_root=preview_root,
        small_size=small_size,
        middle_size=middle_size,
    )


def _to_database_record(result: PreviewResult) -> PreviewRecord:
    """
    Convert a completed PREVIEW result into a PostgreSQL record.

    The caller must ensure that result.ready is True.
    """

    if not result.ready:
        raise ValueError(
            f"Cannot create database record for incomplete previews: "
            f"{result.photo_id}"
        )

    return PreviewRecord(
        photo_id=result.photo_id,
        small_path=result.small.path,
        middle_path=result.middle.path,
        small_width=result.small.width,
        small_height=result.small.height,
        middle_width=result.middle.width,
        middle_height=result.middle.height,
    )


def _is_preview_up_to_date(result: PreviewResult) -> bool:
    """
    True when the registered PostgreSQL row already matches the result.

    When it does, the row does not need to be written again, so the
    pipeline counts it as database_skipped instead of re-upserting.
    """

    existing = get_preview(result.photo_id)

    if existing is None:
        return False

    return (
        existing.small_path == result.small.path
        and existing.middle_path == result.middle.path
        and existing.small_width == result.small.width
        and existing.small_height == result.small.height
        and existing.middle_width == result.middle.width
        and existing.middle_height == result.middle.height
    )


@dataclass(frozen=True)
class PreviewPipelineResult:
    """
    Summary of one PREVIEW pipeline run.
    """

    results: tuple[PreviewResult, ...]
    database_updated: int
    database_skipped: int

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def ready(self) -> int:
        return sum(result.ready for result in self.results)

    @property
    def errors(self) -> int:
        return sum(result.has_error for result in self.results)


def run(
    records: list[PhotoRecord] | tuple[PhotoRecord, ...],
    *,
    workers: int | None = None,
) -> PreviewPipelineResult:
    """
    Run PREVIEW generation for already-registered PhotoRecord objects.

    Preview settings are taken from the central application settings.

    Valid existing previews are skipped.
    Missing previews are created.
    Invalid previews are regenerated.

    PostgreSQL is updated only after both previews are valid.
    """

    records = list(records)

    if not records:
        return PreviewPipelineResult(
            results=(),
            database_updated=0,
            database_skipped=0,
        )

    worker_count = resolve_workers(workers)

    preview_root = settings.preview_root
    small_size = settings.preview_small_size
    middle_size = settings.preview_middle_size

    results: list[PreviewResult] = []
    database_updated = 0
    database_skipped = 0

    worker = partial(
        process_record,
        preview_root=preview_root,
        small_size=small_size,
        middle_size=middle_size,
    )

    def _consume(result: PreviewResult) -> None:
        nonlocal database_updated, database_skipped

        results.append(result)

        if not result.ready:
            return

        if _is_preview_up_to_date(result):
            # Row already matches the validated result: nothing to write.
            database_skipped += 1
            return

        db_record = _to_database_record(result)
        upsert_preview(db_record)
        database_updated += 1

    if len(records) == 1:
        # Every PHOTO_PREVIEW job is one record. Spawning a pool (and six
        # processes under the old default) for a single item was pure
        # overhead; job-level parallelism lives in the worker's --parallel.
        try:
            _consume(worker(records[0]))
        except Exception as exc:
            raise RuntimeError(
                f"PREVIEW failed for {records[0].photo_id}: {exc}"
            ) from exc
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            for record, future in bounded_submit(
                executor,
                worker,
                records,
                window=default_window(worker_count),
            ):
                try:
                    result = future.result()
                except Exception as exc:
                    raise RuntimeError(
                        f"PREVIEW failed for {record.photo_id}: {exc}"
                    ) from exc

                _consume(result)

    return PreviewPipelineResult(
        results=tuple(results),
        database_updated=database_updated,
        database_skipped=database_skipped,
    )
