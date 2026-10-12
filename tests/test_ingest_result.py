"""
Unit tests for app.ingest.result.

IngestFileResult / IngestResult are frozen dataclasses that
summarize one INGEST pass with VALID/INVALID counters.
"""

import dataclasses

import pytest

from app.ingest.register import PhotoRecord
from app.ingest.result import (
    IngestFileResult,
    IngestResult,
    create_ingest_result,
    invalid_result,
    valid_result,
)


def _record() -> PhotoRecord:
    return PhotoRecord(
        photo_id="PH_c4a49077cb428c56ad682a36",
        source_path="/read/only/source.jpg",
        filename="source.jpg",
        sha256="c4a49077cb428c56ad682a36fcbd4c6d17e271a5af05fd990481bd33ce1520a6",
        container_format="JPEG",
        frame_count=1,
        width=10,
        height=10,
    )


def test_valid_result_carries_record():
    record = _record()
    result = valid_result(record)

    assert isinstance(result, IngestFileResult)
    assert result.status == "VALID"
    assert result.record is record
    assert result.error is None
    assert result.source_path == record.source_path
    assert result.filename == record.filename


def test_invalid_result_carries_error_and_no_record():
    result = invalid_result(
        source_path="/read/only/broken.jpg",
        filename="broken.jpg",
        error="Integrity check failed",
    )

    assert result.status == "INVALID"
    assert result.record is None
    assert result.error == "Integrity check failed"


def test_counters_count_valid_and_invalid():
    summary = create_ingest_result(
        [
            valid_result(_record()),
            invalid_result(source_path="a", filename="a", error="x"),
            invalid_result(source_path="b", filename="b", error="y"),
        ]
    )

    assert isinstance(summary, IngestResult)
    assert summary.discovered == 3
    assert summary.counters == {"VALID": 1, "INVALID": 2}
    assert len(summary.results) == 3


def test_empty_batch_has_zero_counters():
    summary = create_ingest_result([])

    assert summary.discovered == 0
    assert summary.counters == {"VALID": 0, "INVALID": 0}
    assert summary.results == []


def test_results_are_immutable():
    result = valid_result(_record())

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "INVALID"
