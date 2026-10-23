"""Preview worker parallelism: 0 means half of the logical cores."""

from __future__ import annotations

from app.jobs.worker import resolve_parallel


def test_preview_zero_means_half_of_the_cores():
    assert resolve_parallel(0, preview_only=True, cpu_count=12) == 6
    assert resolve_parallel(0, preview_only=True, cpu_count=4) == 2
    assert resolve_parallel(0, preview_only=True, cpu_count=1) == 1


def test_preview_explicit_value_wins():
    assert resolve_parallel(8, preview_only=True, cpu_count=12) == 8


def test_other_workers_keep_the_old_meaning():
    assert resolve_parallel(0, preview_only=False, cpu_count=12) == 1
    assert resolve_parallel(3, preview_only=False, cpu_count=12) == 3
