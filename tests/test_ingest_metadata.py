"""
INGEST metadata: EXIF capture date, file size and the fast skip shortcut.

No database is touched here: the skip shortcut is exercised through a fake
lookup, which is exactly how pipeline.run is meant to receive it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.ingest.integrity import (
    check_file,
    discover_files,
    parse_exif_datetime,
    read_taken_at,
    scan_directory,
)
from app.ingest.pipeline import known_pairs, run
from app.ingest.register import register_photo


def _jpeg(path: Path, taken_at: str | None = None) -> Path:
    image = Image.new("RGB", (40, 30), "white")

    if taken_at:
        exif = image.getexif()
        exif[0x9003] = taken_at  # DateTimeOriginal
        image.save(path, exif=exif)
    else:
        image.save(path)

    return path


# ---- EXIF parsing (pure) ----


def test_parse_exif_datetime_accepts_the_exif_format():
    assert parse_exif_datetime("2026:05:01 10:20:30") == "2026-05-01 10:20:30"


def test_parse_exif_datetime_rejects_unusable_values():
    for value in [
        None,
        20260501,
        "",
        "not a date",
        "0000:00:00 00:00:00",
        "1899:01:01 00:00:00",
        "2200:01:01 00:00:00",
    ]:
        assert parse_exif_datetime(value) is None


def test_parse_exif_datetime_uses_the_first_19_characters():
    # Some cameras append a sub-second part or a timezone offset.
    assert parse_exif_datetime("2026:05:01 10:20:30+03:00") == "2026-05-01 10:20:30"


# ---- integrity check carries the new metadata ----


def test_check_file_reports_size_and_capture_date(tmp_path):
    path = _jpeg(tmp_path / "shot.jpg", taken_at="2026:05:01 10:20:30")

    result = check_file(path)

    assert result["integrity_status"] == "VALID"
    assert result["size_bytes"] == path.stat().st_size
    assert result["taken_at"] == "2026-05-01 10:20:30"


def test_check_file_tolerates_missing_exif(tmp_path):
    path = _jpeg(tmp_path / "plain.jpg")

    result = check_file(path)

    assert result["integrity_status"] == "VALID"
    assert result["taken_at"] is None


def test_read_taken_at_on_a_broken_exif_block_is_not_an_error(tmp_path):
    class Exploding:
        def getexif(self):
            raise OSError("truncated EXIF")

    assert read_taken_at(Exploding()) is None


# ---- scan (folder picker, no reads, no DB) ----


def test_scan_directory_counts_recursively_and_sizes_files(tmp_path):
    first = _jpeg(tmp_path / "a.jpg")
    nested = tmp_path / "sub"
    nested.mkdir()
    second = _jpeg(nested / "b.JPG")
    (nested / "notes.txt").write_text("not a photo", encoding="utf-8")

    stats = scan_directory(tmp_path)

    assert stats["files"] == 2
    assert stats["bytes"] == first.stat().st_size + second.stat().st_size
    assert stats["path"] == str(tmp_path)


def test_scan_directory_of_a_missing_folder_is_empty(tmp_path):
    stats = scan_directory(tmp_path / "nope")

    assert stats["files"] == 0
    assert stats["bytes"] == 0


# ---- the skip shortcut in pipeline.run ----


def test_run_skips_files_the_lookup_already_knows(tmp_path):
    _jpeg(tmp_path / "a.jpg")
    _jpeg(tmp_path / "b.jpg")

    seen: list[tuple[str, int]] = []

    def skip_known(pairs):
        seen.extend(pairs)
        return set(pairs)

    result = run(tmp_path, workers=1, skip_known=skip_known)

    assert result.counters["SKIPPED"] == 2
    assert result.counters["VALID"] == 0
    assert result.counters["INVALID"] == 0
    assert all(item.status == "SKIPPED" for item in result.results)
    assert {name for name, _ in seen} == {"a.jpg", "b.jpg"}


def test_run_without_the_shortcut_processes_everything(tmp_path):
    _jpeg(tmp_path / "a.jpg")

    result = run(tmp_path, workers=1)

    assert result.counters == {"VALID": 1, "INVALID": 0, "SKIPPED": 0}


def test_run_can_stay_non_recursive(tmp_path):
    nested = tmp_path / "sub"
    nested.mkdir()
    _jpeg(tmp_path / "top.jpg")
    _jpeg(nested / "deep.jpg")

    result = run(tmp_path, workers=1, recursive=False)

    assert result.counters["VALID"] == 1
    assert [item.filename for item in result.results] == ["top.jpg"]


def test_known_pairs_skips_unreadable_paths(tmp_path):
    path = _jpeg(tmp_path / "a.jpg")
    missing = tmp_path / "gone.jpg"

    assert known_pairs([path, missing]) == [("a.jpg", path.stat().st_size)]


def test_discover_files_returns_sorted_paths(tmp_path):
    _jpeg(tmp_path / "b.jpg")
    _jpeg(tmp_path / "a.jpg")

    assert [p.name for p in discover_files(tmp_path)] == ["a.jpg", "b.jpg"]


# ---- register validation ----


def test_register_photo_rejects_a_negative_size():
    with pytest.raises(ValueError):
        register_photo(
            photo_id="PH_" + "0" * 24,
            source_path="/photos/a.jpg",
            filename="a.jpg",
            sha256="a" * 64,
            container_format="JPEG",
            frame_count=1,
            width=10,
            height=10,
            size_bytes=-1,
        )


def test_register_photo_keeps_the_defaults_for_old_callers():
    record = register_photo(
        photo_id="PH_" + "0" * 24,
        source_path="/photos/a.jpg",
        filename="a.jpg",
        sha256="a" * 64,
        container_format="JPEG",
        frame_count=1,
        width=10,
        height=10,
    )

    assert record.size_bytes is None
    assert record.taken_at is None
