"""Read and cache capture-scoped crop advertiser vote snapshots."""

from __future__ import annotations

from datetime import date
from threading import Lock
from typing import Any

from app.billboard.database import get_qwen_frequency_snapshot
from app.refine.rules import get_rules

_lock = Lock()
_cache: dict[tuple[str, str, bool], dict[str, Any]] = {}


def snapshot(*, date_from: str | None = None, date_to: str | None = None) -> dict[str, Any]:
    rules = get_rules()["rules"]
    start = date_from or rules["crop_frequency_date_from"]
    end = date_to or rules["crop_frequency_date_to"]
    use_aliases = rules["use_client_aliases"]
    key = (start, end, use_aliases)
    with _lock:
        if key not in _cache:
            _cache[key] = get_qwen_frequency_snapshot(
                date_from=start, date_to=end, use_aliases=use_aliases
            )
        return _cache[key]


def clear_cache() -> None:
    with _lock:
        _cache.clear()
