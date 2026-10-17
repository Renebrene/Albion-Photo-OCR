"""Two concurrent ingests of the same file must not fail the batch."""

from __future__ import annotations

from app.ingest import database
from app.ingest.register import PhotoRecord


def _record(suffix: str) -> PhotoRecord:
    return PhotoRecord(
        photo_id="PH_" + suffix * 12,
        source_path=f"/photos/{suffix}.jpg",
        filename=f"{suffix}.jpg",
        sha256=suffix * 32,
        container_format="JPEG",
        frame_count=1,
        width=10,
        height=8,
        size_bytes=100,
    )


def test_raced_rows_are_reclassified_as_existing(monkeypatch):
    first = _record("a")
    second = _record("b")

    monkeypatch.setattr(
        database, "check_identity_batch",
        lambda records: {
            "NEW": [first, second],
            "EXISTING": [],
            "CONFLICT": [],
        },
    )
    # A concurrent ingest inserted `first` between the check and our INSERT.
    monkeypatch.setattr(
        database, "insert_photos",
        lambda records: {first.photo_id},
    )

    result = database.register_new_photos([first, second])

    assert result["NEW"] == [first]
    assert result["EXISTING"] == [second]
    assert result["CONFLICT"] == []


def test_identity_conflicts_still_fail(monkeypatch):
    first = _record("c")

    monkeypatch.setattr(
        database, "check_identity_batch",
        lambda records: {
            "NEW": [],
            "EXISTING": [],
            "CONFLICT": [first],
        },
    )

    try:
        database.register_new_photos([first])
    except ValueError as exc:
        assert "Identity conflicts" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("conflict must raise")
