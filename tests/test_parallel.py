"""
Tests for bounded parallel submission (app.core.parallel).

Pure logic only: no database, no model.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.core.parallel import bounded_submit, default_window


def test_bounded_submit_preserves_order_and_results():
    items = list(range(25))

    with ThreadPoolExecutor(max_workers=4) as executor:
        seen = [
            (item, future.result())
            for item, future in bounded_submit(
                executor, lambda x: x * 2, items, window=4
            )
        ]

    assert [item for item, _ in seen] == items
    assert [value for _, value in seen] == [x * 2 for x in items]


def test_bounded_submit_limits_in_flight():
    in_flight = 0
    peak = 0
    lock = threading.Lock()

    def work(_):
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.01)
        with lock:
            in_flight -= 1
        return True

    with ThreadPoolExecutor(max_workers=8) as executor:
        for _, future in bounded_submit(
            executor, work, list(range(40)), window=3
        ):
            future.result()

    assert peak <= 3


def test_bounded_submit_empty():
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(bounded_submit(executor, lambda x: x, [], window=2)) == []


def test_default_window_scales_with_workers():
    assert default_window(1) == 4
    assert default_window(6) == 12
