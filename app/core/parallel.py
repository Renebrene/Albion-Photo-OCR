"""
Small helper for bounded parallel submission.

Submitting one future per item up front materialises the whole work list
(huge for large imports) and can hold thousands of pending futures. This
helper keeps at most `window` futures in flight while preserving submission
order, so callers can consume results incrementally.
"""

from __future__ import annotations

from collections import deque
from concurrent.futures import Executor, Future
from typing import Callable, Iterable, Iterator, TypeVar

T = TypeVar("T")


def bounded_submit(
    executor: Executor,
    fn: Callable[[T], object],
    items: Iterable[T],
    *,
    window: int,
) -> Iterator[tuple[T, Future]]:
    """
    Yield ``(item, future)`` pairs, never holding more than *window* futures.

    Order follows the input order. The caller is expected to call
    ``future.result()`` on each yielded future.
    """

    window = max(1, int(window))

    pending: deque[tuple[T, Future]] = deque()
    iterator = iter(items)

    for _ in range(window):
        try:
            item = next(iterator)
        except StopIteration:
            break

        pending.append((item, executor.submit(fn, item)))

    while pending:
        item, future = pending.popleft()
        yield item, future

        try:
            nxt = next(iterator)
        except StopIteration:
            continue

        pending.append((nxt, executor.submit(fn, nxt)))


def default_window(workers: int) -> int:
    """A sensible in-flight window for *workers* threads/processes."""

    return max(4, int(workers) * 2)
