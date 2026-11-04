"""Series consensus by capture time and source folder."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.hybrid.series import series_consensus


def _frame(photo_id: str, seconds: int, final: str | None, folder: str = "/photos/1"):
    return SimpleNamespace(
        photo_id=photo_id,
        taken_at=datetime(2026, 9, 1, 12, 0, 0) + timedelta(seconds=seconds),
        source_dir=folder,
        previous_final_id=final,
    )


def test_four_frame_series_outvotes_one_outlier():
    items = [
        _frame("a", 0, "zorge"),
        _frame("b", 4, "zorge"),
        _frame("c", 8, "zorge"),
        _frame("d", 9, "other"),
    ]

    assert series_consensus(items) == {"d": "zorge"}


def test_two_frames_are_not_a_series():
    items = [_frame("a", 0, "zorge"), _frame("b", 5, "other")]

    assert series_consensus(items) == {}


def test_different_folders_are_not_a_series():
    items = [
        _frame("a", 0, "zorge", "/photos/1"),
        _frame("b", 5, "other", "/photos/2"),
        _frame("c", 9, "other", "/photos/2"),
    ]

    assert series_consensus(items) == {}


def test_large_time_gap_breaks_the_series():
    items = [
        _frame("a", 0, "zorge"),
        _frame("b", 11, "other"),
        _frame("c", 12, "other"),
    ]

    assert series_consensus(items) == {}


def test_frames_without_previous_verdict_do_not_vote():
    items = [
        _frame("a", 0, None),
        _frame("b", 5, "zorge"),
        _frame("c", 9, "other"),
    ]

    assert series_consensus(items) == {}
