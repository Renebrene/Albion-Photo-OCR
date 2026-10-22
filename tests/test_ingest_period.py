"""
Scan depth by time: the INSPECT date window.

Two modes, both inclusive, both optional:

- "upload"  — the file's own date (mtime). Applied while walking, so a file
  outside the window is never read, decoded or hashed.
- "capture" — the EXIF capture date, available only after the file has been
  decoded; such a file comes back FILTERED instead of VALID.

No database is used here: `skip_known` is a plain callable, exactly as
pipeline.run expects it.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pytest
from PIL import Image

from app.ingest.integrity import (
    date_in_period,
    discover,
    discover_files,
    file_date,
    scan_directory,
)
from app.ingest.pipeline import run, taken_at_date
from app.ingest.result import filtered_result
from app.ingest.video_integrity import discover_videos


def _jpeg(path: Path, taken_at: str | None = None) -> Path:
    image = Image.new("RGB", (40, 30), "white")

    if taken_at:
        exif = image.getexif()
        exif[0x9003] = taken_at  # DateTimeOriginal
        image.save(path, exif=exif)
    else:
        image.save(path)

    return path


def _dated(path: Path, day: str) -> Path:
    """Set the file's own timestamp (mtime) to a calendar day."""

    moment = datetime.strptime(day, "%Y-%m-%d").replace(hour=12)
    stamp = moment.timestamp()
    os.utime(path, (stamp, stamp))

    return path


def _counter(result, status: str) -> int:
    return result.counters.get(status, 0)


# ---- pure helpers ---------------------------------------------------------


def test_date_in_period_is_inclusive_and_open_ended():
    moment = date(2026, 5, 10)

    assert date_in_period(moment, date(2026, 5, 10), date(2026, 5, 10)) is True
    assert date_in_period(moment, date(2026, 5, 11), None) is False
    assert date_in_period(moment, None, date(2026, 5, 9)) is False
    assert date_in_period(moment, None, None) is True


def test_unknown_date_is_kept():
    # A failed stat (share gone) or a missing EXIF date must not look "too old".
    assert date_in_period(None, date(2026, 5, 10), date(2026, 5, 10)) is True


def test_taken_at_date_reads_the_stored_exif_format():
    assert taken_at_date("2026-05-01 10:20:30") == date(2026, 5, 1)
    assert taken_at_date(None) is None
    assert taken_at_date("not a date") is None


def test_file_date_missing_file_is_none(tmp_path):
    assert file_date(tmp_path / "nope.jpg") is None


def test_filtered_result_is_not_an_error():
    item = filtered_result(source_path="/photos/a.jpg", filename="a.jpg")

    assert item.status == "FILTERED"
    assert item.record is None
    assert item.error is None


# ---- discovery ------------------------------------------------------------


def test_discover_applies_the_window_and_counts_excluded(tmp_path):
    _dated(_jpeg(tmp_path / "inside.jpg"), "2026-05-10")
    _dated(_jpeg(tmp_path / "before.jpg"), "2026-04-01")
    _dated(_jpeg(tmp_path / "after.jpg"), "2026-06-01")

    where = date(2026, 5, 10)
    discovery = discover(tmp_path, since=where, until=where)

    assert [path.name for path in discovery.files] == ["inside.jpg"]
    assert discovery.excluded_by_period == 2


def test_discover_without_a_window_is_unchanged(tmp_path):
    _dated(_jpeg(tmp_path / "a.jpg"), "2020-01-01")
    _dated(_jpeg(tmp_path / "b.jpg"), "2026-05-10")

    discovery = discover(tmp_path)

    assert [path.name for path in discovery.files] == ["a.jpg", "b.jpg"]
    assert discovery.excluded_by_period == 0
    assert discover_files(tmp_path) == discovery.files


def test_scan_directory_reports_the_period_split(tmp_path):
    _dated(_jpeg(tmp_path / "inside.jpg"), "2026-05-10")
    _dated(_jpeg(tmp_path / "outside.jpg"), "2026-01-01")

    stats = scan_directory(
        tmp_path, since=date(2026, 5, 10), until=date(2026, 5, 10)
    )

    assert stats["files"] == 1
    assert stats["excluded_by_period"] == 1


# ---- upload mode (the file's own date) ------------------------------------


def test_upload_mode_does_not_read_files_outside_the_window(tmp_path):
    # The file outside the window is not a JPEG at all: if it were read, the
    # INVALID counter would grow. It must stay untouched and merely excluded.
    (tmp_path / "broken.jpg").write_bytes(b"not an image")
    _dated(tmp_path / "broken.jpg", "2026-01-01")

    result = run(
        tmp_path,
        workers=1,
        since=date(2026, 5, 1),
        until=date(2026, 5, 31),
        date_mode="upload",
    )

    assert result.discovered == 0
    assert _counter(result, "INVALID") == 0
    assert result.excluded_by_period == 1


