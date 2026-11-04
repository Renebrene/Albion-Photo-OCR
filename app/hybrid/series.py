"""Series consensus for HYBRID.

Photos shot in one burst are often the same screen from the same folder.  A
low-margin outlier can then be corrected by the verdicts of its series even
when its own top-1 is nearly tied.  This is deliberately a separate rule from
the immediate left/right batch neighbours: it groups by capture time and
source folder, not by row order.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Iterable


DEFAULT_GAP_SECONDS = 10.0
DEFAULT_MIN_GROUP = 3
DEFAULT_SHARE = 0.75


def _as_datetime(value: Any) -> datetime | None:
    return value if isinstance(value, datetime) else None


def series_consensus(
    items: Iterable[Any],
    *,
    gap_seconds: float = DEFAULT_GAP_SECONDS,
    min_group: int = DEFAULT_MIN_GROUP,
    share: float = DEFAULT_SHARE,
) -> dict[str, str]:
    """
    Return ``photo_id -> consensus fingerprint`` for low-confidence outliers.

    Frames without capture time or source folder are never grouped: there is
    no reliable series boundary.  Only frames with an existing previous HYBRID
    verdict vote; the denominator is the number of such voters in the group.
    """

    if gap_seconds < 0:
        raise ValueError("gap_seconds must be >= 0")
    if min_group < 2:
        raise ValueError("min_group must be >= 2")
    if not 0 < share <= 1:
        raise ValueError("share must be in (0, 1]")

    ordered = sorted(
        (
            item
            for item in items
            if _as_datetime(getattr(item, "taken_at", None)) is not None
            and getattr(item, "source_dir", None)
        ),
        key=lambda item: (
            str(item.source_dir),
            item.taken_at,
            str(item.photo_id),
        ),
    )

    groups: list[list[Any]] = []
    current: list[Any] = []
    previous = None

    for item in ordered:
        if previous is not None:
            same_dir = item.source_dir == previous.source_dir
            gap = (item.taken_at - previous.taken_at).total_seconds()
            if not same_dir or gap > gap_seconds:
                if current:
                    groups.append(current)
                current = []
        current.append(item)
        previous = item

    if current:
        groups.append(current)

    result: dict[str, str] = {}

    for group in groups:
        voters = [
            item
            for item in group
            if getattr(item, "previous_final_id", None)
        ]
        if len(voters) < min_group:
            continue

        counts = Counter(str(item.previous_final_id) for item in voters)
        winner, votes = counts.most_common(1)[0]

        if votes / len(voters) < share:
            continue

        for item in group:
            if getattr(item, "previous_final_id", None) != winner:
                result[str(item.photo_id)] = winner

    return result
