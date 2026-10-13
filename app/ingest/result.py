from __future__ import annotations

from dataclasses import dataclass

from app.ingest.register import PhotoRecord


@dataclass(frozen=True)
class IngestFileResult:
    """
    Result of processing one source file through INGEST.

    A file is VALID with a PhotoRecord, INVALID with an error message, or
    SKIPPED because (filename, size) already exists in the database.
    """

    source_path: str
    filename: str

    status: str

    record: PhotoRecord | None = None
    error: str | None = None


@dataclass(frozen=True)
class IngestResult:
    """
    Result of one complete INGEST pass.

    The result contains one IngestFileResult for every
    discovered source file.
    """

    discovered: int
    results: list[IngestFileResult]
    counters: dict[str, int]


def valid_result(record: PhotoRecord) -> IngestFileResult:
    return IngestFileResult(
        source_path=record.source_path,
        filename=record.filename,
        status="VALID",
        record=record,
        error=None,
    )


def invalid_result(
    *,
    source_path: str,
    filename: str,
    error: str,
) -> IngestFileResult:
    return IngestFileResult(
        source_path=source_path,
        filename=filename,
        status="INVALID",
        record=None,
        error=error,
    )


def skipped_result(*, source_path: str, filename: str) -> IngestFileResult:
    """
    A file that is already registered (same name and size in the database).

    Skipping is only a shortcut: the identity check on sha256 still decides
    whether anything is written.
    """

    return IngestFileResult(
        source_path=source_path,
        filename=filename,
        status="SKIPPED",
        record=None,
        error=None,
    )


def create_ingest_result(
    results: list[IngestFileResult],
) -> IngestResult:
    counters = {
        "VALID": sum(result.status == "VALID" for result in results),
        "INVALID": sum(result.status == "INVALID" for result in results),
        "SKIPPED": sum(result.status == "SKIPPED" for result in results),
    }

    return IngestResult(
        discovered=len(results),
        results=results,
        counters=counters,
    )