def test_upload_mode_keeps_the_boundaries(tmp_path):
    _dated(_jpeg(tmp_path / "first.jpg"), "2026-05-01")
    _dated(_jpeg(tmp_path / "last.jpg"), "2026-05-31")

    result = run(
        tmp_path,
        workers=1,
        since=date(2026, 5, 1),
        until=date(2026, 5, 31),
        date_mode="upload",
    )

    assert _counter(result, "VALID") == 2
    assert result.excluded_by_period == 0


def test_upload_mode_without_bounds_registers_everything(tmp_path):
    _dated(_jpeg(tmp_path / "old.jpg"), "2019-01-01")

    result = run(tmp_path, workers=1, date_mode="upload")

    assert _counter(result, "VALID") == 1
    assert result.excluded_by_period == 0
    assert _counter(result, "FILTERED") == 0


# ---- capture mode (the EXIF date) -----------------------------------------


def test_capture_mode_filters_by_capture_date_not_by_file_date(tmp_path):
    # Copied onto the volume today, but shot in January: the file date is
    # inside the window, the capture date is not.
    path = _dated(_jpeg(tmp_path / "old_shot.jpg", "2026:01:15 09:00:00"), "2026-05-20")

    result = run(
        tmp_path,
        workers=1,
        since=date(2026, 5, 1),
        until=date(2026, 5, 31),
        date_mode="capture",
    )

    assert path.exists()
    assert _counter(result, "VALID") == 0
    assert _counter(result, "FILTERED") == 1
    # The walk itself was not narrowed: the decision needs the decoded file.
    assert result.excluded_by_period == 0


def test_capture_mode_keeps_a_photo_shot_inside_the_window(tmp_path):
    _jpeg(tmp_path / "shot.jpg", "2026:05:20 09:00:00")

    result = run(
        tmp_path,
        workers=1,
        since=date(2026, 5, 1),
        until=date(2026, 5, 31),
        date_mode="capture",
    )

    assert _counter(result, "VALID") == 1
    assert _counter(result, "FILTERED") == 0


def test_capture_mode_falls_back_to_the_file_date_without_exif(tmp_path):
    _dated(_jpeg(tmp_path / "plain.jpg"), "2026-01-01")

    result = run(
        tmp_path,
        workers=1,
        since=date(2026, 5, 1),
        until=date(2026, 5, 31),
        date_mode="capture",
    )

    assert _counter(result, "FILTERED") == 1


def test_capture_mode_does_not_hide_errors(tmp_path):
    # A broken file stays INVALID even with a window: the period is not a
    # reason to swallow a real read error.
    (tmp_path / "broken.jpg").write_bytes(b"not an image")

    result = run(
        tmp_path,
        workers=1,
        since=date(2026, 5, 1),
        until=date(2026, 5, 31),
        date_mode="capture",
    )

    assert _counter(result, "INVALID") == 1
    assert _counter(result, "FILTERED") == 0


def test_skipped_files_are_still_skipped_in_capture_mode(tmp_path):
    _jpeg(tmp_path / "known.jpg", "2026:01:15 09:00:00")

    result = run(
        tmp_path,
        workers=1,
        skip_known=lambda pairs: {(name, size) for name, size in pairs},
        since=date(2026, 5, 1),
        until=date(2026, 5, 31),
        date_mode="capture",
    )

    assert _counter(result, "SKIPPED") == 1
    assert _counter(result, "FILTERED") == 0


def test_unknown_date_mode_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        run(tmp_path, workers=1, date_mode="yesterday")


# ---- videos ---------------------------------------------------------------


def test_video_discovery_applies_the_window(tmp_path):
    inside = tmp_path / "inside.mp4"
    outside = tmp_path / "outside.mp4"
    inside.write_bytes(b"not probed here")
    outside.write_bytes(b"not probed here")
    _dated(inside, "2026-05-10")
    _dated(outside, "2026-01-01")

    discovery = discover_videos(
        tmp_path, since=date(2026, 5, 10), until=date(2026, 5, 10)
    )

    assert [path.name for path in discovery.files] == ["inside.mp4"]
    assert discovery.excluded_by_period == 1


def test_video_discovery_of_a_missing_folder_is_empty(tmp_path):
    discovery = discover_videos(tmp_path / "nope", since=date(2026, 5, 1))

    assert discovery.files == []
    assert discovery.excluded_by_period == 0
